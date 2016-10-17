import asyncio
import logging

from autobahn.asyncio.wamp import ApplicationSession
from autobahn_autoreconnect import ApplicationRunner

from channels import Channel
from .asgi import channel_layer, AUV_SEND_CHANNEL, auv_update_group
from .models import Configuration

logger = logging.getLogger(__name__)
AUV_ID = 'f00a7a7b-44cd-4a5f-b424-a15037ccece8'


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
        """Relay commands to Mothership over asgi channels"""
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
        """Handle authentication challenge"""
        if challenge.method == 'ticket':
            logger.info("WAMP-Ticket challenge received: {}".format(challenge))
            config = Configuration.get_solo()
            return config.auth_token
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")

        await self.register(self.move_right, 'com.auv.move_right')
        await self.register(self.move_left, 'com.auv.move_left')
        await self.register(self.move_forward, 'com.auv.move_forward')
        await self.register(self.move_reverse, 'com.auv.move_reverse')
        await self.register(self.stop, 'com.auv.stop')
        await self.register(self.move_to_waypoint, 'com.auv.move_to_waypoint')
        await self.register(self.start_trip, 'com.auv.start_trip')
        await self.register(self.set_trip, 'com.auv.set_trip')
        await self.register(self.update_settings, 'com.auv.update_settings')

        # create subtasks
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self._connected(), loop=loop)
        asyncio.ensure_future(self.heartbeat(), loop=loop)
        asyncio.ensure_future(self.update(), loop=loop)

    async def _connected(self):
        """Let everyone know that we have connected"""
        # TODO get this ide from the database
        self.publish('com.auv.connected', AUV_ID)

    async def update(self):
        """Broadcast updates whenever recieved on update channel"""
        while True:
            await asyncio.sleep(0.1)
            channels = [self.auv_update_channel_name]
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    data['auv_id'] = AUV_ID
                    logger.debug('Auv Update Data: {}'.format(data))
                    self.publish('com.auv.update', data)
                else:
                    break

    async def heartbeat(self):
        """Broadcast heartbeat at 1Hz"""
        while True:
            await asyncio.sleep(1)
            self.publish('com.auv.heartbeat', 'ok')
            logger.debug('heartbeat')

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

    def start_trip(self, data):
        msg = {
            'cmd': 'start_trip',
        }
        self._relay_cmd(msg)

    def set_trip(self, trip):
        msg = {
            'cmd': 'set_trip',
            'kwargs': {
                'trip': trip
            }
        }
        self._relay_cmd(msg)

    def stop(self):
        msg = {
            'cmd': 'stop',
        }
        self._relay_cmd(msg)

    def update_settings(self, settings_dict):
        msg = {
            'cmd': 'update_settings',
            'kwargs': settings_dict,
        }
        self._relay_cmd(msg)


if __name__ == '__main__':
    import configparser
    crossbar_config = configparser.ConfigParser()
    crossbar_config.read('config.ini')
    url = crossbar_config['crossbar']['url']
    realm = crossbar_config['crossbar']['realm']
    runner = ApplicationRunner(url=url, realm=realm)
    runner.run(RemoteInterface)
