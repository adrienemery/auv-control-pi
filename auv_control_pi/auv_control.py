import curio

from collections import deque
from .asgi import channel_layer, AUV_SEND_CHANNEL, AUV_UPDATE_CHANNEL


class Mothership:

    def __init__(self):
        self.lat = None
        self.lng = None
        self.heading = 0
        self.speed = 0
        self.water_temperature = 0
        self.command_buffer = deque()

    async def move_right(self, speed=None, **kwargs):
        self.send('move right with speed {}'.format(speed))

    async def move_left(self, speed=None, **kwargs):
        self.send('move left with speed {}'.format(speed))

    async def move_forward(self, speed=None, **kwargs):
        self.send('move forward with speed {}'.format(speed))

    async def move_reverse(self, speed=None, **kwargs):
        self.send('move reverse with speed {}'.format(speed))

    async def stop(self, **kwargs):
        self.send('stop')

    async def move_to_waypoint(self, lat, lon, **kwargs):
        self.send('moving to waypoint: ({}, {})'.format(lat, lon))

    async def start_trip(self, trip_id, **kwargs):
        # download waypoints
        pass

    async def send(self, msg):
        self.command_buffer.append(msg)

    async def run(self):
        await curio.spawn(self._flush_command_buffer())
        await curio.spawn(self._update())

    async def _flush_command_buffer(self):
        while True:
            try:
                print(self.command_buffer.popleft())
            except IndexError:
                pass
            await curio.sleep(0.05)

    def _parse_raw_data(self, raw_data):
        # TODO handle list of raw_data
        return {}

    async def _update(self):
        """
        Read in data from serial buffer and broadcast on
        the auv update channel.
        """
        while True:
            update_attrs = ('lat', 'lng', 'heading', 'speed', 'water_temperature')
            msg = {attr: getattr(self, attr) for attr in update_attrs}
            channel_layer.send(AUV_UPDATE_CHANNEL, msg)
            await curio.sleep(1)


async def main():
    controller = Mothership()
    await curio.spawn(controller.run())

    # main loop
    while True:
        # check for commands to send to auv
        channels = [AUV_SEND_CHANNEL]
        # read all messages off of channel
        while True:
            _, data = channel_layer.receive_many(channels)
            if data:
                print(data)
                try:
                    fnc = getattr(controller, data.get('cmd'))
                except AttributeError:
                    pass
                else:
                    if fnc and callable(fnc):
                        await fnc(**data.get('kwargs', {}))
            else:
                break
        await curio.sleep(0.05)  # chill out for a bit


if __name__ == '__main__':
    curio.run(main())
