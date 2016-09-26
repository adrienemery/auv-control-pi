from collections import namedtuple, deque
from django.conf import settings
from pygc import great_distance

if settings.SIMULATE:
    from navio.gps import GPS
    from navio.compass import Compass  # TODO
else:
    from .simulator import GPS, Compass, Simulator


Coords = namedtuple('Coords', ['lat', 'lng'])


class Navigator:

    def __init__(self, waypoints=None):
        self._gps = GPS()
        self._compass = Compass()
        if settings.SIMULATE:
            self._simulator = Simulator(self._gps, self._compass)
        else:
            self._simulator = None

        self.waypoints = deque(waypoints or [])
        if self.waypoints:
            self.next_waypoint = self.waypoints.popleft()
        else:
            self.next_waypoint = None

    @property
    def coords(self):
        return Coords(lat=self._gps.lat, lng=self._gps.lng)

    @property
    def heading(self):
        return self._compass.heading

    def distance_to_next_waypoint(self):
        start_lat, start_lng = self._gps.lat, self._gps.lng
        end_lat, end_lng = self.next_waypoint.lat, self.next_waypoint.lng
        result = great_distance(start_latitude=start_lat, start_longitude=start_lng,
                                end_latitude=end_lat, end_longitude=end_lng)
        return result['distance']

    def distance_to_end(self):
        """Calculate sum of distances between all remaining waypoints
        """
        pass
