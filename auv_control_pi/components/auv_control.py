import asyncio
import logging

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from ..models import Configuration
from ..motors import Motor


logger = logging.getLogger(__name__)


class Mothership(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speed = 0

        # config = Configuration.get_solo()
        # self.left_motor = Motor(name='left', rc_channel=config.left_motor_channel)
        # self.right_motor = Motor(name='right', rc_channel=config.right_motor_channel)

        self.left_motor = Motor(name='left', rc_channel=10)
        self.right_motor = Motor(name='right', rc_channel=11)

        # TODO determine if the trim required is a function of motor speed
        self.trim = 0

        self.throttle = 0
        self.turn_speed = 0
        self.update_frequency = 10

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm)

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops
        """
        logger.info("Joined Crossbar Session")

        # TODO add rpc methods to manually arm/disarm each motor for safety
        # arming/disarming the rc controller could arm/disarm the motors
        # as well as doing it from web interface
        self.left_motor.initialize()
        self.right_motor.initialize()

        await self.register(self.set_left_motor_speed, 'auv.set_left_motor_speed')
        await self.register(self.set_right_motor_speed, 'auv.set_right_motor_speed')
        await self.register(self.set_trim, 'auv.set_trim')
        await self.register(self.trim_right, 'auv.trim_right')
        await self.register(self.trim_left, 'auv.trim_left')
        await self.register(self.forward_throttle, 'auv.forward_throttle')
        await self.register(self.reverse_throttle, 'auv.reverse_throttle')
        await self.register(self.move_right, 'auv.move_right')
        await self.register(self.move_left, 'auv.move_left')
        await self.register(self.move_center, 'auv.move_center')
        await self.register(self.stop, 'auv.stop')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    def set_left_motor_speed(self, speed):
        self.left_motor.speed = int(speed)

    def set_right_motor_speed(self, speed):
        self.right_motor.speed = int(speed)

    def set_trim(self, trim):
        self.trim = int(trim)
        self._move()
        # TODO save trim value to database

    def trim_left(self):
        self.set_trim(self.trim - 1)

    def trim_right(self):
        self.set_trim(self.trim + 1)

    def _move(self):
        turn_speed = self.turn_speed + self.trim

        # left turn
        if turn_speed < 0:
            self.right_motor.speed = self.throttle
            self.left_motor.speed = round(self.throttle * ((100 - abs(turn_speed)) / 100))

        # right turn
        elif turn_speed > 0:
            self.right_motor.speed = round(self.throttle * ((100 - abs(turn_speed)) / 100))
            self.left_motor.speed = self.throttle

        # straight
        else:
            self.right_motor.speed = self.throttle
            self.left_motor.speed = self.throttle

    def move_right(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn

        To move right we adjust the right motor to a percentage of the speed
        of the left motor
        """
        self.turn_speed = abs(int(turn_speed))
        logger.debug('Move right with speed {}'.format(turn_speed))
        self._move()

    def move_left(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn
        """
        logger.debug('Move left with speed {}'.format(turn_speed))
        self.turn_speed = -abs(int(turn_speed))
        self._move()

    def move_center(self):
        """Remove any turn from the motors
        """
        self.turn_speed = 0
        self._move()

    def rotate_right(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.debug('Rotate right with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.forward(speed)
        self.right_motor.reverse(speed)

    def rotate_left(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.debug('Rotate left with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.reverse(speed)
        self.right_motor.forward(speed)

    def forward_throttle(self, throttle):
        logger.debug('Setting forward throttle to {}'.format(throttle))
        self.throttle = abs(int(throttle))
        self._move()

    def reverse_throttle(self, throttle):
        self.throttle = -(abs(int(throttle)))
        logger.debug('Move reverse with speed {}'.format(throttle))
        self._move()

    def stop(self):
        logger.info('Stopping')
        self.throttle = 0
        self.turn_speed = 0
        self.left_motor.stop()
        self.right_motor.stop()

    async def _update(self):
        """Publish current state to anyone listening
        """
        while True:
            payload = {
                'left_motor_speed': self.left_motor.speed,
                'left_motor_duty_cycle': self.left_motor.duty_cycle_ms,
                'right_motor_speed': self.right_motor.speed,
                'right_motor_duty_cycle': self.right_motor.duty_cycle_ms,
                'throttle': self.throttle,
                'turn_speed': self.turn_speed,
                # 'timestamp': timezone.now().isoformat()
            }
            self.publish('auv.update', payload)
            await asyncio.sleep(1 / self.update_frequency)
