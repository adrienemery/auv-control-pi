
from asgi import channel_layer


class RemoteInterface(ApplicationSession):

    DEFAULT_TURN_SPEED = 0.5
    DEFAULT_FORWARD_SPEED = 0.5
    DEFAULT_REVERSE_SPEED = 0.5
    SERIAL_SEND_CHANNEL = 'serial.send'
    SERIAL_RECV_CHANNEL = 'serial.recv'

    def __init__(serial_obj, *args, **kwargs):
        self._serial = serial_obj
        self._auto = False

    def send_serial(msg):
        channel_layer.send(self.SERIAL_SEND_CHANNEL, msg)

    def move_right(speed=None):
        speed = self.DEFAULT_FORWARD_SPEED or speed
        assert 0 <= speed <= 1
        msg = {
            'fnc': 'move_right',
            'kwargs': {'speed': speed}
        }
        self.send_serial(msg)

    def move_left(speed=None):
        pass

    def move_forward(speed=None):
        pass

    def move_reverse(speed=None):
        pass

    def stop():
        pass

    def enable_manual_control():
        # send message to disable auto pilot on APM
        self._auto = False
        # return

    def start_trip(trip_id):
        pass
