import hashlib
import json

from django.db import migrations, models


DEFAULT_RECOMMENDER_VERSION = "tfidf-embedding-v1"


def backfill_feedback_metadata(apps, schema_editor):
    RecommendationFeedback = apps.get_model("recommender", "RecommendationFeedback")

    for feedback in RecommendationFeedback.objects.all().iterator():
        payload = {
            "input_type": feedback.input_type,
            "input_value": feedback.input_value.strip(),
            "recommendation_urls": [
                item.get("url", "")
                for item in (feedback.recommendations or [])
            ],
            "recommender_version": DEFAULT_RECOMMENDER_VERSION,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        feedback.result_set_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        feedback.recommender_version = DEFAULT_RECOMMENDER_VERSION
        if not feedback.anonymous_id:
            feedback.anonymous_id = f"legacy-{feedback.pk}"
        feedback.save(update_fields=["anonymous_id", "result_set_id", "recommender_version"])


class Migration(migrations.Migration):

    dependencies = [
        ("recommender", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendationfeedback",
            name="anonymous_id",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="recommendationfeedback",
            name="recommender_version",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="recommendationfeedback",
            name="result_set_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.RunPython(backfill_feedback_metadata, migrations.RunPython.noop),
    ]
