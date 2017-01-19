import logging
import time

from collections import deque, namedtuple
from pygc import great_distance, great_circle
from navio.mpu9250 import MPU9250

from .ahrs import AHRS


logger = logging.getLogger(__name__)
Point = namedtuple('Point', ['lat', 'lng'])


def heading_to_point(point_a, point_b):
    """Calculate heading between two points
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return result['azimuth']


def distance_to_point(point_a, point_b):
    """Calculate distance between to points
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return float(result['distance'])


class Compass:

    def __init__(self):
        self.imu = MPU9250()
        self.ahrs = AHRS()
        self._connected = False
        if self.imu.testConnection():
            logger.info("Connection established: True")
            self.imu.initialize()
            self._connected = True
        else:
            logger.error('Could not connect to IMU')

    @property
    def heading(self):
        if not self._connected:
            return None

        accel, gyro, mag = self.imu.getMotion9()
        self.ahrs.update(accel, gyro, mag)


class Navitgator:

    # target distance is the minimum distance we need to
    # arrive at in order to consider ourselves "arrived"
    # at the waypoint
    TARGET_DISTANCE = 60  # meters

    def __init__(self, gps, compass,
                 left_motor=None, right_motor=None,
                 update_period=1, current_location=None):
        self._running = False
        self.gps = gps
        self.compass = compass
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.target_waypoint = None
        self.target_heading = None
        self.current_location = current_location or Point(lat=49.2827, lng=-123.1207)

        self.update_period = update_period
        self.arrived = False
        self.waypoints = deque()

    def stop(self):
        self._running = False

    def move_to_waypoint(self, waypoint):
        self.arrived = False
        self.target_waypoint = waypoint
        self.target_heading = heading_to_point(self.current_location, waypoint)

    def start_trip(self, waypoints=None):
        if waypoints:
            self.waypoints = deque(waypoints)
        self.move_to_waypoint(self.waypoints.popleft())

    def pause_trip(self):
        # push the current waypoint back on the stack
        self.waypoints.appendleft(self.target_waypoint)
        self.target_waypoint = None

    def update(self):
        """Update the current position and heading
        """
        # update current location
        # self.current_location = self.gps

        if self.target_waypoint and not self.arrived:
            # update compass heading if we have a target waypoint
            self.compass.heading = heading_to_point(self.current_location,
                                                    self.target_waypoint)
            # check if we have hit our target
            if self.distance_to_target <= self.TARGET_DISTANCE:
                try:
                    # if there are waypoints qued up keep going
                    self.move_to_waypoint(self.waypoints.popleft())
                except IndexError:
                    # otherwise we have arrived
                    self.arrived = True
                    logger.info('Arrived at Waypoint({}, {})'.format(self.target_waypoint.lat,
                                                                     self.target_waypoint.lng))

    @property
    def distance_to_target(self):
        if self.target_waypoint:
            return distance_to_point(self.current_location, self.target_waypoint)
        else:
            return None

    def run(self):
        logger.info('Starting simulation')
        self._running = True
        while self._running:
            self.update()
            time.sleep(self.update_period)


class Trip:

    def __init__(self, pk, waypoints):
        self.pk = pk
        self.waypoints = [Point(lat=w['lat'], lng=w['lng']) for w in waypoints]
