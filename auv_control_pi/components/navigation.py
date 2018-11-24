import os
import asyncio
import logging

from collections import deque, namedtuple
from pygc import great_distance
from autobahn.asyncio.wamp import ApplicationSession
from simple_pid import PID

from auv_control_pi.config import config

SIMULATION = os.getenv('SIMULATION', False)
logger = logging.getLogger(__name__)
Point = namedtuple('Point', ['lat', 'lng'])


def heading_to_point(point_a, point_b):
    """Calculate heading between two points
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return int(result['azimuth'])


def distance_to_point(point_a, point_b):
    """Calculate distance between to points
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return int(result['distance'])


def get_error_angle(target, heading):
    """Calculate error angle between -180 to 180 between target and heading angles

    If normalized is True then the result will be scaled to -1 to 1
    """
    error = heading - target
    abs_error = abs(target - heading)

    if abs_error == 180:
        return abs_error
    elif abs_error < 180:
        return error
    elif heading > target:
        return abs_error - 360
    else:
        return 360 - abs_error


class Navitgator(ApplicationSession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = False
        self.heading = None
        self.target_heading = None
        self.current_location = None
        self.target_waypoint = None
        self.update_frequency = 10
        self.arrived = False
        self.waypoints = deque()
        # the pid setpoint is the error setpoint
        # and thus we always want the error to be 0 regardless of the scale
        # we use to feed into the pid.
        self.pid = PID(config.kP, config.kI, config.kD, setpoint=0, output_limits=(-100, 100))
        self.pid_output = None
        self.heading_error = None

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'navigation'))
        self.join(realm=self.config.realm)

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops
        """
        logger.info("Joined Crossbar Session")
        await self.subscribe(self._update_ahrs, 'ahrs.update')
        await self.subscribe(self._update_gps, 'gps.update')
        await self.register(self.move_to_waypoint, 'nav.move_to_waypoint')
        await self.register(self.start_trip, 'nav.start_trip')
        await self.register(self.pause_trip, 'nav.pause_trip')
        await self.register(self.stop, 'nav.stop')
        await self.register(self.set_pid_values, 'nav.set_pid_values')
        await self.register(self.get_pid_values, 'nav.get_pid_values')
        await self.register(self.get_target_waypoint_distance, 'nav.get_target_waypoint_distance')
        await self.register(self.set_target_waypoint_distance, 'nav.set_target_waypoint_distance')
        await self.register(self.set_navigation_values, 'nav.set_navigation_values')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    def _update_ahrs(self, data):
        self.heading = data.get('heading', None)

    def _update_gps(self, data):
        self.current_location = Point(lat=data.get('lat'), lng=data.get('lng'))

    def set_pid_values(self, kP, kI, kD, debounce=None):
        self.pid.Kp = kP
        self.pid.Ki = kI
        self.pid.Kd = kD
        config.kP, config.kI, config.kD = kP, kI, kD
        if debounce is not None:
            config.pid_error_debounce = debounce
        config.save()

    def get_pid_values(self):
        return {
            'kP': self.pid.Kp,
            'kI': self.pid.Ki,
            'kD': self.pid.Kd,
            'debounce': config.pid_error_debounce
        }

    def get_target_waypoint_distance(self):
        return {
            'target_waypoint_distance': config.target_waypoint_distance
        }

    def set_target_waypoint_distance(self, target_waypoint_distance):
        config.target_waypoint_distance = target_waypoint_distance
        config.save()

    def set_navigation_values(self, target_waypoint_distance):
        config.target_waypoint_distance = target_waypoint_distance
        config.save()

    def move_to_waypoint(self, waypoint):
        if isinstance(waypoint, dict):
            waypoint = Point(**waypoint)
        logger.info('Moving to waypint: {}'.format(waypoint))
        self.arrived = False
        self.target_waypoint = waypoint
        self.target_heading = heading_to_point(self.current_location, waypoint)
        self.enabled = True

    def start_trip(self, waypoints=None):
        if waypoints:
            self.waypoints = deque(waypoints)
        self.move_to_waypoint(self.waypoints.popleft())

    def pause_trip(self):
        # push the current waypoint back on the stack
        self.waypoints.appendleft(self.target_waypoint)
        self.target_waypoint = None

    def stop(self):
        self.enabled = False
        self.call('auv.stop')

    async def _update(self):
        """Update the current position and heading
        """
        while True:
            if self.enabled and self.target_waypoint and not self.arrived:
                # check if we have hit our target within the target distance
                # Note: target distance is the minimum distance we need to
                # arrive at in order to consider ourselves "arrived"
                # at the waypoint
                if self.distance_to_target <= config.target_waypoint_distance:
                    try:
                        # if there are waypoints qeued up keep going
                        self.move_to_waypoint(self.waypoints.popleft())
                    except IndexError:
                        # otherwise we have arrived
                        self.arrived = True
                        logger.info('Arrived at {}'.format(self.target_waypoint))

                # otherwise keep steering towards the target waypoint
                else:
                    self._steer()

            config.refresh_from_db()
            self.publish('nav.update', {
                'enabled': self.enabled,
                'target_waypoint': self.target_waypoint._asdict() if self.target_waypoint else None,
                'target_heading': self.target_heading,
                'kP': self.pid.Kp,
                'kI': self.pid.Ki,
                'kD': self.pid.Kd,
                'heading_error': self.heading_error,
                'pid_output': self.pid_output,
                'arrived': self.arrived,
                'distance_to_target': self.distance_to_target
            })
            await asyncio.sleep(1 / self.update_frequency)

    def _steer(self):
        """Calculate heading error to feed into PID
        """
        # TODO think about how often should we update the target heading?
        # if it's updated too often then it could cause jittery behavior
        self.target_heading = heading_to_point(self.current_location, self.target_waypoint)
        self.heading_error = get_error_angle(self.target_heading, self.heading)
        # update the pid
        self.pid_output = self.pid(self.heading_error)

        # only take action if the error is beyond the debounce
        if abs(self.heading_error) > config.pid_error_debounce:
            # take action to ajdust the speed of each motor to steer
            # in the direction to minimize the heading error
            self.call('auv.set_turn_val', self.pid_output)

    @property
    def distance_to_target(self):
        if self.target_waypoint:
            return distance_to_point(self.current_location, self.target_waypoint)
        else:
            return None


class Trip:

    def __init__(self, pk, waypoints):
        self.pk = pk
        self.waypoints = [Point(lat=w['lat'], lng=w['lng']) for w in waypoints]
