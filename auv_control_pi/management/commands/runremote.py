import logging

from django.core.management.base import BaseCommand
from auv_control_pi.components.remote_control import main

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):
        main()
