from collections import deque, namedtuple
from pygc import great_distance


Point = namedtuple('Point', ['lat', 'lng'])


def heading_to_point(point_a, point_b):
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return result['azimuth']


def distance_to_point(point_a, point_b):
    result = great_distance(start_latitude=point_a.lat,
                            start_longitude=point_a.lng,
                            end_latitude=point_b.lat,
                            end_longitude=point_b.lng)
    return float(result['distance'])


class Navigator:

    def __init__(self, gps, compass, left_motor, right_motor):
        self._gps = gps
        self._compass = compass
        self._left_motor = left_motor
        self._right_motor = right_motor

    def move_to_waypoint(self, point):
        pass
