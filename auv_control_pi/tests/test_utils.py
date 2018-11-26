from ..utils import get_error_angle, Point, heading_to_point, distance_to_point


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


def test_get_error_angle():
    result = get_error_angle(target=10, heading=0)
    assert result == -10

    result = get_error_angle(target=0, heading=10)
    assert result == 10

    result = get_error_angle(target=10, heading=350)
    assert result == -20

    result = get_error_angle(target=0, heading=20)
    assert result == 20

    result = get_error_angle(target=0, heading=180)
    assert result == -180

    result = get_error_angle(target=0, heading=181)
    assert result == -179

    result = get_error_angle(target=0, heading=179)
    assert result == 179

