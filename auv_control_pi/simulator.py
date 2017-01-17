import logging
import time
from collections import deque

from pygc import great_circle
from .navigation import heading_to_point, distance_to_point, Point


logger = logging.getLogger(__name__)


class GPS:

    def __init__(self):
        self.lat = 49.2827
        self.lng = -123.1207


class Compass:

    def __init__(self):
        self.heading = 0


class Motor:

    def __init__(self, name):
        self.name = name
        self.speed = 0

    def __repr__(self):
        return 'Motor({})'.format(self.name)


class Navitgator:

    # target distance is the minimum distance we need to
    # arrive at in order to consider ourselves "arrived"
    # at the waypoint
    TARGET_DISTANCE = 20  # meters

    def __init__(self, gps, compass,
                 left_motor=None, right_motor=None,
                 update_period=1, current_location=None):
        self._gps = gps
        self._compass = compass
        self._left_motor = left_motor
        self._right_motor = right_motor
        self._running = False
        self.target_waypoint = None
        self._current_location = current_location or Point(lat=49.2827, lng=-123.1207)

        self.update_period = update_period
        self.speed = 0  # [m/s]
        self.arrived = False
        self.waypoints = deque()

    def stop(self):
        self._running = False

    def move_to_waypoint(self, waypoint):
        self.arrived = False
        self.target_waypoint = waypoint
        self._compass.heading = heading_to_point(self._current_location, waypoint)
        self.speed = 50

    def start_trip(self, waypoints=None):
        if waypoints:
            self.waypoints = deque(waypoints)
        self.move_to_waypoint(self.waypoints.popleft())

    def pause_trip(self):
        # push the current waypoint back on the stack
        self.waypoints.appendleft(self.target_waypoint)
        self.target_waypoint = None

    def _update(self):
        """Update the current position and heading"""
        # update current position based on speed
        distance = self.speed * self.update_period
        result = great_circle(distance=distance,
                              azimuth=self._compass.heading,
                              latitude=self._current_location.lat,
                              longitude=self._current_location.lng)
        self._current_location = Point(result['latitude'], result['longitude'])
        self._gps.lat = self._current_location.lat
        self._gps.lng = self._current_location.lng

        if self.target_waypoint and not self.arrived:
            # update compass heading if we have a target waypoint
            self._compass.heading = heading_to_point(self._current_location,
                                                     self.target_waypoint)
            # check if we have hit our target
            if self.distance_to_target <= self.TARGET_DISTANCE:
                try:
                    # if there are waypoints qued up keep going
                    self.move_to_waypoint(self.waypoints.popleft())
                except IndexError:
                    # otherwise we have arrived
                    self.arrived = True
                    self.speed = 0
                    logger.info('Arrived at Waypoint({}, {})'.format(self.target_waypoint.lat,
                                                                     self.target_waypoint.lng))

        else:
            # update heading and speed based on motor speeds
            self.speed = (self._left_motor.speed + self._right_motor.speed) // 2
            self._compass.heading += ((self._left_motor.speed - self._right_motor.speed) / 10)
            self._compass.heading = abs(self._compass.heading % 360)

    @property
    def distance_to_target(self):
        if self.target_waypoint:
            return distance_to_point(self._current_location, self.target_waypoint)
        else:
            return None

    def run(self):
        logger.info('Starting simulation')
        self._running = True
        while self._running:
            self._update()
            time.sleep(self.update_period)
