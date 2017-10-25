import curio

from django.core.management.base import BaseCommand
from auv_control_pi.auv_control import Mothership
from auv_control_pi.motors import motor_controller


class Command(BaseCommand):

    def handle(self, *args, **options):
        curio.run(self.run())

    async def run(self):
        await curio.spawn(motor_controller.run())
        mothership = Mothership()
        await curio.spawn(mothership.run())


