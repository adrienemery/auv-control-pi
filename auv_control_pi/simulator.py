import time

from pygc import great_circle
from .utils import heading_to_point, distance_to_point, Point


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


class Simulator:

    # target distance is the minimum distance we need to
    # arrive at in order to consider ourselves "arrived"
    # at the waypoint
    TARGET_DISTANCE = 20  # meters

    def __init__(self, gps, compass,
                 motor_port=None, motor_starboard=None,
                 update_period=1, current_location=None):
        self._gps = gps
        self._compass = compass
        self._motor_port = motor_port
        self._motor_starboard = motor_starboard
        self._running = False
        self._target_waypoint = None
        self._current_location = current_location or Point(lat=49.2827, lng=-123.1207)

        self.update_period = update_period
        self.speed = 0  # [m/s]
        self.arrived = False

    def stop(self):
        self._running = False

    def move_to_waypoint(self, waypoint):
        self._target_waypoint = waypoint
        self._compass.heading = heading_to_point(self._current_location, waypoint)
        self.speed = 10

    def _update(self):
        """Update the current position and heading"""
        if self.speed:
            # update current position based on speed
            distance = self.speed * self.update_period
            result = great_circle(distance=distance,
                                  azimuth=self._compass.heading,
                                  latitude=self._current_location.lat,
                                  longitude=self._current_location.lng)
            self._current_location = Point(result['latitude'], result['longitude'])

        if self._target_waypoint:
            # update compass heading if we have a target waypoint
            self._compass.heading = heading_to_point(self._current_location,
                                                     self._target_waypoint)
            # check if we have hit our target
            if self._distane_to_target() <= self.TARGET_DISTANCE:
                self.arrived = True

    def _distane_to_target(self):
        return distance_to_point(self._current_location, self._target_waypoint)

    def run(self):
        self._running = True
        while self._running:
            self._update()
            time.sleep(self.update_period)




