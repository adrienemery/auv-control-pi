import curio
import logging

from collections import deque
from django.conf import settings

# from navio import pwm
from .asgi import channel_layer, AUV_SEND_CHANNEL, auv_update_group
from .config import config
from .navigation import Point


if settings.SIMULATE:
    from .simulator import GPS, Compass, Simulator, Motor
else:
    from navio.gps import GPS
    from navio.compass import Compass  # TODO
    from .motor import Motor
    from .navigation import Navigator


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.debug = print


class Mothership:
    """Main entry point for controling the Mothership and AUV
    """

    MANUAL = 'manual'
    LOITER = 'loiter'
    TRIP = 'trip'

    def __init__(self):
        self.lat = 0.0
        self.lng = 0.0
        self.heading = 0
        self.speed = 0
        self.water_temperature = 0
        self.command_buffer = deque()

        self.left_motor = Motor(config.left_motor_channel)
        self.right_motor = Motor(config.right_motor_channel)
        self.mode = self.MANUAL
        self.waypoints = deque()

        self._gps = GPS()
        self._compass = Compass()
        if settings.SIMULATE:
            self._navigator = Simulator(gps=self._gps, compass=self._compass)
        else:
            self._navigator = Navigator()

    async def _move_right(self, speed=None):
        if speed is None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = -abs(speed)

    async def _move_left(self, speed=None):
        if speed is None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = abs(speed)

    async def _stop(self):
        self._navigator.stop()
        self.left_motor.speed = 0
        self.right_motor.speed = 0

    async def _move_forward(self, speed=None):
        if speed is not None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = abs(speed)

    async def _move_reverse(self, speed=None):
        if speed is not None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = -abs(speed)

    async def move_right(self, speed=None, **kwargs):
        self._move_right(speed)
        logger.info('Move right with speed {}'.format(speed))

    async def move_left(self, speed=None, **kwargs):
        self._move_left(speed)
        logger.info('Move left with speed {}'.format(speed))

    async def move_forward(self, speed=None, **kwargs):
        self._move_forward(speed)
        logger.info('Move forward with speed {}'.format(speed))

    async def move_reverse(self, speed=None, **kwargs):
        self._move_reverse(speed)
        logger.info('Move reverse with speed {}'.format(speed))

    async def stop(self, **kwargs):
        self._stop()
        logger.info('Stopping')

    async def move_to_waypoint(self, lat, lng, **kwargs):
        self._navigator.move_to_waypoint(Point(lat=lat, lng=lng))
        self.mode = self.TRIP
        logger.info('Moving to waypoint: ({}, {})'.format(lat, lng))

    async def start_trip(self, waypoints, **kwargs):
        self._navigator.start_trip(waypoints)
        self.mode = self.TRIP
        logger.info('Starting trip')

    async def send(self, msg):
        self.command_buffer.append(msg)

    async def run(self):
        await curio.spawn(self._update())
        await curio.run_in_thread(self._navigator.run)
        # main loop
        while True:
            # check for commands to send to auv
            channels = [AUV_SEND_CHANNEL]
            # read all messages off of channel
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    print(data)
                    try:
                        fnc = getattr(self, data.get('cmd'))
                    except AttributeError:
                        pass
                    else:
                        if fnc and callable(fnc):
                            await fnc(**data.get('kwargs', {}))
                else:
                    break
            await curio.sleep(0.05)  # chill out for a bit

    async def _update(self):
        """
        Read in data from serial buffer and broadcast on
        the auv update channel.
        """
        while True:
            payload = {
                'lat': self._gps.lat,
                'lng': self._gps.lng,
                'heading': self._compass.heading,
                'speed': self._navigator.speed,
                'left_motor_speed': self.left_motor.speed,
                'right_motor_speed': self.right_motor.speed,
                'mode': self.mode,
            }
            # broadcast auv data to group
            auv_update_group.send(payload)
            logger.debug('Broadcast udpate')
            await curio.sleep(1)


mothership = Mothership()

if __name__ == '__main__':
    curio.run(mothership.run())
