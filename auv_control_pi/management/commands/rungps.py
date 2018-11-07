import logging

from autobahn.asyncio.component import Component, run
from django.core.management.base import BaseCommand
from auv_control_pi.components.gps import GPSComponent

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):
        comp = Component(
            transports="ws://crossbar:8080/ws",
            realm="realm1",
            session_factory=GPSComponent,
        )
        run([comp])
