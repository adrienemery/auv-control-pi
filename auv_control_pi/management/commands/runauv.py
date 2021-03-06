import logging

from autobahn.asyncio.component import Component, run
from django.core.management.base import BaseCommand
from auv_control_pi.components.auv_control import AUV

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):
        auv_comp = Component(
            transports="ws://crossbar:8080/ws",
            realm="realm1",
            session_factory=AUV,
        )
        run([auv_comp])
