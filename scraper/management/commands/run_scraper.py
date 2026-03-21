from django.core.management.base import BaseCommand
from scraper.scraper import run_scraper

class Command(BaseCommand):
    help = "Scrape new Aeon essays and save to DB"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting scraper")
        run_scraper()
        self.stdout.write("Done.")
