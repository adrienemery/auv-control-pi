import json

import curio
import logging

from collections import deque

from channels import Group
from django.conf import settings

from django.utils import timezone

from auv_control_pi.consumers import AsyncConsumer
from .asgi import channel_layer, AUV_SEND_CHANNEL, AUV_UPDATE_CHANNEL
from .navigation import Point, Trip
from .models import Configuration
from .motors import Motor

if settings.SIMULATE:
    from .simulator import Navitgator, GPS
else:
    from .navigation import Navigator


logger = logging.getLogger(__name__)


class Mothership(AsyncConsumer):
    """Main entry point for controling the Mothership and AUV
    """
    channels = [AUV_SEND_CHANNEL]

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
        self.left_motor = Motor(name='left', rc_channel=config.left_motor_channel)
        self.right_motor = Motor(name='right', rc_channel=config.right_motor_channel)
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

    def set_motor_speed(self, motor_side, speed):
        try:
            motor = getattr(self, '{}_motor'.format(motor_side))
            motor.speed = int(speed)
        except AttributeError:
            logger.warning('Motor "{}" does not exist'.format(motor_side))

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

    def move_to_waypoint(self, lat, lng):
        self._navigator.move_to_waypoint(Point(lat=lat, lng=lng))
        self.mode = self.MOVE_TO_WAYPOINT
        logger.info('Moving to waypoint: ({}, {})'.format(lat, lng))

    def start_trip(self):
        if self.trip:
            self._navigator.start_trip(self.trip.waypoints)
            self.mode = self.TRIP
            logger.info('Starting trip with id: {}'.format(self.trip.pk))
        logger.warning('No trip set to start')

    def set_trip(self, trip):
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

    async def run(self):
        logger.info('Starting Mothership')
        await curio.spawn(self._update())
        await curio.spawn(self._read_commands())
        await curio.run_in_thread(self._navigator.run)

    async def _update(self):
        """Broadcast current state on the auv update channel"""
        while True:
            payload = {
                'lat': self.lat,
                'lng': self.lng,
                'heading': self.heading,
                'left_motor_speed': self.left_motor.speed,
                'left_motor_duty_cycle': self.left_motor.duty_cycle,
                'right_motor_speed': self.right_motor.speed,
                'right_motor_duty_cycle': self.right_motor.duty_cycle,
                'mode': self.mode,
                'timestamp': timezone.now().isoformat()
            }

            # broadcast auv data to group
            Group(AUV_UPDATE_CHANNEL).send({'text': json.dumps(payload)})
            logger.debug('Broadcast udpate')
            await curio.sleep(1 / 10)


