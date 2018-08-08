import asyncio
import logging

from collections import deque
from django.utils import timezone

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from .models import Configuration
from .motors import Motor


logger = logging.getLogger(__name__)


class Mothership(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speed = 0
        self.command_buffer = deque()
        config = Configuration.get_solo()
        self.left_motor = Motor(name='left', wamp_session=self, rc_channel=config.left_motor_channel)
        self.right_motor = Motor(name='right', wamp_session=self, rc_channel=config.right_motor_channel)
        self.update_frequency = 1

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm, authmethods=['anonymous'], authid='auv')

    def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")
        self.left_motor.initialize()
        self.right_motor.initialize()

        self.register(self.move_right, 'auv.move_right')
        self.register(self.move_left, 'auv.move_left')
        self.register(self.set_left_motor_speed, 'auv.set_left_motor_speed')
        self.register(self.set_right_motor_speed, 'auv.set_right_motor_speed')
        self.register(self.move_forward, 'auv.move_forward')
        self.register(self.move_reverse, 'auv.move_reverse')
        self.register(self.stop, 'auv.stop')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    def set_left_motor_speed(self, speed):
        self.left_motor.speed = int(speed)

    def set_right_motor_speed(self, speed):
        self.left_motor.speed = int(speed)

    def move_right(self, speed=None):
        logger.info('Move right with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.forward(speed)
        self.right_motor.reverse(speed)

    def move_left(self, speed=None):
        logger.info('Move left with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.reverse(speed)
        self.right_motor.forward(speed)

    def move_forward(self, speed=None):
        logger.info('Move forward with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.forward(speed)
        self.right_motor.forward(speed)

    def move_reverse(self, speed=None):
        logger.info('Move reverse with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.reverse(speed)
        self.right_motor.reverse(speed)

    def stop(self):
        logger.info('Stopping')
        self._navigator.pause_trip()
        self.left_motor.stop()
        self.right_motor.stop()

    async def _update(self):
        """Broadcast current state on the auv update channel"""
        while True:
            payload = {
                'left_motor_speed': self.left_motor.speed,
                'left_motor_duty_cycle': self.left_motor.duty_cycle,
                'right_motor_speed': self.right_motor.speed,
                'right_motor_duty_cycle': self.right_motor.duty_cycle,
                'timestamp': timezone.now().isoformat()
            }
            self.publish('auv.update', payload)
            logger.debug('Publish ASV udpate')
            await asyncio.sleep(1 / self.update_frequency)


if __name__ == '__main__':
    runner = ApplicationRunner(url='ws://localhost:8000/ws', realm='realm1')
    runner.run(Mothership)
