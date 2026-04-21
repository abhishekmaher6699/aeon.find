from ninja import NinjaAPI, Schema
import logging
from recommender.engine import recommend_by_url, recommend_by_prompt

api = NinjaAPI()
logger = logging.getLogger("web")


class UrlRequest(Schema):
    url: str


class PromptRequest(Schema):
    prompt: str


class ArticleResult(Schema):
    url: str
    title: str
    description: str
    image_url: str


@api.post("/recommend/url", response=list[ArticleResult])
def recommend_url(request, payload: UrlRequest):
    logger.info("API recommend_url called | url=%s", payload.url)
    results = recommend_by_url(payload.url)
    logger.info("API recommend_url completed | url=%s count=%s", payload.url, len(results))
    return results


@api.post("/recommend/prompt", response=list[ArticleResult])
def recommend_prompt(request, payload: PromptRequest):
    logger.info("API recommend_prompt called | prompt_chars=%s", len(payload.prompt))
    results = recommend_by_prompt(payload.prompt)
    logger.info("API recommend_prompt completed | count=%s", len(results))
    return results
