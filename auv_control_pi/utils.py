import time
from collections import deque, namedtuple
from pygc import great_distance

Point = namedtuple('Point', ['lat', 'lng'])


def elapsed_micros(start_time_us):
    return (time.perf_counter() * 1e6) - start_time_us


def micros():
    return time.perf_counter() * 1e6


def clamp_angle(deg):
    """Rotate angle back to be within [0, 360]
    """
    n_rotations = deg // 360
    deg -= 360 * n_rotations
    return deg


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

