from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RecommendationFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("surface", models.CharField(choices=[("web", "Web"), ("extension", "Extension")], max_length=20)),
                ("input_type", models.CharField(choices=[("prompt", "Prompt"), ("url", "URL")], max_length=20)),
                ("input_value", models.TextField()),
                ("vote", models.CharField(choices=[("useful", "Useful"), ("not_useful", "Not useful")], max_length=20)),
                ("recommendations", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
