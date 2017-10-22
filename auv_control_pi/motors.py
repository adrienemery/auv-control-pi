import curio
import logging

import time

from .asgi import channel_layer, MOTOR_CONTROL_CHANNEL
from navio.pwm import PWM

try:
    import spidev
    pi = True
except ImportError:
    pi = False

logger = logging.getLogger(__name__)

T100 = 't100'
SERVO = 'servo'

# map of duty cycle settings in milliseconds which is the
# units expected by the navio PWM module.
# For more info on the T100 controller specs see
# https://www.bluerobotics.com/store/thrusters/besc-30-r1/
T100_PWM_MAP = {
    'max_forward': 1900,
    'min_forward': 1525,
    'stopped': 1500,
    'min_reverse': 1475,
    'max_reverse': 1100,
}

SERVO_PWM_MAP = T100_PWM_MAP
PWM_FREQUENCY = 50  # Hz


def _calculate_value_in_range(min_val, max_val, percentage):
    """Get the value within a range based on percentage.

    Example:
        A percentage 0.0 maps to min_val
        A percentage of 1.0 maps to max_val
    """
    value_range = max_val - min_val
    return min_val + int(percentage * value_range)


class Motor:
    """An interface class to allow simple acces to motor functions"""

    def __init__(self, name, rc_channel, motor_type=T100, test=False):
        self.name = name
        self.rc_channel = rc_channel
        if motor_type == T100:
            self.pwm_map = T100_PWM_MAP
        elif motor_type == SERVO:
            self.pwm_map = SERVO_PWM_MAP
        else:
            raise ValueError('Unknown motor_type')

        self._speed = 0

        # add motor to the motor controller
        channel_layer.send(
            MOTOR_CONTROL_CHANNEL,
            {
                'cmd': 'add_motor',
                'kwargs': {'name': 'left', 'channel': self.rc_channel}
            }
        )

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, value):
        """Must be value betweeon -100 and 100

        Negative values indicate the motor is running in reverse.
        """
        # clamp the speed between -100 and 100
        value = max(-100, value)
        value = min(100, value)

        duty_cycle = self.pwm_map['stopped']
        if value > 0:
            duty_cycle = _calculate_value_in_range(
                min_val=self.pwm_map['min_forward'],
                max_val=self.pwm_map['max_forward'],
                percentage=value / 100,
            )

        elif value < 0:
            duty_cycle = _calculate_value_in_range(
                min_val=self.pwm_map['min_reverse'],
                max_val=self.pwm_map['max_reverse'],
                percentage=abs(value) / 100,
            )

        self._speed = value

        # update the motor conroller with the calculated duty cycle in microseconds
        channel_layer.send(
            MOTOR_CONTROL_CHANNEL,
            {
                'cmd': 'set_duty_cycle',
                'kwargs': {'name': 'left', 'duty_cycle_us': duty_cycle}
            }
        )

    def forward(self, speed):
        self.speed = abs(speed)

    def reverse(self, speed):
        self.speed = -abs(speed)

    def stop(self):
        self.speed = 0


class MotorController:
    """Manage each motor's initialization and updating duty cycle
    """

    def __init__(self):
        self.motors = {}

    async def add_motor(self, name, channel):
        logger.warning('Adding Motor(name={}, channel={})'.format(name, channel))
        # we need to add one to the channel since they are 0 indexed in code
        # but 1 indexed on the navio2 board
        self.motors[name] = {'pwm': PWM(channel - 1), 'duty_cycle': T100_PWM_MAP['stopped'] / 1000, 'initialized': False}
        await curio.run_in_thread(self.initialize_motor, name)

    async def set_duty_cycle(self, name, duty_cycle_us):
        duty_cycle_ms = duty_cycle_us / 1000  # convert to milliseconds
        logger.warning('Setting {} motor duty cycle to {}'.format(name, duty_cycle_ms))
        self.motors[name]['duty_cycle'] = duty_cycle_ms

    def initialize_motor(self, name):
        """Initialization sequence for each new motor

        This is a blocking method and should be run in a thread or proceess.
        """
        pwm = self.motors[name]['pwm']
        if pi:
            pwm.initialize()
            pwm.set_period(PWM_FREQUENCY)
            pwm.enable()
            pwm.set_duty_cycle(self.motors[name]['duty_cycle'])
            time.sleep(1)
            self.motors[name]['initialized'] = True

    async def _read_commands(self):
        """Check for incoming commands on the motor control channel"""
        channels = [MOTOR_CONTROL_CHANNEL]
        # read all messages off of channel
        while True:
            _, data = channel_layer.receive_many(channels)
            if data:
                logger.debug('Recieved data: {}'.format(data))
                try:
                    fnc = getattr(self, data.get('cmd'))
                except AttributeError:
                    pass
                else:
                    if fnc and callable(fnc):
                        try:
                            await fnc(**data.get('kwargs', {}))
                        except Exception as exc:
                            logger.error(exc)
            else:
                await curio.sleep(0.05)  # chill out for a bit

    async def _update(self):
        """Update the duty cycle for each registered motor"""
        while True:
            for motor_name, data in self.motors.items():
                if pi:
                    if data['initialized']:
                        await curio.run_in_thread(data['pwm'].set_duty_cycle, data['duty_cycle'])
            await curio.sleep(0.05)

    async def run(self):
        """Main entry point"""
        logger.warning('Starting Motor Controller')
        await curio.spawn(self._update())
        await curio.spawn(self._read_commands())


motor_controller = MotorController()

if __name__ == '__main__':
    motor_controller.run()
