import logging
import time

from collections import deque, namedtuple
from pygc import great_distance, great_circle
from pygc.gc import vinc_pt

from navio.gps import GPS
from navio.mpu9250 import MPU9250
from .ahrs import AHRS


logger = logging.getLogger(__name__)
Point = namedtuple('Point', ['lat', 'lng'])


def heading_to_point(point_a, point_b):
    """
    Calculate heading between two points
    :param point_a: Coordinate Point(lat,lng) of a 1st point
    :param point_b: Coordinate Point(lat,lng) of a 2nd point
    :return: Heading from A to B
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return result['azimuth']


def distance_to_point(point_a, point_b):
    """
    Calculate distance between to points
    :param point_a: Coordinate Point(lat,lng) of a 1st point
    :param point_b: Coordinate Point(lat,lng) of a 2nd point
    :return: Distance between A and B
    """
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return float(result['distance'])


def get_new_point(point_a, bearing, distance):
    """
    Calculate the coordinates of a point, given a starting point a bearing and a distance
    :param point_a: reference point coordinates Point(lat,lng)
    :param bearing: bearing from reference point to new point
    :param distance: distance between the reference point and the new point
    :return: new point coordinates Point(lat,lng)
    """
    f = 1 / 298.277223563  # flattening of the ellipsoid
    a = 6378137.0  # length of the semi - major axis(radius at equator)

    new_point_lat, new_point_lng, _ = vinc_pt(f, a, point_a.lat, point_a.lng, bearing, distance)
    new_point = Point(lat=new_point_lat, lng=new_point_lng)
    return new_point


def heading_modulo_180(heading):
    """
    Corrects heading value to range between [-180:180]
    :param heading: a heading with potential value ranges outside of [-180:180]
    :return: corrected heading which value ranges between [-180:180]
    """
    while heading > 180 or heading < -180:
        if heading > 180:
            heading - 360
        elif heading < -180:
            heading + 360
    return heading


class Navigator:

    # target distance is the minimum distance we need to
    # arrive at in order to consider ourselves "arrived"
    # at the waypoint
    TARGET_RADIUS = 60  # meters

    def __init__(self, gps, left_motor=None, right_motor=None, update_period=1):
        self._running = False
        self.imu = MPU9250()
        self.imu.initialize()
        self.ahrs = AHRS()
        self.gps = GPS()
        self.gps.update()
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.target_waypoint = None
        self.target_heading = None
        self.absolute_heading = None  # In what direction the AUV is looking
        self.current_location = Point(self.gps.lat, self.gps.lon)

        self.update_period = update_period
        self.arrived = False
        self.waypoints = deque()
        self.position_control = PositionControl(current_position=self.current_location, target_radius=self.TARGET_RADIUS)

    def stop(self):
        self._running = False

    def move_to_waypoint(self, waypoint):
        self.arrived = False
        self.target_waypoint = waypoint
        self.target_heading = heading_to_point(self.current_location, waypoint)
        self.position_control.set_limits(self.target_waypoint, self.target_heading)

    def start_trip(self, waypoints=None):
        if waypoints:
            self.waypoints = deque(waypoints)
        self.move_to_waypoint(self.waypoints.popleft())

    def pause_trip(self):
        # push the current waypoint back on the stack
        self.waypoints.appendleft(self.target_waypoint)
        self.target_waypoint = None

    def update(self):
        """
        Update the current position and heading
        """
        accel, gyro, mag = self.imu.getMotion9()
        self.ahrs.update(accel, gyro, mag)
        # self.current_location = self.gps
        self.absolute_heading = self.ahrs.heading()
        # now we want to get the current_heading aligned with the target heading. TODO
        # we want that absolute heading always aligned with the target heading until the zone changes,
        # then we dont want them aligned anymore

        self.position_control.update(self.current_location)
        if not self.position_control.in_green_zone:
            self.target_heading = self.position_control.new_heading
            # play with the motors to head to the new destination

        # TODO implement controls using real io to sensors/motors

        if self.target_waypoint and not self.arrived:
            # check if we have hit our target
            if self.distance_to_target <= self.TARGET_DISTANCE:
                try:
                    # if there are waypoints qeued up keep going
                    self.move_to_waypoint(self.waypoints.popleft())
                except IndexError:
                    # otherwise we have arrived
                    self.arrived = True
                    logger.info('Arrived at Waypoint({}, {})'.format(self.target_waypoint.lat,
                                                                     self.target_waypoint.lng))

            # otherwise keep steering towards the target waypoint
            else:
                # TODO use PID to calculate steering inputs
                # TODO have a speed setting to throttle speed of craft
                self.steer()

    def steer(self):
        # calculate heading error to feed into PID
        # TODO test the handedness of this
        heading_error = self.target_heading - self.ahrs.heading
        if abs(heading_error > 5):  # TODO make this an adjustable config value on in database
            # take action to ajdust the speed of each motor to steer
            # in the direction to minimize the heading error
            # TODO
            pass

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


class PositionControl:

    def __init__(self, current_position=None, next_waypoint=None, target_radius=None):
        self.A = current_position or Point(lat=49.2827, lng=-123.1207)
        self.B = next_waypoint or Point(lat=48.8566, lng=2.3522)
        self.C1 = Point(lat=None, lng=None)  # left green/orange zone limit
        self.C2 = Point(lat=None, lng=None)  # right green/orange zone limit
        self.D1 = Point(lat=None, lng=None)  # left orange/red zone limit
        self.D2 = Point(lat=None, lng=None)  # right orange/red zone limit
        self.alpha = None  # Absolute heading
        self.beta = None  # Relative heading
        self.gamma1 = None  # bearing from B to C1/D1
        self.gamma2 = None  # bearing from B to C2/D2
        self.delta1 = None  # bearing from A to C1 if drifting left or C2 if drifting right green/orange limit
        self.delta2 = None  # bearing from A to D1 if drifting left or D2 if drifting right orange/red limit
        self.new_heading = None
        self.green_zone_radius = target_radius/3 or 20  # TODO make this 1/3 - 2/3 zones look nicer
        self.orange_zone_radius = target_radius or 60  # behind that radius, it's red zone
        self.position = {'drift': 'straight',
                         'direction': 'forward',
                         'zone': 'green',
                         'time': {'in_green_zone': 0,
                                  'in_orange_zone': 0,
                                  'in_red_zone': 0,
                                  'going_backward': 0},
                         'flag': {'danger_zone': False,
                                  'going_backward': False,
                                  'new_heading': False},
                         }

    def drift_position(self, current_position=None):
        if distance_to_point(current_position, self.C1) < distance_to_point(current_position, self.C2):
            self.position['drift'] = 'left'
        elif distance_to_point(current_position, self.C2) < distance_to_point(current_position, self.C1):
            self.position['drift'] = 'right'
        else:
            self.position['drift'] = 'straight'

    async def check_direction(self, current_position=None):
        if self.position['drift'] == 'right':
            if distance_to_point(current_position, self.B) <= distance_to_point(self.A, self.B) or \
               distance_to_point(current_position, self.D2) <= distance_to_point(self.A, self.D2):
                self.position['direction'] = 'forward'
                self.position['time']['going_backward'] = 0
            else:
                if self.position['time']['going_backward'] <= 5:  # we haven't gone backward long enough to update status
                    self.position['time']['going_backward'] += 1
                    await time.sleep(1)
                elif self.position['time']['going_backward'] > 5:  # we are now officially going backward
                    self.position['direction'] = 'backward'
                    self.position['time']['going_backward'] += 1  # we want to keep track of how long this is going
                    await time.sleep(1)
                    if self.position['time']['going_backward'] > 15:  # if we've been going backward for too long
                        self.position['flag']['going_backward'] = True  # we need to do something about it

        elif self.position['drift'] == 'left':
            if distance_to_point(current_position, self.B) <= distance_to_point(self.A, self.B) or \
               distance_to_point(current_position, self.D1) <= distance_to_point(self.A, self.D1):
                self.position['direction'] = 'forward'
                self.position['time']['going_backward'] = 0
            else:
                if self.position['time']['going_backward'] <= 5:
                    self.position['time']['going_backward'] += 1
                    await time.sleep(1)
                elif self.position['time']['going_backward'] > 5:
                    self.position['direction'] = 'backward'
                    self.position['time']['going_backward'] += 1
                    await time.sleep(1)
                    if self.position['time']['going_backward'] > 15:
                        self.position['flag']['going_backward'] = True
        else:
            if distance_to_point(current_position, self.B) <= distance_to_point(self.A, self.B):
                self.position['direction'] = 'forward'
                self.position['time']['going_backward'] = 0
            else:
                if self.position['time']['going_backward'] <= 5:
                    self.position['time']['going_backward'] += 1
                    await time.sleep(1)
                elif self.position['time']['going_backward'] > 5:
                    self.position['direction'] = 'backward'
                    self.position['time']['going_backward'] += 1
                    await time.sleep(1)
                    if self.position['time']['going_backward'] > 15:
                        self.position['flag']['going_backward'] = True

    def green_orange_zone_limit_points(self):
        self.C1 = get_new_point(self.B, self.gamma1, self.green_zone_radius)
        self.C2 = get_new_point(self.B, self.gamma2, self.green_zone_radius)

    def orange_red_zone_limit_points(self):
        self.D1 = get_new_point(self.B, self.gamma1, self.orange_zone_radius)
        self.D2 = get_new_point(self.B, self.gamma2, self.orange_zone_radius)

    # When this method is being called A is the starting point
    def set_limits(self, target=None, heading_to_target=None):
        self.B = target or Point(lat=48.8566, lng=2.3522)
        self.alpha = heading_to_target or heading_to_point(self.A, self.B)
        self.gamma1 = heading_modulo_180(self.alpha - 90)
        self.gamma2 = heading_modulo_180(self.alpha + 90)
        self.green_orange_zone_limit_points()
        self.orange_red_zone_limit_points()

    async def in_green_zone_check(self, current_position=None):
        if self.position['drift'] == 'right':
            self.delta1 = heading_to_point(current_position, self.C2)
            if self.delta1 > self.alpha:  # we just crossed the border from orange or just started our trip
                self.position['time']['in_orange_zone'] = 0  # reset the timer from the orange zone (we could come from it)
                if self.position['time']['in_green_zone'] < 5:  # it just happened, wait a moment before making it official
                    self.position['time']['in_green_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_green_zone'] >= 5:  # We've been long enough in the zone to consider ourselves in
                    self.position['zone'] = 'green'
                    self.position['flag']['danger_zone'] = False
                    self.position['flag']['new_heading'] = False
            # elif self.delta1 < self.alpha: We are in orange zone, let 'in_orange_zone_check' method take care of it
            # else self.alpha == self.delta: -> threshold. 'in_the_green_zone' keeps its previous value

        elif self.position['drift'] == 'left':
            self.delta1 = heading_to_point(current_position, self.C1)
            if self.delta1 < self.alpha:  # we just crossed the border, or just started our trip
                self.position['time']['in_orange_zone'] = 0
                if self.position['time']['in_green_zone'] < 5:
                    self.position['time']['in_green_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_green_zone'] >= 5:  # We've been long enough in the zone to consider ourselves in
                    self.position['zone'] = 'green'
                    self.position['flag']['danger_zone'] = False
            # elif self.delta1 > self.alpha: We are in orange zone, let 'in_orange_zone_check' method take care of it
            # else self.alpha == self.delta1: -> threshold. 'in_the_green_zone' keeps its previous value
        # else "straight" do nothing

    async def in_orange_zone_check(self, current_position=None):
        if self.position['drift'] == 'right':
            self.delta1 = heading_to_point(current_position, self.C2)
            self.delta2 = heading_to_point(current_position, self.D2)
            if self.delta1 < self.alpha < self.delta2:  # in orange zone
                self.position['time']['in_green_zone'] = 0
                self.position['time']['in_red_zone'] = 0
                if self.position['time']['in_orange_zone'] < 5:  # we just crossed the border
                    self.position['time']['in_orange_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_orange_zone'] >= 5:  # we've been in orange zone for a while now
                    if self.position['zone'] == 'green':  # if previous zone is green
                        self.position['zone'] = 'orange'
                    elif self.position['zone'] == 'red': # if previous zone is red
                        self.position['zone'] = 'red&orange'
                        # if we come from the red zone we want to keep that information
                        # because we don't want to change the heading again when we cross back to the orange zone

                # elif other cases, means not in orange zone but either in green or red zone.
                # Let those colour_zone_check methods handle it
            # elif self.alpha == self.delta1: -> threshold. 'in_the_green_zone' keeps its previous value
            # elif self.alpha == self.delta2: -> threshold. 'in_the_red_zone' keeps its previous value

        elif self.position['drift'] == 'left':
            self.delta1 = heading_to_point(current_position, self.C1)
            self.delta2 = heading_to_point(current_position, self.D1)
            if self.delta2 < self.alpha < self.delta1:  # in orange zone
                self.position['time']['in_green_zone'] = 0
                self.position['time']['in_red_zone'] = 0
                if self.position['time']['in_orange_zone'] < 5:  # we just crossed the border
                    self.position['time']['in_orange_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_orange_zone'] >= 5:  # we've been in orange zone for a while now
                    # We want a different behaviour whether we come from the green zone or the red zone
                    if self.position['zone'] == 'green':  # if previous zone is green
                        self.position['zone'] = 'orange'
                    elif self.position['zone'] == 'red':  # if previous zone is red
                        self.position['zone'] = 'red&orange'
                # elif other cases, means not in orange zone but either in green or red zone.
                # Let those colour_zone_check methods handle it
            # elif self.alpha == self.delta1: -> threshold. 'in_the_green_zone' keeps its previous value
            # elif self.alpha == self.delta2: -> threshold. 'in_the_red_zone' keeps its previous value
        # else "straight" do nothing

    async def in_red_zone_check(self, current_position=None):
        # if we're in the red zone it means that we've gone through the orange zone.
        # Therefore we've applied new headings so alpha is not the same anymore
        # TODO: do the drawings and figure it out -> alpha should not be the same anymore (doesnt change the logic tho?)
        if self.position['drift'] == 'right':
            self.delta1 = heading_to_point(current_position, self.D2)
            if self.delta1 < self.alpha:
                self.position['time']['in_orange_zone'] = 0  # then reset orange timer
                if self.position['time']['in_red_zone'] < 5:  # we just crossed the border, or just started our trip
                    self.position['time']['in_red_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_red_zone'] >= 5:  # We've been long enough the zone to consider ourselves in
                    self.position['zone'] = 'red'
                    self.position['time']['in_red_zone'] += 1  # continue checking time in red zone
                    await time.sleep(1)
                if self.position['time']['in_red_zone'] > 180:
                    self.position['flag']['danger_zone'] = True
            # elif self.delta1 > self.alpha: We are in orange zone, let 'in_orange_zone_check' method take care of it
            # else self.alpha == self.delta: -> threshold. 'in_the_green_zone' keeps its previous value

        elif self.position['direction'] == 'left':
            self.delta1 = heading_to_point(current_position, self.D1)
            if self.delta1 > self.alpha:
                self.position['time']['in_orange_zone'] = 0
                if self.position['time']['in_red_zone'] < 5:  # we just crossed the border
                    self.position['time']['in_red_zone'] += 1
                    await time.sleep(1)
                if self.position['time']['in_red_zone'] >= 5:  # We've been long enough in the zone to consider ourselves in
                    self.position['zone'] = 'red_zone'
                    self.position['time']['in_red_zone'] += 1  # continue checking time in red zone
                    await time.sleep(1)
                if self.position['time']['in_red_zone'] > 180:
                    self.position['flag']['danger_zone'] = True
            # elif self.delta1 < self.alpha: We are in orange zone, let 'in_orange_zone_check' method take care of it
            # else self.alpha == self.delta1: -> threshold. 'in_the_red_zone' keeps its previous value
        # else "straight" do nothing

    def check_current_zone(self, current_position=None):
        self.drift_position(current_position)
        self.check_direction(current_position)
        self.in_green_zone_check(current_position)
        self.in_orange_zone_check(current_position)
        self.in_red_zone_check(current_position)

    def compute_new_heading(self):
        # self.beta - self.alpha represent the bearing error due to drifting (caused by current or wind or whatever)
        # drift angle  needs to be considered for next route heading
        drift_error = abs(heading_modulo_180(self.beta - self.alpha))  # /!\ this is an angle not a heading
        if self.position['drift'] == 'right':
            if self.position['zone'] == 'orange':  # coming from green zone
                # subtracting an angle (to a heading) is equivalent to adding a negative heading
                self.new_heading = heading_modulo_180(heading_to_point(self.A, self.C1) - drift_error)
                self.position['flag']['new_heading'] = True
            elif self.position['zone'] == 'red' and not self.position['flag']['danger_zone']:  # coming from orange zone
                self.new_heading = heading_modulo_180(heading_to_point(self.A, self.D1) - drift_error)
            # elif self.position['flag']['danger_zone'] >> do something special? or just stop everything? or do nothing?
            # elif self.position['zone'] == 'red&orange' and not  self.drift['flag']['danger_zone']: # in orange zone from red zone
                # Do nothing (keep the in-red-zone updated heading)
            # elif self.position['zone'] == green:
                # Hotsy Totsy
        elif self.position['drift'] == 'left':
            if self.position['zone'] == 'orange':  # coming from green zone
                self.new_heading = heading_modulo_180(heading_to_point(self.A, self.C2) + drift_error)
                self.position['flag']['new_heading'] = True
            elif self.position['zone'] == 'red' and not self.position['flag']['danger_zone']:  # coming from orange zone
                self.new_heading = heading_modulo_180(heading_to_point(self.A, self.D2) + drift_error)
            # elif self.position['flag']['danger_zone'] >> do something special? or just stop everything? or do nothing?
            # elif self.position['zone'] == 'red&orange' and not position.['flag']['danger_zone']: # in orange zone from red zone
                # Do nothing (keep the in-red-zone updated heading)
            # elif elf.position['zone'] == 'green:
                # Hotsy Totsy

    def update(self, current_position=None):
        self.check_current_zone(current_position)
        self.beta = heading_to_point(self.A, current_position)  # bearing between A and A' (drifting heading)
        self.A = current_position  # update current position

        # if self.in_green_zone:  # let it go, meaning: don't change the current heading
        # in orange zone, compute a new heading once, in the red zone keep doing it.
        # in orange zone from red zone (orange&red) let it go
        # if going backward, may be a new heading would help
        if self.position['zone'] == 'orange' and not self.position['flag']['new_heading'] or \
           self.position['zone'] == 'red' or \
           self.position['direction']['going_backward']:
            self.compute_new_heading()


# IDEAS:
# The code should try to always keep the same heading (same alpha) in background until decided to change.
# Meaning we should always try to look in the same direction whether we are drifting or not

# Alpha should be where we're looking.
# So, before starting the first route to the first waypoint, we should align alpha with A-B heading.
# And as the mothership is moving (in the green zone) constantly correct where the board is looking
# to keep both headings aligned (NOTE it'll probably be a freaking mess when heading straight south with -180/180 limit)

# Although it may be good to have local PositionControl.alpha = original A-B heading in PositionControl.
# which is invariant. While the code constantly corrects (on the side) the real alpha to keep it aligned.
# That would probably make the control easiest and the math less sensitive to small variation

# So, before the PositionControl.update call, we must have everything aligned.

