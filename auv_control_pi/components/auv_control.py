import asyncio
import logging

from ..models import Configuration, AUVLog
from ..motors import Motor
from ..wamp import ApplicationSession, rpc

logger = logging.getLogger(__name__)
config = Configuration.get_solo()


def get_motor_speed(throttle, turn_speed):
    turn_speed = abs(turn_speed)
    motor_speed = 100 - turn_speed * 2
    motor_speed = round(throttle * motor_speed / 100)
    return motor_speed


class AUV(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """

    update_method = 'update'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.left_motor = Motor(name='left', rc_channel=config.left_motor_channel)
        # self.right_motor = Motor(name='right', rc_channel=config.right_motor_channel)

        self.left_motor = Motor(name='left', rc_channel=10)
        self.right_motor = Motor(name='right', rc_channel=11)

        # TODO determine if the trim required is a function of motor speed

        # load the current trim value from the database
        self.trim = config.trim
        self.throttle = 0
        self.throttle_limit = 90
        self.turn_speed = 0
        self.update_frequency = 10

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm)

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops
        """
        # arming/disarming the rc controller could arm/disarm the motors
        # as well as doing it from web interface
        self.left_motor.initialize()
        self.right_motor.initialize()
        await super().onJoin(details)

    @rpc('auv.set_left_motor_speed')
    def set_left_motor_speed(self, speed):
        self.left_motor.speed = int(speed)

    @rpc('auv.set_right_motor_speed')
    def set_right_motor_speed(self, speed):
        self.right_motor.speed = int(speed)

    @rpc('auv.set_trim')
    def set_trim(self, trim):
        self.trim = int(trim)
        self._move()

        # save trim value to database
        config.trim = self.trim
        config.save()

    @rpc('auv.trim_left')
    def trim_left(self):
        self.set_trim(self.trim - 1)

    @rpc('auv.trim_right')
    def trim_right(self):
        self.set_trim(self.trim + 1)

    def _move(self):
        turn_speed = self.turn_speed + self.trim

        # left turn
        if turn_speed < 0:
            self.right_motor.speed = self.throttle
            self.left_motor.speed = get_motor_speed(self.throttle, turn_speed)

        # right turn
        elif turn_speed > 0:
            self.right_motor.speed = get_motor_speed(self.throttle, turn_speed)
            self.left_motor.speed = self.throttle

        # straight
        else:
            self.right_motor.speed = self.throttle
            self.left_motor.speed = self.throttle

    @rpc('auv.move_right')
    def move_right(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn

        To move right we adjust the right motor to a percentage of the speed
        of the left motor
        """
        self.turn_speed = abs(int(turn_speed))
        logger.debug('Move right with speed {}'.format(turn_speed))
        self._move()

    @rpc('auv.move_left')
    def move_left(self, turn_speed):
        """Adjust the speed of the turning side motor to induce a turn
        """
        logger.debug('Move left with speed {}'.format(turn_speed))
        self.turn_speed = -abs(int(turn_speed))
        self._move()

    @rpc('auv.move_center')
    def move_center(self):
        """Remove any turn from the motors
        """
        self.turn_speed = 0
        self._move()

    @rpc('auv.set_turn_val')
    def set_turn_val(self, turn_speed):
        self.turn_speed = int(turn_speed)
        self._move()

    @rpc('auv.rotate_right')
    def rotate_right(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.debug('Rotate right with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.forward(speed)
        self.right_motor.reverse(speed)

    @rpc('auv.rotate_left')
    def rotate_left(self, speed):
        """Set motors in opposite direction to rotate craft
        """
        logger.debug('Rotate left with speed {}'.format(speed))
        speed = int(speed)
        self.throttle = 0
        self.left_motor.reverse(speed)
        self.right_motor.forward(speed)

    @rpc('auv.set_throttle')
    def set_throttle(self, throttle):
        throttle = int(throttle)
        throttle = max(-self.throttle_limit, throttle)
        throttle = min(self.throttle_limit, throttle)
        self.throttle = throttle
        self._move()

    @rpc('auv.forward_throttle')
    def forward_throttle(self, throttle=0):
        logger.debug('Setting forward throttle to {}'.format(throttle))
        throttle = abs(int(throttle))
        throttle = min(self.throttle_limit, throttle)
        self.throttle = throttle
        self._move()

    @rpc('auv.reverse_throttle')
    def reverse_throttle(self, throttle=0):
        logger.debug('Move reverse with speed {}'.format(throttle))
        throttle = -(abs(int(throttle)))
        throttle = max(-self.throttle_limit, throttle)
        self.throttle = throttle
        self._move()

    @rpc('auv.stop')
    def stop(self):
        logger.info('Stopping')
        self.throttle = 0
        self.turn_speed = 0
        self.left_motor.stop()
        self.right_motor.stop()

    async def update(self):
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
                'trim': self.trim,
                # 'timestamp': timezone.now().isoformat()
            }
            self.publish('auv.update', payload)

            # log to database
            # AUVLog.objects.create(**payload)
            await asyncio.sleep(1 / self.update_frequency)
