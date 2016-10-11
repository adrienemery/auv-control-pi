import pytest

from pygc import great_circle

from ..simulator import Navitgator, GPS, Motor, Compass
from ..utils import Point, distance_to_point


@pytest.fixture
def sim():
    starting_point = Point(50, 120)
    return Navitgator(gps=GPS(), compass=Compass(),
                      current_location=starting_point,
                      update_period=1)


def test_simulator_move_to_waypoint(sim):
    waypoint = Point(49, 120)
    sim.move_to_waypoint(waypoint)
    assert sim._compass.heading == 180


def test_simulator_update(sim):
    # generate a waypoint 100 meters away due South
    heading = 140.0
    distance = 100
    result = great_circle(distance=distance,
                          azimuth=heading,
                          latitude=sim._current_location.lat,
                          longitude=sim._current_location.lng)
    waypoint = Point(result['latitude'], result['longitude'])
    sim.move_to_waypoint(waypoint)
    sim.speed = 10
    starting_point = sim._current_location

    # since we have an update period of 1s and speed of 10 m/s
    # after one update cycle we should have moved 10 meters
    # from our last point
    sim._update()
    distance_moved = distance_to_point(starting_point, sim._current_location)
    assert sim.speed == pytest.approx(distance_moved)
    assert heading == pytest.approx(sim._compass.heading)
    assert sim.arrived is False

    # should take 8 updates total to get within 20 meters
    # since we have already moved 10 meters we should only need
    # to move another 70 meters
    for x in range(7):
        sim._update()
        if x < 6:
            assert sim.arrived is False
    assert sim.arrived is True
