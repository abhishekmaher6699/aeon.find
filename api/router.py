from ninja import NinjaAPI, Schema
import logging
from recommender.engine import recommend_by_url, recommend_by_prompt
from recommender.feedback import build_feedback_context, get_feedback_summary, normalize_recommendations
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
    anonymous_id: str
    surface: str
    input_type: str
    input_value: str
    vote: str
    recommendations: list[FeedbackRecommendation]


class RecommendationFeedbackContextRequest(Schema):
    input_type: str
    input_value: str
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


@api.post("/feedback/recommendation/context")
def get_recommendation_feedback_context(request, payload: RecommendationFeedbackContextRequest):
    valid_input_types = {choice[0] for choice in RecommendationFeedback.INPUT_TYPE_CHOICES}

    if payload.input_type not in valid_input_types:
        return api.create_response(request, {"error": "Invalid input type."}, status=400)
    if not payload.input_value.strip():
        return api.create_response(request, {"error": "Input value is required."}, status=400)
    if not payload.recommendations:
        return api.create_response(request, {"error": "At least one recommendation is required."}, status=400)

    context = build_feedback_context(
        input_type=payload.input_type,
        input_value=payload.input_value.strip(),
        recommendations=normalize_recommendations(
            [{"url": item.url, "title": item.title} for item in payload.recommendations]
        ),
    )
    return context


@api.post("/feedback/recommendation")
def save_recommendation_feedback(request, payload: RecommendationFeedbackRequest):
    valid_surfaces = {choice[0] for choice in RecommendationFeedback.SURFACE_CHOICES}
    valid_input_types = {choice[0] for choice in RecommendationFeedback.INPUT_TYPE_CHOICES}
    valid_votes = {choice[0] for choice in RecommendationFeedback.VOTE_CHOICES}

    if not payload.anonymous_id.strip():
        return api.create_response(request, {"error": "Anonymous ID is required."}, status=400)
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

    normalized_recommendations = normalize_recommendations(
        [{"url": item.url, "title": item.title} for item in payload.recommendations]
    )
    feedback_context = build_feedback_context(
        input_type=payload.input_type,
        input_value=payload.input_value.strip(),
        recommendations=normalized_recommendations,
    )

    feedback, created = RecommendationFeedback.objects.update_or_create(
        anonymous_id=payload.anonymous_id.strip(),
        result_set_id=feedback_context["result_set_id"],
        defaults={
            "surface": payload.surface,
            "input_type": payload.input_type,
            "input_value": payload.input_value.strip(),
            "vote": payload.vote,
            "recommendations": normalized_recommendations,
            "recommender_version": feedback_context["recommender_version"],
        },
    )

    logger.info(
        "Feedback saved | id=%s created=%s result_set_id=%s vote=%s count=%s",
        feedback.id,
        created,
        feedback.result_set_id,
        feedback.vote,
        len(feedback.recommendations),
    )

    summary = get_feedback_summary(feedback.result_set_id)

    return {
        "success": True,
        "id": feedback.id,
        "created": created,
        "result_set_id": feedback.result_set_id,
        "recommender_version": feedback.recommender_version,
        "summary": summary,
    }
