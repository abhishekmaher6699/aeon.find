from django.contrib import admin

from .models import RecommendationFeedback


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = ("surface", "input_type", "vote", "short_input", "recommendation_count", "created_at")
    list_filter = ("surface", "input_type", "vote", "created_at")
    search_fields = ("input_value",)
    readonly_fields = ("surface", "input_type", "input_value", "vote", "recommendations", "created_at")

    def short_input(self, obj):
        return obj.input_value[:80]

    short_input.short_description = "Input"

    def recommendation_count(self, obj):
        return len(obj.recommendations)

    recommendation_count.short_description = "Results"
