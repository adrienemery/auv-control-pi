import serial
from serial.tools import list_ports

from asgi import channel_layer


class PortNotFound(serial.SerialException):
    pass


class AUVController:

    def __init__(self):
        ports = list(list_ports.grep('usb'))
        if not ports:
            print('No USB ports found')
            self._serial = None
        else:
            self._serial = serial.Serial(port=ports[0].device, timeout=0, write_timeout=0.1)

    def move_right(self, speed=None, **kwargs):
        print('move right with speed {}'.format(speed))

    def move_left(self, speed=None, **kwargs):
        print('move left with speed {}'.format(speed))


def main():
    controller = AUVController()
    while True:
        # check for commands to send to auv
        channels = ['serial.send']
        channel, data = channel_layer.receive_many(channels)
        if data:
            print(data)
            fnc = getattr(controller, data.get('cmd'))
            if fnc and callable(fnc):
                fnc(**data.get('kwargs'))

if __name__ == '__main__':
    main()
