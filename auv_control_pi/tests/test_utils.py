from ..utils import Point, heading_to_point, distance_to_point


def test_point():
    point = Point(10, 20)
    assert point.lat == 10
    assert point.lng == 20


def test_heading_to_point():
    start_point = Point(49, -120)
    end_point = Point(50, -120)
    heading = heading_to_point(start_point, end_point)
    assert heading == 0.0


def test_distance_to_point():
    start_point = Point(49, -120)
    end_point = Point(50, -120)
    distance = distance_to_point(start_point, end_point)
    assert isinstance(distance, float)
