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
      slug title standfirstLong
      authors { name }
      primaryTopic { title }
      section { slug }
      image { url }
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


def scrape_content(slug):
    url = f"https://aeon.co/essays/{slug}"
    logger.info("Scraping content | slug=%s url=%s", slug, url)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        if response.status_code == 429:
            logger.warning("Rate limited while scraping | slug=%s wait_seconds=10", slug)
            time.sleep(10)
            response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
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
