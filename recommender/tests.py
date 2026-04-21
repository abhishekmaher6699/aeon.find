import json

from django.test import Client, TestCase

from .models import RecommendationFeedback


class RecommendationFeedbackApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.base_payload = {
            "anonymous_id": "anon-123",
            "surface": "web",
            "input_type": "prompt",
            "input_value": "philosophy of mind",
            "vote": "useful",
            "recommendations": [
                {"url": "https://aeon.co/essays/example-one", "title": "Example One"},
                {"url": "https://aeon.co/essays/example-two", "title": "Example Two"},
            ],
        }

    def test_feedback_is_saved(self):
        response = self.client.post(
            "/api/feedback/recommendation",
            data=json.dumps(self.base_payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecommendationFeedback.objects.count(), 1)
        payload = response.json()

        feedback = RecommendationFeedback.objects.get()
        self.assertTrue(payload["created"])
        self.assertEqual(payload["summary"]["total_votes"], 1)
        self.assertEqual(payload["summary"]["useful_percentage"], 100)
        self.assertTrue(feedback.result_set_id)
        self.assertEqual(feedback.recommender_version, "tfidf-embedding-v1")
        self.assertEqual(feedback.anonymous_id, "anon-123")
        self.assertEqual(feedback.surface, "web")
        self.assertEqual(feedback.input_type, "prompt")
        self.assertEqual(feedback.vote, "useful")
        self.assertEqual(len(feedback.recommendations), 2)

    def test_feedback_is_deduped_per_anonymous_id_and_result_set(self):
        first = self.client.post(
            "/api/feedback/recommendation",
            data=json.dumps(self.base_payload),
            content_type="application/json",
        )
        second_payload = dict(self.base_payload)
        second_payload["vote"] = "not_useful"
        second = self.client.post(
            "/api/feedback/recommendation",
            data=json.dumps(second_payload),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(RecommendationFeedback.objects.count(), 1)

        feedback = RecommendationFeedback.objects.get()
        self.assertEqual(feedback.vote, "not_useful")
        self.assertFalse(second.json()["created"])
        self.assertEqual(second.json()["summary"]["total_votes"], 1)
        self.assertEqual(second.json()["summary"]["useful_percentage"], 0)

    def test_feedback_rejects_invalid_vote(self):
        invalid_payload = dict(self.base_payload)
        invalid_payload["vote"] = "maybe"
        response = self.client.post(
            "/api/feedback/recommendation",
            data=json.dumps(invalid_payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(RecommendationFeedback.objects.count(), 0)

    def test_feedback_context_returns_summary(self):
        self.client.post(
            "/api/feedback/recommendation",
            data=json.dumps(self.base_payload),
            content_type="application/json",
        )

        response = self.client.post(
            "/api/feedback/recommendation/context",
            data=json.dumps(
                {
                    "input_type": "prompt",
                    "input_value": "philosophy of mind",
                    "recommendations": self.base_payload["recommendations"],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recommender_version"], "tfidf-embedding-v1")
        self.assertEqual(payload["summary"]["total_votes"], 1)
        self.assertEqual(payload["summary"]["useful_percentage"], 100)
