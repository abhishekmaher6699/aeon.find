from django.core.management.base import BaseCommand
from recommender.builder import build_and_save

class Command(BaseCommand):
    help = "Build and save TF-IDF recommendation model"

    def handle(self, *args, **kwargs):
        self.stdout.write("Building models...")
        build_and_save()
        self.stdout.write("Done.")