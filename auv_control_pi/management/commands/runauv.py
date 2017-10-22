import logging
import curio

from django.core.management.base import BaseCommand
from auv_control_pi.auv_control import mothership
from auv_control_pi.motors import motor_controller

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):
        curio.run(self.run())

    async def run(self):
        # await curio.spawn(mothership.run())
        await curio.spawn(motor_controller.run())

