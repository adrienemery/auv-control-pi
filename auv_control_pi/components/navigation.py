import os
import asyncio
import logging
from collections import deque

from simple_pid import PID

from auv_control_pi.config import config
from auv_control_pi.utils import Point, distance_to_point, heading_to_point, get_error_angle
from auv_control_pi.wamp import ApplicationSession, rpc, subscribe

SIMULATION = os.getenv('SIMULATION', False)
logger = logging.getLogger(__name__)


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
        self.completed_waypoints = []
        # the pid setpoint is the error setpoint
        # and thus we always want the error to be 0 regardless of the scale
        # we use to feed into the pid.
        self.pid = PID(config.kP, config.kI, config.kD, setpoint=0, output_limits=(-100, 100))
        self.pid_output = None
        self.heading_error = None

    @subscribe('ahrs.update')
    def _update_ahrs(self, data):
        self.heading = data.get('heading', None)

    @subscribe('gps.update')
    def _update_gps(self, data):
        self.current_location = Point(lat=data.get('lat'), lng=data.get('lng'))

    @rpc('nav.set_pid_values')
    def set_pid_values(self, kP, kI, kD, debounce=None):
        self.pid.Kp = float(kP)
        self.pid.Ki = float(kI)
        self.pid.Kd = float(kD)
        config.kP, config.kI, config.kD = self.pid.Kp, self.pid.Ki, self.pid.Kd
        if debounce is not None:
            config.pid_error_debounce = debounce
        config.save()

    @rpc('nav.get_pid_values')
    def get_pid_values(self):
        return {
            'kP': self.pid.Kp,
            'kI': self.pid.Ki,
            'kD': self.pid.Kd,
            'debounce': config.pid_error_debounce
        }

    @rpc('nav.get_target_waypoint_distance')
    def get_target_waypoint_distance(self):
        return {
            'target_waypoint_distance': config.target_waypoint_distance
        }

    @rpc('nav.set_target_waypoint_distance')
    def set_target_waypoint_distance(self, target_waypoint_distance):
        config.target_waypoint_distance = int(target_waypoint_distance)
        config.save()

    @rpc('nav.move_to_waypoint')
    def move_to_waypoint(self, waypoint):
        self.call('auv.forward_throttle', 50)
        self.pid.auto_mode = True
        if isinstance(waypoint, dict):
            waypoint = Point(**waypoint)
        logger.info('Moving to waypint: {}'.format(waypoint))
        self.arrived = False
        self.target_waypoint = waypoint
        self.target_heading = heading_to_point(self.current_location, waypoint)
        self.enabled = True

    @rpc('nav.start_trip')
    def start_trip(self, waypoints=None):
        if waypoints:
            self.waypoints = deque(waypoints)
            self.completed_waypoints = []
            self.move_to_waypoint(self.waypoints.popleft())

    @rpc('nav.resume_trip')
    def resume_trip(self):
        if not self.arrived:
            self.move_to_waypoint(self.target_waypoint)

    @rpc('nav.stop')
    def stop(self):
        self.enabled = False
        self.pid.auto_mode = False
        self.call('auv.stop')

    async def update(self):
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
                        self.completed_waypoints.append(self.target_waypoint._asdict())
                        # if there are waypoints qeued up keep going
                        self.move_to_waypoint(self.waypoints.popleft())
                    except IndexError:
                        # otherwise we have arrived
                        self.arrived = True
                        self.stop()
                        logger.info('Arrived at {}'.format(self.target_waypoint))

                # otherwise keep steering towards the target waypoint
                else:
                    self._steer()

            config.refresh_from_db()
            self.publish('nav.update', {
                'enabled': self.enabled,
                'target_waypoint': self.target_waypoint._asdict() if self.target_waypoint else None,
                'completed_waypoints': list(self.completed_waypoints),
                'waypoints': list(self.waypoints),
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
