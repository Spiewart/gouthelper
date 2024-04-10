from django.apps import apps
from django.core.management.base import BaseCommand

from ...services import update_defaults


class Command(BaseCommand):
    help = "Update the Defaults table in the database."

    def handle(self, *args, **options):
        update_defaults(apps, None)
        self.stdout.write(self.style.SUCCESS("Successfully updated GoutHelper defaults."))
