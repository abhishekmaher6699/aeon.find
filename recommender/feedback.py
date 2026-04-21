import hashlib
import json

from django.conf import settings

from .models import RecommendationFeedback


def get_recommender_version():
    return settings.RECOMMENDER_VERSION


def normalize_recommendations(recommendations):
    return [
        {
            "url": item["url"],
            "title": item.get("title", ""),
        }
        for item in recommendations
    ]


def build_result_set_id(input_type, input_value, recommendations, recommender_version=None):
    version = recommender_version or get_recommender_version()
    payload = {
        "input_type": input_type,
        "input_value": input_value.strip(),
        "recommendation_urls": [item["url"] for item in normalize_recommendations(recommendations)],
        "recommender_version": version,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_feedback_summary(result_set_id):
    queryset = RecommendationFeedback.objects.filter(result_set_id=result_set_id)
    total_votes = queryset.count()
    useful_votes = queryset.filter(vote=RecommendationFeedback.VOTE_USEFUL).count()
    not_useful_votes = total_votes - useful_votes
    useful_percentage = round((useful_votes / total_votes) * 100) if total_votes else None

    return {
        "total_votes": total_votes,
        "useful_votes": useful_votes,
        "not_useful_votes": not_useful_votes,
        "useful_percentage": useful_percentage,
    }


def build_feedback_context(input_type, input_value, recommendations):
    normalized = normalize_recommendations(recommendations)
    recommender_version = get_recommender_version()
    result_set_id = build_result_set_id(
        input_type=input_type,
        input_value=input_value,
        recommendations=normalized,
        recommender_version=recommender_version,
    )

    return {
        "result_set_id": result_set_id,
        "recommender_version": recommender_version,
        "recommendations": normalized,
        "summary": get_feedback_summary(result_set_id),
    }
