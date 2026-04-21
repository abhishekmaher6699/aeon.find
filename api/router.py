from ninja import NinjaAPI, Schema
import logging
from recommender.engine import recommend_by_url, recommend_by_prompt
from recommender.models import RecommendationFeedback

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


class FeedbackRecommendation(Schema):
    url: str
    title: str


class RecommendationFeedbackRequest(Schema):
    surface: str
    input_type: str
    input_value: str
    vote: str
    recommendations: list[FeedbackRecommendation]


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


@api.post("/feedback/recommendation")
def save_recommendation_feedback(request, payload: RecommendationFeedbackRequest):
    valid_surfaces = {choice[0] for choice in RecommendationFeedback.SURFACE_CHOICES}
    valid_input_types = {choice[0] for choice in RecommendationFeedback.INPUT_TYPE_CHOICES}
    valid_votes = {choice[0] for choice in RecommendationFeedback.VOTE_CHOICES}

    if payload.surface not in valid_surfaces:
        return api.create_response(request, {"error": "Invalid surface."}, status=400)
    if payload.input_type not in valid_input_types:
        return api.create_response(request, {"error": "Invalid input type."}, status=400)
    if payload.vote not in valid_votes:
        return api.create_response(request, {"error": "Invalid vote."}, status=400)
    if not payload.input_value.strip():
        return api.create_response(request, {"error": "Input value is required."}, status=400)
    if not payload.recommendations:
        return api.create_response(request, {"error": "At least one recommendation is required."}, status=400)

    feedback = RecommendationFeedback.objects.create(
        surface=payload.surface,
        input_type=payload.input_type,
        input_value=payload.input_value.strip(),
        vote=payload.vote,
        recommendations=[
            {
                "url": item.url,
                "title": item.title,
            }
            for item in payload.recommendations
        ],
    )

    logger.info(
        "Feedback saved | id=%s surface=%s input_type=%s vote=%s count=%s",
        feedback.id,
        feedback.surface,
        feedback.input_type,
        feedback.vote,
        len(feedback.recommendations),
    )

    return {"success": True, "id": feedback.id}
