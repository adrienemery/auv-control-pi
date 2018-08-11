from ..navigation import PositionControl, get_new_point, heading_modulo_180, reverse_heading_modulo_180
from collections import namedtuple

Point = namedtuple('Point', ['lat', 'lng'])

paris = Point(lat=48.8566, lng=2.3522)
vancouver = Point(lat=49.2827, lng=-123.1207)


# https://www.fcc.gov/media/radio/distance-and-azimuths
def test_get_new_point():
    result = get_new_point(paris, heading_modulo_180(325.87), 7915506)
    assert result.lat == vancouver.lat and result.lng == vancouver.lng


def test_heading_modulo_180_1():
    heading = 270
    assert heading_modulo_180(heading) == -90


def test_heading_modulo_180_2():
    heading = 390
    assert heading_modulo_180(heading) == 30


def test_heading_modulo_180_3():
    heading = -90
    assert heading_modulo_180(heading) == -90


def test_heading_modulo_180_4():
    heading = -270
    assert heading_modulo_180(heading) == 90


def test_heading_modulo_180_5():
    heading = -390
    assert heading_modulo_180(heading) == -30


def test_heading_modulo_180_6():
    heading = 90
    assert heading_modulo_180(heading) == 90


def test_reverse_heading_modulo_180_1():
    heading = 10
    assert reverse_heading_modulo_180(heading) == 10


def test_reverse_heading_modulo_180_2():
    heading = 190
    assert reverse_heading_modulo_180(heading) == 190


def test_reverse_heading_modulo_180_3():
    heading = 390
    assert reverse_heading_modulo_180(heading) == 30


def test_reverse_heading_modulo_180_4():
    heading = -10
    assert reverse_heading_modulo_180(heading) == 350


def test_reverse_heading_modulo_180_5():
    heading = -190
    assert reverse_heading_modulo_180(heading) == 170


def test_reverse_heading_modulo_180_6():
    heading = -390
    assert reverse_heading_modulo_180(heading) == -30


def test_drift_position_right():
    current_position = Point(lat=77.682035, long=-15.888030)
    control = PositionControl()
    control.green_orange_zone_limit_points()
    control.orange_red_zone_limit_points()
    control.check_drift_position(current_position)

    assert control.info.drift == "right"


def test_drift_position_left():
    current_position = Point(lat=17.250762, long=-54.427977)
    control = PositionControl()
    control.green_orange_zone_limit_points()
    control.orange_red_zone_limit_points()
    control.check_drift_position(current_position)

    assert control.info.drift == "left"


