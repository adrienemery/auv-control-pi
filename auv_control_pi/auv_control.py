import curio
import logging

from collections import deque
from django.conf import settings

# from navio import pwm
from django.utils import timezone

from .asgi import channel_layer, AUV_SEND_CHANNEL, auv_update_group
from .navigation import Point
from .models import Configuration


if settings.SIMULATE:
    from .simulator import GPS, Compass, Navitgator, Motor
else:
    from navio.gps import GPS
    from navio.compass import Compass  # TODO
    from .motor import Motor
    from .navigation import Navigator


logger = logging.getLogger(__name__)


class Mothership:
    """Main entry point for controling the Mothership and AUV
    """

    MANUAL = 'manual'
    LOITER = 'loiter'
    TRIP = 'trip'
    MOVE_TO_WAYPOINT = 'move_to_waypoint'

    def __init__(self):
        self.lat = 0.0
        self.lng = 0.0
        self.heading = 0
        self.speed = 0
        self.water_temperature = 0
        self.command_buffer = deque()
        config = Configuration.get_solo()
        self.left_motor = Motor(config.left_motor_channel)
        self.right_motor = Motor(config.right_motor_channel)
        self.mode = self.MANUAL
        self.waypoints = deque()
        self._gps = GPS()
        self._compass = Compass()
        if settings.SIMULATE:
            self._navigator = Navitgator(gps=self._gps, compass=self._compass,
                                         right_motor=self.right_motor,
                                         left_motor=self.left_motor)
        else:
            self._navigator = Navigator()

    async def _move_right(self, speed=None):
        if speed is None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = -abs(speed)
        logger.debug('Left Motor Speed: {}'.format(self.left_motor.speed))
        logger.debug('Right Motor Speed: {}'.format(self.right_motor.speed))

    async def _move_left(self, speed=None):
        if speed is None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = abs(speed)
        logger.debug('Left Motor Speed: {}'.format(self.left_motor.speed))
        logger.debug('Right Motor Speed: {}'.format(self.right_motor.speed))

    async def _stop(self):
        self._navigator.stop_trip()
        self.left_motor.speed = 0
        self.right_motor.speed = 0
        logger.debug('Left Motor Speed: {}'.format(self.left_motor.speed))
        logger.debug('Right Motor Speed: {}'.format(self.right_motor.speed))

    async def _move_forward(self, speed=None):
        if speed is not None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = abs(speed)
        logger.debug('Left Motor Speed: {}'.format(self.left_motor.speed))
        logger.debug('Right Motor Speed: {}'.format(self.right_motor.speed))

    async def _move_reverse(self, speed=None):
        if speed is not None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = -abs(speed)
        logger.debug('Left Motor Speed: {}'.format(self.left_motor.speed))
        logger.debug('Right Motor Speed: {}'.format(self.right_motor.speed))

    async def move_right(self, speed=None, **kwargs):
        await self._move_right(speed)
        logger.info('Move right with speed {}'.format(speed))

    async def move_left(self, speed=None, **kwargs):
        await self._move_left(speed)
        logger.info('Move left with speed {}'.format(speed))

    async def move_forward(self, speed=None, **kwargs):
        await self._move_forward(speed)
        logger.info('Move forward with speed {}'.format(speed))

    async def move_reverse(self, speed=None, **kwargs):
        await self._move_reverse(speed)
        logger.info('Move reverse with speed {}'.format(speed))

    async def stop(self, **kwargs):
        await self._stop()
        logger.info('Stopping')

    async def move_to_waypoint(self, lat, lng, **kwargs):
        self._navigator.move_to_waypoint(Point(lat=lat, lng=lng))
        self.mode = self.MOVE_TO_WAYPOINT
        logger.info('Moving to waypoint: ({}, {})'.format(lat, lng))

    async def start_trip(self, waypoints, **kwargs):
        self._navigator.start_trip(waypoints)
        self.mode = self.TRIP
        logger.info('Starting trip')

    async def send(self, msg):
        self.command_buffer.append(msg)

    async def _run_navigator(self):
        await curio.run_in_thread(self._navigator.run)

    async def _read_commands(self):
        # check for commands to send to auv
        channels = [AUV_SEND_CHANNEL]
        # read all messages off of channel
        while True:
            _, data = channel_layer.receive_many(channels)
            if data:
                logger.debug('Recieved data: {}'.format(data))
                try:
                    fnc = getattr(self, data.get('cmd'))
                except AttributeError:
                    pass
                else:
                    if fnc and callable(fnc):
                        await fnc(**data.get('kwargs', {}))
            else:
                await curio.sleep(0.05)  # chill out for a bit

    async def run(self):
        logger.info('Starting Mothership')
        await curio.spawn(self._update())
        await curio.spawn(self._run_navigator())
        logger.info('Running main loop')
        await self._read_commands()

    async def _update(self):
        """Broadcast current state on the auv update channel"""
        while True:
            payload = {
                'lat': self._gps.lat,
                'lng': self._gps.lng,
                'heading': self._compass.heading,
                'speed': self._navigator.speed,
                'left_motor_speed': self.left_motor.speed,
                'right_motor_speed': self.right_motor.speed,
                'distance_to_target': self._navigator.distance_to_target,
                'mode': self.mode,
                'arrived': self._navigator.arrived,
                'timestamp': timezone.now().isoformat()
            }
            if self._navigator.target_waypoint:
                payload['target_waypoint'] = {
                    'lat': self._navigator.target_waypoint.lat,
                    'lng': self._navigator.target_waypoint.lng
                }
            else:
                payload['target_waypoint'] = None

            # broadcast auv data to group
            auv_update_group.send(payload)
            logger.debug('Broadcast udpate')
            await curio.sleep(1)


mothership = Mothership()

if __name__ == '__main__':
    curio.run(mothership.run())
