from django.apps import apps
from django.core.management.base import BaseCommand

from ...services import create_or_update_contents


class Command(BaseCommand):
    help = "Update the Contents table in the database with \
the contents of the markdown\\/contents directory."

    def handle(self, *args, **options):
        create_or_update_contents(apps, None)
        self.stdout.write(self.style.SUCCESS("Successfully updated contents."))
