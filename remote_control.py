import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from asgi import channel_layer, MOTHERSHIP_SEND_CHANNEL, MOTHERSHIP_UPDATE_CHANNEL


class RemoteInterface(ApplicationSession):

    DEFAULT_TURN_SPEED = 0.5
    DEFAULT_FORWARD_SPEED = 0.5
    DEFAULT_REVERSE_SPEED = 0.5

    @staticmethod
    def _relay_cmd(msg):
        """
        Relay commands to Mothership using asgi channels
        """
        assert isinstance(msg, dict)
        msg['sender'] = 'remote_control'
        channel_layer.send(MOTHERSHIP_SEND_CHANNEL, msg)

    @staticmethod
    def _check_speed(speed):
        if not 0 <= speed <= 1:
            err_msg = 'speed must be in range 0 <= speed <= 1, got {}'.format(speed)
            raise ValueError(err_msg)

    async def onJoin(self, details):
        """
        Register functions for access via RPC
        """
        print("session ready")
        await self.register(self.move_right, 'com.mothership.move_right')
        await self.register(self.move_left, 'com.mothership.move_left')
        await self.register(self.move_forward, 'com.mothership.move_forward')
        await self.register(self.move_reverse, 'com.mothership.move_reverse')
        await self.register(self.move_to_waypoint, 'com.mothership.move_to_waypoint')
        await self.register(self.stop, 'com.mothership.stop')
        await self.register(self.start_trip, 'com.mothership.start_trip')
        await self.update()

    def move_right(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_right',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_left(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_left',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_forward(self, speed=None):
        speed = self.DEFAULT_FORWARD_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_left',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_reverse(self, speed=None):
        speed = self.DEFAULT_REVERSE_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_left',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_to_waypoint(self, lat, lon):
        msg = {
            'cmd': 'move_to_waypoint',
            'kwargs': {
                'lat': lat,
                'lon': lon
            }
        }
        self._relay_cmd(msg)

    def stop(self, ):
        msg = {
            'cmd': 'stop',
        }
        self._relay_cmd(msg)

    def start_trip(self, trip_id):
        msg = {
            'cmd': 'stop',
        }
        self._relay_cmd(msg)

    async def update(self):
        """
        Broadcast updates at 1Hz
        """
        while True:
            await asyncio.sleep(0.1)
            channels = [MOTHERSHIP_UPDATE_CHANNEL]
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    print('Got data: {}'.format(data))
                    # publish data
                    self.publish('com.mothership.onupdate', data)
                else:
                    break


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('config.ini')
    url = config['crossbar']['url']
    realm = config['crossbar']['realm']
    runner = ApplicationRunner(url=url, realm=realm)
    runner.run(RemoteInterface)
