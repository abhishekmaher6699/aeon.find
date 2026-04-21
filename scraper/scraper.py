import logging
import time

import httpx
from bs4 import BeautifulSoup

from .models import Article

GRAPHQL_URL = "https://api.aeonmedia.co/graphql"
logger = logging.getLogger("scraper")

QUERY = """
query getAeonArticlesByType($type: [ArticleTypeEnum!], $afterCursor: String) {
  articles(site: aeon, type: $type, status: [published], sort: {field: published_at, order: desc}, after: $afterCursor, first: 12) {
    nodes {
      slug
      title
      standfirstShort
      standfirstLong
      authors { name }
      primaryTopic { title slug }
      section { slug }
      image { url alt }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
}

def fetch_page(after_cursor=None):
    variables = {"type": ["essay"]}
    if after_cursor:
        variables["afterCursor"] = after_cursor

    logger.info("Fetching articles...")
    response = httpx.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]["articles"]


def fetch_recent_article_metadata(slug, max_pages=5):
    cursor = None

    for _ in range(max_pages):
        data = fetch_page(cursor)

        for node in data["nodes"]:
            if node["slug"] == slug:
                logger.info("Metadata found")
                return node

        if not data["pageInfo"]["hasNextPage"]:
            break

        cursor = data["pageInfo"]["endCursor"]

    logger.warning("Metadata not found")
    return None


def build_seed_text_from_metadata(node):
    if not node:
        return ""

    parts = [
        node.get("title", ""),
        node.get("standfirstShort", ""),
        node.get("standfirstLong", ""),
        (node.get("primaryTopic") or {}).get("title", ""),
        (node.get("primaryTopic") or {}).get("slug", ""),
        (node.get("section") or {}).get("slug", ""),
        (node.get("image") or {}).get("alt", ""),
    ]

    text = " ".join(p.strip() for p in parts if p and p.strip())

    logger.info("Metadata text built (%s chars)", len(text))
    return text


def scrape_content(slug, max_attempts=3, request_timeout=30, wait_on_rate_limit=True):
    url = f"https://aeon.co/essays/{slug}"

    try:
        response = None

        for attempt in range(1, max_attempts + 1):
            response = httpx.get(url, headers=HEADERS, timeout=request_timeout, follow_redirects=True)

            if response.status_code != 429:
                break

            wait_seconds = min(10 * attempt, 30)

            logger.warning("Rate limited, retrying (%ss)", wait_seconds)

            if not wait_on_rate_limit:
                break

            if attempt < max_attempts:
                time.sleep(wait_seconds)

        if response is None:
            raise RuntimeError("No response")

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        article_div = soup.find(id="article-content")

        if not article_div:
            logger.warning("Article container missing")
            return ""

        dropcap_div = article_div.find(class_="has-dropcap")

        if not dropcap_div:
            logger.warning("Dropcap section missing")
            return ""

        paragraphs = [p.get_text(" ", strip=True) for p in dropcap_div.find_all("p")]
        content = " ".join(p for p in paragraphs if p)

        logger.info("Scraped (%s chars)", len(content))
        return content

    except Exception:
        logger.exception("Scrape failed")
        return ""


def run_scraper():
    cursor = None
    stop = False
    total = 0

    while not stop:
        data = fetch_page(cursor)

        for node in data["nodes"]:
            slug = node["slug"]

            if Article.objects.filter(slug=slug).exists():
                logger.info("Existing article found, stopping")
                stop = True
                break

            content = scrape_content(slug)

            try:
                Article.objects.create(
                    slug=slug,
                    url=f"https://aeon.co/essays/{slug}",
                    title=node["title"],
                    author=node["authors"][0]["name"] if node["authors"] else "",
                    description=node.get("standfirstLong", ""),
                    category=node["primaryTopic"]["title"] if node.get("primaryTopic") else "",
                    section=node["section"]["slug"] if node.get("section") else "",
                    image_url=node["image"]["url"] if node.get("image") else "",
                    content=content,
                )

                total += 1

                if total % 50 == 0:
                    logger.info("Saved %s articles", total)

            except Exception:
                logger.exception("Failed to save article")
                continue

        if not data["pageInfo"]["hasNextPage"]:
            break

        if not stop:
            cursor = data["pageInfo"]["endCursor"]

    logger.info("Scraper finished (%s saved)", total)