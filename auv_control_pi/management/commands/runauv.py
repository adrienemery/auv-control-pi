import logging
import curio

from django.core.management.base import BaseCommand
from auv_control_pi.auv_control import mothership

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):
        curio.run(mothership.run())
