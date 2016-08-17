from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from asgi import channel_layer


class RemoteInterface(ApplicationSession):

    DEFAULT_TURN_SPEED = 0.5
    DEFAULT_FORWARD_SPEED = 0.5
    DEFAULT_REVERSE_SPEED = 0.5
    SERIAL_SEND_CHANNEL = 'auv.send'
    NAVIGATION_CHANNEL = 'nav.send'

    def send_serial(self, msg):
        assert isinstance(msg, dict)
        msg['sender'] = 'remote_control'
        channel_layer.send(self.SERIAL_SEND_CHANNEL, msg)

    @staticmethod
    def _check_speed(speed):
        if not 0 <= speed <= 1:
            err_msg = 'speed must be in range 0 <= speed <= 1, got {}'.format(speed)
            raise ValueError(err_msg)

    async def onJoin(self, details):
        print("session ready")

        def move_right(speed=None):
            speed = self.DEFAULT_TURN_SPEED or speed
            self._check_speed(speed)
            msg = {
                'cmd': 'move_right',
                'kwargs': {'speed': speed}
            }
            self.send_serial(msg)

        def move_left(speed=None):
            speed = self.DEFAULT_TURN_SPEED or speed
            self._check_speed(speed)
            msg = {
                'cmd': 'move_left',
                'kwargs': {'speed': speed}
            }
            self.send_serial(msg)

        def move_forward(speed=None):
            speed = self.DEFAULT_FORWARD_SPEED or speed
            self._check_speed(speed)
            msg = {
                'cmd': 'move_left',
                'kwargs': {'speed': speed}
            }
            self.send_serial(msg)

        def move_reverse(speed=None):
            speed = self.DEFAULT_REVERSE_SPEED or speed
            self._check_speed(speed)
            msg = {
                'cmd': 'move_left',
                'kwargs': {'speed': speed}
            }
            self.send_serial(msg)

        def move_to_waypoint(lat, lon):
            msg = {
                'cmd': 'move_to_waypoint',
                'kwargs': {
                    'lat': lat,
                    'lon': lon
                }
            }
            self.send_serial(msg)

        def stop():
            msg = {
                'cmd': 'stop',
            }
            self.send_serial(msg)

        def start_trip(trip_id):
            pass

        # register functions on for RPC
        await self.register(move_right, 'com.auv.move_right')
        await self.register(move_left, 'com.auv.move_left')
        await self.register(move_forward, 'com.auv.move_forward')
        await self.register(move_reverse, 'com.auv.move_reverse')
        await self.register(move_to_waypoint, 'com.auv.move_to_waypoint')
        await self.register(stop, 'com.auv.stop')
        await self.register(start_trip, 'com.auv.start_trip')


if __name__ == '__main__':
    runner = ApplicationRunner(url=u"ws://localhost:8080/ws", realm=u"realm1")
    runner.run(RemoteInterface)
