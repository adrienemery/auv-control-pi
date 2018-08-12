import asyncio
import logging

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
        # config = Configuration.get_solo()
        # self.left_motor = Motor(name='left', rc_channel=config.left_motor_channel)
        # self.right_motor = Motor(name='right', rc_channel=config.right_motor_channel)

        self.left_motor = Motor(name='left', rc_channel=10)
        self.right_motor = Motor(name='right', rc_channel=11)

        self.reverse_speed = 0
        self.forward_speed = 0
        self.throttle = 0
        self.turn_speed = 0
        self.update_frequency = 5

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm)

    def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")
        self.left_motor.initialize()
        self.right_motor.initialize()

        self.register(self.set_left_motor_speed, 'auv.set_left_motor_speed')
        self.register(self.set_right_motor_speed, 'auv.set_right_motor_speed')
        self.register(self.forward_throttle, 'auv.forward_throttle')
        self.register(self.reverse_throttle, 'auv.reverse_throttle')
        self.register(self.move_right, 'auv.move_right')
        self.register(self.move_left, 'auv.move_left')
        self.register(self.move_center, 'auv.move_center')
        self.register(self.stop, 'auv.stop')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    def set_left_motor_speed(self, speed):
        self.left_motor.speed = int(speed)

    def set_right_motor_speed(self, speed):
        self.right_motor.speed = int(speed)

    def move_right(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn

        To move right we adjust the right motor to a percentage of the speed
        of the left motor
        """
        self.turn_speed = abs(int(turn_speed))
        logger.info('Move right with speed {}'.format(turn_speed))
        self.right_motor.speed = round(self.throttle * ((100 - self.turn_speed) / 100))
        self.left_motor.speed = self.throttle

    def move_left(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn
        """
        logger.info('Move left with speed {}'.format(turn_speed))
        self.turn_speed = -abs(int(turn_speed))
        self.left_motor.speed = round(self.throttle * ((100 + self.turn_speed) / 100))
        self.right_motor.speed = self.throttle

    def move_center(self):
        """Remove any turn from the motors
        """
        self.turn_speed = 0
        self.left_motor.speed = self.throttle
        self.right_motor.speed = self.throttle

    def rotate_right(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.info('Rotate right with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.forward(speed)
        self.right_motor.reverse(speed)

    def rotate_left(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.info('Rotate left with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.reverse(speed)
        self.right_motor.forward(speed)

    def forward_throttle(self, throttle):
        logger.info('Setting forward throttle to {}'.format(throttle))
        self.throttle = abs(int(throttle))
        if self.turn_speed > 0:
            self.move_right(self.turn_speed)
        elif self.turn_speed < 0:
            self.move_left(self.turn_speed)
        else:
            self.left_motor.forward(self.throttle)
            self.right_motor.forward(self.throttle)

    def reverse_throttle(self, throttle):
        self.throttle = -(abs(int(throttle)))
        logger.info('Move reverse with speed {}'.format(throttle))
        if self.turn_speed > 0:
            self.move_right(self.turn_speed)
        elif self.turn_speed < 0:
            self.move_left(self.turn_speed)
        else:
            self.left_motor.reverse(self.throttle)
            self.right_motor.reverse(self.throttle)

    def stop(self):
        logger.info('Stopping')
        self.left_motor.stop()
        self.right_motor.stop()

    async def _update(self):
        """Broadcast current state on the auv update channel"""
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
            logger.debug('Publish ASV udpate')
            await asyncio.sleep(1 / self.update_frequency)


if __name__ == '__main__':
    runner = ApplicationRunner(url='ws://localhost:8000/ws', realm='realm1')
    runner.run(Mothership)
