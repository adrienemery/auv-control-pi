from django.core.management.base import BaseCommand
from ...models import Configuration


class Command(BaseCommand):

    def handle(self, *args, **options):
        # create config object if it doesn't already exist
        Configuration.get_solo()
