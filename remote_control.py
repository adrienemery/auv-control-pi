import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from asgi import channel_layer, AUV_SEND_CHANNEL, AUV_UPDATE_CHANNEL



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
        channel_layer.send(AUV_SEND_CHANNEL, msg)
        print('sending cmd: {}'.format(msg))

    @staticmethod
    def _check_speed(speed):
        if not 0 <= speed <= 1:
            err_msg = 'speed must be in range 0 <= speed <= 1, got {}'.format(speed)
            raise ValueError(err_msg)

    def onConnect(self):
        print('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm, authmethods=['ticket'], authid='auv')

    def onChallenge(self, challenge):
        if challenge.method == 'ticket':
            print("WAMP-Ticket challenge received: {}".format(challenge))
            return '18d4120fa5e2b7c6b41940bdc8834a664c30e3b3659cdf0536e2dce17a01f6c3'
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        """
        Register functions for access via RPC
        """
        print("session ready")
        await self.register(self.move_right, 'com.auv.move_right')
        await self.register(self.move_left, 'com.auv.move_left')
        await self.register(self.move_forward, 'com.auv.move_forward')
        await self.register(self.move_reverse, 'com.auv.move_reverse')
        await self.register(self.move_to_waypoint, 'com.auv.move_to_waypoint')
        await self.register(self.stop, 'com.auv.stop')
        await self.register(self.start_trip, 'com.auv.start_trip')
        # await self.update()
        # await self.heartbeat()

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
            channels = [AUV_UPDATE_CHANNEL]
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    print('Got data: {}'.format(data))
                    # publish data
                    self.publish('com.auv.update', data)
                else:
                    break

    async def heartbeat(self):
        while True:
            await asyncio.sleep(1)
            # publish data
            self.publish('com.auv.heartbeat', 'ok')
            print('heartbeat')


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()
    config.read('config.ini')
    url = config['crossbar']['url']
    realm = config['crossbar']['realm']
    runner = ApplicationRunner(url=url, realm=realm)
    runner.run(RemoteInterface)
