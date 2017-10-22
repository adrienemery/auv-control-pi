import curio
import logging

from collections import deque
from django.conf import settings

from django.utils import timezone

from .asgi import channel_layer, AUV_SEND_CHANNEL
from .navigation import Point, Trip
from .models import Configuration


if settings.SIMULATE:
    from .simulator import Navitgator, Motor
else:
    from .motors import Motor
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
        self.update_frequency = 1
        self.trip = None
        if settings.SIMULATE:
            self._navigator = Navitgator(right_motor=self.right_motor,
                                         left_motor=self.left_motor)
        else:
            self._navigator = Navigator(right_motor=self.right_motor,
                                        left_motor=self.left_motor)

    async def move_right(self, speed=None):
        logger.info('Move right with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = -abs(speed)

    async def move_left(self, speed=None):
        logger.info('Move left with speed {}'.format(speed))
        if speed is None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = abs(speed)

    async def move_forward(self, speed=None):
        logger.info('Move forward with speed {}'.format(speed))
        if speed is not None:
            speed = 50
        self.left_motor.speed = abs(speed)
        self.right_motor.speed = abs(speed)

    async def move_reverse(self, speed=None):
        logger.info('Move reverse with speed {}'.format(speed))
        if speed is not None:
            speed = 50
        self.left_motor.speed = -abs(speed)
        self.right_motor.speed = -abs(speed)

    async def stop(self):
        logger.info('Stopping')
        self._navigator.pause_trip()
        self.left_motor.speed = 0
        self.right_motor.speed = 0

    async def move_to_waypoint(self, lat, lng):
        self._navigator.move_to_waypoint(Point(lat=lat, lng=lng))
        self.mode = self.MOVE_TO_WAYPOINT
        logger.info('Moving to waypoint: ({}, {})'.format(lat, lng))

    async def start_trip(self):
        if self.trip:
            self._navigator.start_trip(self.trip.waypoints)
            self.mode = self.TRIP
            logger.info('Starting trip with id: {}'.format(self.trip.pk))
        logger.warning('No trip set to start')

    async def set_trip(self, trip):
        if trip is not None:
            self.trip = Trip(pk=trip['id'], waypoints=trip['waypoints'])
            logger.info('Trip set with id: {}'.format(trip['id']))
        else:
            self.trip = trip

    async def update_settings(self, **new_settings):
        if new_settings.get('mode') == self.MOVE_TO_WAYPOINT:
            target_lat = new_settings.get('target_lat')
            target_lng = new_settings.get('target_lng')
            if target_lat and target_lng:
                await self.move_to_waypoint(target_lat, target_lng)
        for attr, val in new_settings.items():
            if hasattr(self, attr):
                setattr(self, attr, val)

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
                        try:
                            await fnc(**data.get('kwargs', {}))
                        except Exception as exc:
                            logger.error()
            else:
                await curio.sleep(0.05)  # chill out for a bit

    async def run(self):
        logger.info('Starting Mothership')
        await curio.spawn(self._update())
        await curio.spawn(self._read_commands())
        await curio.run_in_thread(self._navigator.run)

    async def _update(self):
        """Broadcast current state on the auv update channel"""
        while True:
            payload = {
                # 'lat': self._gps.lat,
                # 'lng': self._gps.lng,
                # 'heading': self._compass.heading,
                # 'speed': self._navigator.speed,
                'left_motor_speed': self.left_motor.speed,
                'right_motor_speed': self.right_motor.speed,
                # 'distance_to_target': self._navigator.distance_to_target,
                'mode': self.mode,
                # 'arrived': self._navigator.arrived,
                'timestamp': timezone.now().isoformat()
            }
            # if self._navigator.target_waypoint:
            #     payload['target_waypoint'] = {
            #         'lat': self._navigator.target_waypoint.lat,
            #         'lng': self._navigator.target_waypoint.lng
            #     }
            # else:
            #     payload['target_waypoint'] = None

            # broadcast auv data to group
            # channel_layer.send('auv.update', payload)
            logger.debug('Broadcast udpate')
            await curio.sleep(1 / self.update_frequency)


mothership = Mothership()
