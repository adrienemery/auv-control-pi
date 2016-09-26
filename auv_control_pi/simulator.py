import time


class GPS:

    def __init__(self):
        self.lat = 49.2827
        self.lng = -123.1207


class Compass:

    def __init__(self):
        self.heading = 120.0


class Motor:

    def __init__(self, name):
        self.name = name
        self.speed = 0

    def __repr__(self):
        return 'Motor({})'.format(self.name)


class Simulator:

    def __init__(self, gps, compass, motor_port=None, motor_starboard=None):
        self._gps = gps
        self._compass = compass
        self._motor_port = motor_port
        self._motor_starboard = motor_starboard
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            time.sleep(0.9)


