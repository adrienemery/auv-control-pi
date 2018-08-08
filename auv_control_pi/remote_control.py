import asyncio
import logging

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from channels import Channel

from .asgi import channel_layer, AUV_SEND_CHANNEL
from .models import Configuration

logger = logging.getLogger(__name__)


class RemoteInterface(ApplicationSession):

    DEFAULT_TURN_SPEED = 50
    DEFAULT_FORWARD_SPEED = 50
    DEFAULT_REVERSE_SPEED = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # generate a unique channel name for ourselves
        # subscribe to the auv update channel

    def _relay_cmd(self, msg):
        """Relay commands to Mothership over asgi channels"""
        assert isinstance(msg, dict)
        msg['sender'] = 'remote_control'
        Channel(AUV_SEND_CHANNEL).send(msg)
        logger.info('sending cmd: {}'.format(msg))

    @staticmethod
    def _check_speed(speed):
        if not -100 <= speed <= 100:
            err_msg = 'speed must be in range -100 <= speed <= 100, got {}'.format(speed)
            raise ValueError(err_msg)

    def onChallenge(self, challenge):
        """Handle authentication challenge"""
        if challenge.method == 'ticket':
            logger.info("WAMP-Ticket challenge received: {}".format(challenge))
            config = Configuration.get_solo()
            return config.auth_token
        else:
            raise Exception("Invalid authmethod {}".format(challenge.method))

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'auv'))
        self.join(realm=self.config.realm, authmethods=['ticket', 'anonymous'], authid='auv')

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")

        await self.register(self.move_right, 'auv.move_right')
        await self.register(self.move_left, 'auv.move_left')
        await self.register(self.set_left_motor_speed, 'auv.set_left_motor_speed')
        await self.register(self.set_right_motor_speed, 'auv.set_right_motor_speed')
        await self.register(self.move_forward, 'auv.move_forward')
        await self.register(self.move_reverse, 'auv.move_reverse')
        await self.register(self.stop, 'auv.stop')
        await self.register(self.move_to_waypoint, 'auv.move_to_waypoint')
        await self.register(self.start_trip, 'auv.start_trip')
        await self.register(self.set_trip, 'auv.set_trip')
        await self.register(self.update_settings, 'auv.update_settings')

        # create subtasks
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self._connected(), loop=loop)
        asyncio.ensure_future(self.heartbeat(), loop=loop)
        asyncio.ensure_future(self.update(), loop=loop)

    async def _connected(self):
        """Let everyone know that we have connected"""
        config = Configuration.get_solo()
        self.publish('auv.connected', str(config.auv_id))

    async def update(self):
        """Broadcast updates whenever recieved on update channel"""
        while True:
            await asyncio.sleep(0.1)
            channels = ['auv.update']
            while True:
                _, data = channel_layer.receive_many(channels)
                if data:
                    config = Configuration.get_solo()
                    data['auv_id'] = str(config.auv_id)
                    logger.debug('Auv Update Data: {}'.format(data))
                    self.publish('auv.update', data)
                else:
                    break

    async def heartbeat(self):
        """Broadcast heartbeat at 1Hz"""
        while True:
            await asyncio.sleep(1)
            self.publish('auv.heartbeat', 'ok')
            logger.debug('heartbeat')

    def set_left_motor_speed(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'set_motor_speed',
            'params': {
                'motor_side': 'left',
                'speed': speed
            }
        }
        self._relay_cmd(msg)

    def set_right_motor_speed(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'set_motor_speed',
            'params': {
                'motor_side': 'right',
                'speed': speed
            }
        }
        self._relay_cmd(msg)

    def move_right(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_right',
            'params': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_left(self, speed=None):
        speed = self.DEFAULT_TURN_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_left',
            'params': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_forward(self, speed=None):
        speed = self.DEFAULT_FORWARD_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_forward',
            'params': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_reverse(self, speed=None):
        speed = self.DEFAULT_REVERSE_SPEED or speed
        self._check_speed(speed)
        msg = {
            'cmd': 'move_reverse',
            'params': {'speed': speed}
        }
        self._relay_cmd(msg)

    def move_to_waypoint(self, lat, lng):
        msg = {
            'cmd': 'move_to_waypoint',
            'params': {
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
            'params': {
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
            'params': settings_dict,
        }
        self._relay_cmd(msg)


if __name__ == '__main__':
    runner = ApplicationRunner(url='ws://localhost:8000/ws', realm='realm1')
    runner.run(RemoteInterface)
