from ninja import NinjaAPI, Schema
from recommender.engine import recommend_by_url, recommend_by_prompt

api = NinjaAPI()


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
    return recommend_by_url(payload.url)


@api.post("/recommend/prompt", response=list[ArticleResult])
def recommend_prompt(request, payload: PromptRequest):
    return recommend_by_prompt(payload.prompt)