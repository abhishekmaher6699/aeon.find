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

    logger.info("Fetching article page from GraphQL | after_cursor=%s", after_cursor)
    response = httpx.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    articles = response.json()["data"]["articles"]
    logger.info(
        "Fetched GraphQL page | status=%s nodes=%s has_next=%s end_cursor=%s",
        response.status_code,
        len(articles["nodes"]),
        articles["pageInfo"]["hasNextPage"],
        articles["pageInfo"]["endCursor"],
    )
    return articles


def fetch_recent_article_metadata(slug, max_pages=5):
    logger.info("Looking up recent article metadata | slug=%s max_pages=%s", slug, max_pages)
    cursor = None

    for page_number in range(1, max_pages + 1):
        data = fetch_page(cursor)
        nodes = data["nodes"]
        logger.info(
            "Scanning metadata page | slug=%s page_number=%s nodes=%s",
            slug,
            page_number,
            len(nodes),
        )

        for node in nodes:
            if node["slug"] == slug:
                logger.info(
                    "Recent article metadata found | slug=%s page_number=%s title=%s",
                    slug,
                    page_number,
                    node["title"][:120],
                )
                return node

        if not data["pageInfo"]["hasNextPage"]:
            break

        cursor = data["pageInfo"]["endCursor"]

    logger.warning("Recent article metadata not found | slug=%s scanned_pages=%s", slug, max_pages)
    return None


def build_seed_text_from_metadata(node):
    if not node:
        return ""

    standfirst_short = node.get("standfirstShort", "")
    standfirst_long = node.get("standfirstLong", "")
    primary_topic = node.get("primaryTopic") or {}
    section = node.get("section") or {}
    image = node.get("image") or {}

    parts = [
        node.get("title", ""),
        standfirst_short,
        standfirst_long,
        primary_topic.get("title", ""),
        primary_topic.get("slug", ""),
        section.get("slug", ""),
        image.get("alt", ""),
    ]

    metadata = [
        part.strip()
        for part in parts
        if part and part.strip()
    ]

    text = " ".join(metadata)
    logger.info(
        "Built seed text from metadata | slug=%s fields=%s chars=%s preview=%s",
        node.get("slug"),
        metadata,
        len(text),
        text[:240],
    )
    return text


def scrape_content(slug, max_attempts=3, request_timeout=30, wait_on_rate_limit=True):
    url = f"https://aeon.co/essays/{slug}"
    logger.info(
        "Scraping content | slug=%s url=%s max_attempts=%s request_timeout=%s",
        slug,
        url,
        max_attempts,
        request_timeout,
        # wait_on_rate_limit,
    )

    try:
        response = None
        for attempt in range(1, max_attempts + 1):
            response = httpx.get(url, headers=HEADERS, timeout=request_timeout, follow_redirects=True)
            if response.status_code != 429:
                break

            retry_after = response.headers.get("retry-after")
            try:
                wait_seconds = int(retry_after) if retry_after else min(10 * attempt, 30)
            except ValueError:
                wait_seconds = min(10 * attempt, 30)

            logger.warning(
                "Rate limited while scraping | slug=%s attempt=%s wait_seconds=%s",
                slug,
                attempt,
                wait_seconds,
            )

            if not wait_on_rate_limit:
                logger.info("Skipping rate-limit wait and falling back quickly | slug=%s attempt=%s", slug, attempt)
                break

            if attempt < max_attempts:
                time.sleep(wait_seconds)

        if response is None:
            raise RuntimeError("No response received while scraping.")
        response.raise_for_status()

        final_url = str(response.url)
        content_type = response.headers.get("content-type", "")
        logger.info(
            "Scrape response received | slug=%s status=%s final_url=%s content_type=%s bytes=%s",
            slug,
            response.status_code,
            final_url,
            content_type,
            len(response.text),
        )

        soup = BeautifulSoup(response.text, "html.parser")
        page_title = soup.title.get_text(strip=True) if soup.title else ""
        article_div = soup.find(id="article-content")
        if not article_div:
            logger.warning(
                "article-content container missing | slug=%s final_url=%s page_title=%s body_preview=%s",
                slug,
                final_url,
                page_title[:120],
                soup.get_text(" ", strip=True)[:240],
            )
            return ""

        dropcap_div = article_div.find(class_="has-dropcap")
        if not dropcap_div:
            logger.warning(
                "has-dropcap container missing | slug=%s final_url=%s page_title=%s article_preview=%s",
                slug,
                final_url,
                page_title[:120],
                article_div.get_text(" ", strip=True)[:240],
            )
            return ""

        paragraphs = [p.get_text(" ", strip=True) for p in dropcap_div.find_all("p")]
        content = " ".join(p for p in paragraphs if p)
        logger.info(
            "Scrape parsed successfully | slug=%s paragraphs=%s content_chars=%s content_preview=%s",
            slug,
            len(paragraphs),
            len(content),
            content[:240],
        )
        return content
    except Exception as e:
        logger.exception("Failed to scrape content | slug=%s url=%s error=%s", slug, url, e)
        return ""


def run_scraper():
    cursor = None
    stop = False
    total = 0

    while not stop:
        data = fetch_page(cursor)
        nodes = data["nodes"]
        logger.info("Processing fetched nodes | count=%s", len(nodes))

        for node in nodes:
            slug = node["slug"]

            if Article.objects.filter(slug=slug).exists():
                logger.info("Article already exists, stopping scraper loop | slug=%s", slug)
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
                logger.info(
                    "Article created | slug=%s title=%s content_chars=%s",
                    slug,
                    node["title"][:120],
                    len(content),
                )
            except Exception as e:
                logger.exception(
                    "Failed to create article | slug=%s title_len=%s author_len=%s category_len=%s "
                    "description_len=%s image_url_len=%s section_len=%s content_chars=%s error=%s",
                    slug,
                    len(node["title"]),
                    len(node["authors"][0]["name"]) if node["authors"] else 0,
                    len(node["primaryTopic"]["title"]) if node.get("primaryTopic") else 0,
                    len(node.get("standfirstLong", "")),
                    len(node["image"]["url"]) if node.get("image") else 0,
                    len(node["section"]["slug"]) if node.get("section") else 0,
                    len(content),
                    e,
                )
                continue

            total += 1
            if total % 50 == 0:
                logger.info("Scraper progress | total_saved=%s", total)

        if not data["pageInfo"]["hasNextPage"]:
            logger.info("All pages exhausted")
            break

        if not stop:
            cursor = data["pageInfo"]["endCursor"]

    logger.info("Scraper finished | total_saved=%s stop=%s final_cursor=%s", total, stop, cursor)
