import logging
import json

import curio

from channels import Channel
from .asgi import AUV_SEND_CHANNEL, channel_layer


def ws_add(message):
    """Connected to websocket.connect"""
    # Accept the incoming connection
    message.reply_channel.send(
        {"accept": True}
    )


def ws_message(message):
    """Connected to websocket.receive"""
    message.reply_channel.send({
        "text": message.content['text'],
    })
    json_msg = json.loads(message.content['text'])
    Channel(AUV_SEND_CHANNEL).send(content=json_msg)


def ws_disconnect(message):
    """Connected to websocket.disconnect"""
    pass


class AsyncConsumer:
    channels = []

    async def _read_commands(self):
        """Check for incoming commands on the motor control channel"""
        # read all messages off of channel
        while True:
            _, data = channel_layer.receive_many(self.channels)
            if data:
                logging.debug('Recieved data: {}'.format(data))
                try:
                    fnc = getattr(self, data.get('cmd'))
                except AttributeError:
                    pass
                else:
                    if fnc and callable(fnc):
                        try:
                            await curio.run_in_thread(fnc, **data.get('params', {}))
                        except Exception as exc:
                            logging.error(exc)
            else:
                await curio.sleep(0.05)  # chill out for a bit

