import asyncio
import logging

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from channels import Channel
from .asgi import channel_layer, AUV_SEND_CHANNEL, auv_update_group
from .models import Configuration

logger = logging.getLogger(__name__)


class RemoteInterface(ApplicationSession):

    DEFAULT_TURN_SPEED = 50
    DEFAULT_FORWARD_SPEED = 50
    DEFAULT_REVERSE_SPEED = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # generate a unique channel name for ourselves
        self.auv_update_channel_name = channel_layer.new_channel('remote_control?')
        # subscribe to the auv update channel
        auv_update_group.add(self.auv_update_channel_name)
        self.auv_channel = Channel(AUV_SEND_CHANNEL, channel_layer=channel_layer)

    def _relay_cmd(self, msg):
        """
        Relay commands to Mothership using asgi channels
        """
        assert isinstance(msg, dict)
        msg['sender'] = 'remote_control'
        self.auv_channel.send(msg)
        logger.info('sending cmd: {}'.format(msg))

    @staticmethod
    def _check_speed(speed):
        if not -100 <= speed <= 100:
            err_msg = 'speed must be in range -100 <= speed <= 100, got {}'.format(speed)
            raise ValueError(err_msg)

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm, authmethods=['ticket'], authid='auv')

    def onChallenge(self, challenge):
        if challenge.method == 'ticket':
            logger.info("WAMP-Ticket challenge received: {}".format(challenge))
            config = Configuration.get_solo()
            return config.auth_token
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        """
        Register functions for access via RPC
        """
        logger.info("Joined Crossbar Session")
        await self.register(self.move_right, 'com.auv.move_right')
        await self.register(self.move_left, 'com.auv.move_left')
        await self.register(self.move_forward, 'com.auv.move_forward')
        await self.register(self.move_reverse, 'com.auv.move_reverse')
        await self.register(self.stop, 'com.auv.stop')
        await self.register(self.move_to_waypoint, 'com.auv.move_to_waypoint')
        await self.register(self.start_trip, 'com.auv.start_trip')
        await self.update()
        await self.heartbeat()

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
            'cmd': 'move_forward',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_reverse(self, speed=None):
        speed = self.DEFAULT_REVERSE_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_reverse',
            'kwargs': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_to_waypoint(self, lat, lng):
        msg = {
            'cmd': 'move_to_waypoint',
            'kwargs': {
                'lat': lat,
                'lng': lng
            }
        }
        self._relay_cmd(msg)

    def start_trip(self, waypoints):
        msg = {
            'cmd': 'start_trip',
            'kwargs': waypoints
        }
        self._relay_cmd(msg)

    def stop(self, ):
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
            channels = [self.auv_update_channel_name]
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    logger.debug('Auv Update Data: {}'.format(data))
                    # publish data to wamp
                    self.publish('com.auv.update', data)
                else:
                    break

    async def heartbeat(self):
        while True:
            await asyncio.sleep(2)
            # publish data
            self.publish('com.auv.heartbeat', 'ok')
            logger.debug('heartbeat')


if __name__ == '__main__':
    import configparser
    crossbar_config = configparser.ConfigParser()
    crossbar_config.read('config.ini')
    url = crossbar_config['crossbar']['url']
    realm = crossbar_config['crossbar']['realm']
    runner = ApplicationRunner(url=url, realm=realm)
    runner.run(RemoteInterface)
