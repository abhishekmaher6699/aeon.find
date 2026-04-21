from django.contrib import admin

from .models import RecommendationFeedback


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "surface",
        "input_type",
        "vote",
        "recommender_version",
        "short_result_set_id",
        "short_input",
        "recommendation_count",
        "created_at",
    )
    list_filter = ("surface", "input_type", "vote", "recommender_version", "created_at")
    search_fields = ("input_value", "result_set_id", "anonymous_id")
    readonly_fields = (
        "anonymous_id",
        "result_set_id",
        "recommender_version",
        "surface",
        "input_type",
        "input_value",
        "vote",
        "recommendations",
        "created_at",
    )

    def short_input(self, obj):
        return obj.input_value[:80]

    short_input.short_description = "Input"

    def short_result_set_id(self, obj):
        return obj.result_set_id[:12]

    short_result_set_id.short_description = "Result Set"

    def recommendation_count(self, obj):
        return len(obj.recommendations)

    recommendation_count.short_description = "Results"
