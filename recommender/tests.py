from django.test import Client, TestCase

from .models import RecommendationFeedback


class RecommendationFeedbackApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_feedback_is_saved(self):
        response = self.client.post(
            "/api/feedback/recommendation",
            data={
                "surface": "web",
                "input_type": "prompt",
                "input_value": "philosophy of mind",
                "vote": "useful",
                "recommendations": [
                    {"url": "https://aeon.co/essays/example-one", "title": "Example One"},
                    {"url": "https://aeon.co/essays/example-two", "title": "Example Two"},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecommendationFeedback.objects.count(), 1)

        feedback = RecommendationFeedback.objects.get()
        self.assertEqual(feedback.surface, "web")
        self.assertEqual(feedback.input_type, "prompt")
        self.assertEqual(feedback.vote, "useful")
        self.assertEqual(len(feedback.recommendations), 2)

    def test_feedback_rejects_invalid_vote(self):
        response = self.client.post(
            "/api/feedback/recommendation",
            data={
                "surface": "web",
                "input_type": "prompt",
                "input_value": "philosophy of mind",
                "vote": "maybe",
                "recommendations": [
                    {"url": "https://aeon.co/essays/example-one", "title": "Example One"},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(RecommendationFeedback.objects.count(), 0)
