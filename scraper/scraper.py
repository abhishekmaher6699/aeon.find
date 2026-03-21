import httpx
import time
from bs4 import BeautifulSoup
from .models import Article

import logging
import os

os.makedirs('logs', exist_ok=True)

logger = logging.getLogger('scraper')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler('logs/scraper_errors.log')
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(handler)

GRAPHQL_URL = "https://api.aeonmedia.co/graphql"

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
    response = httpx.post(GRAPHQL_URL, json={"query": QUERY, "variables": variables}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()["data"]["articles"]


def scrape_content(slug):
    # time.sleep(0.5)
    url = f"https://aeon.co/essays/{slug}"
    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        if response.status_code == 429:
            print(f"Rate limited on {slug}, waiting 10s...")
            time.sleep(10)
            response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        article_div = soup.find(id="article-content")
        if not article_div:
            return ""
        dropcap_div = article_div.find(class_="has-dropcap")
        if not dropcap_div:
            return ""
        return " ".join(p.get_text() for p in dropcap_div.find_all("p"))
    except Exception as e:
        print(f"Failed to scrape content for {slug}: {e}")
        return ""


def run_scraper():
    cursor = None
    stop = False
    total = 0

    while not stop:
        data = fetch_page(cursor)
        nodes = data["nodes"]

        for node in nodes:
            slug = node["slug"]

            if Article.objects.filter(slug=slug).exists():
                print(f"Already exists, stopping: {slug}")
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
            except Exception as e:
                error_msg = (
                    f"FAILED: {slug} | Error: {e} | "
                    f"title={len(node['title'])} | "
                    f"author={len(node['authors'][0]['name']) if node['authors'] else 0} | "
                    f"category={len(node['primaryTopic']['title']) if node.get('primaryTopic') else 0} | "
                    f"slug={len(slug)} | "
                    f"description={len(node.get('standfirstLong', ''))} | "
                    f"image_url={len(node['image']['url']) if node.get('image') else 0} | "
                    f"section={len(node['section']['slug']) if node.get('section') else 0}"
                )
                logger.error(error_msg)
                print(f"FAILED: {slug} — logged to logs/scraper_errors.log")
                continue  # skip to next article

            total += 1  # move this inside try, after Article.objects.create
            if total % 50 == 0:
                print(f"Total articles saved: {total}")

        if not data["pageInfo"]["hasNextPage"]:
            print("All pages exhausted.")
            break

        if not stop:
            cursor = data["pageInfo"]["endCursor"]

    print(f"Scraper done. Total saved: {total}")