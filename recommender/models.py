from django.db import models


class RecommendationFeedback(models.Model):
    SURFACE_WEB = "web"
    SURFACE_EXTENSION = "extension"
    SURFACE_CHOICES = [
        (SURFACE_WEB, "Web"),
        (SURFACE_EXTENSION, "Extension"),
    ]

    INPUT_PROMPT = "prompt"
    INPUT_URL = "url"
    INPUT_TYPE_CHOICES = [
        (INPUT_PROMPT, "Prompt"),
        (INPUT_URL, "URL"),
    ]

    VOTE_USEFUL = "useful"
    VOTE_NOT_USEFUL = "not_useful"
    VOTE_CHOICES = [
        (VOTE_USEFUL, "Useful"),
        (VOTE_NOT_USEFUL, "Not useful"),
    ]

    surface = models.CharField(max_length=20, choices=SURFACE_CHOICES)
    input_type = models.CharField(max_length=20, choices=INPUT_TYPE_CHOICES)
    input_value = models.TextField()
    vote = models.CharField(max_length=20, choices=VOTE_CHOICES)
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_surface_display()} {self.get_vote_display()} ({self.created_at:%Y-%m-%d %H:%M})"
