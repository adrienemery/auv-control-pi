import curio
import logging

import time

from channels import Channel

from auv_control_pi.consumers import AsyncConsumer
from .asgi import channel_layer, MOTOR_CONTROL_CHANNEL
from navio.pwm import PWM

try:
    import spidev
    pi = True
except ImportError:
    pi = False


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


T100 = 't100'
SERVO = 'servo'

# map of duty cycle settings in milliseconds which is the
# units expected by the navio PWM module.
# For more info on the T100 controller specs see
# https://www.bluerobotics.com/store/thrusters/besc-30-r1/
T100_PWM_MAP = {
    'max_forward': int((1900 - 1525) * 0.9) + 1525,  # limit max mower to avoid burning out motor
    'min_forward': 1525,
    'stopped': 1500,
    'min_reverse': 1475,
    'max_reverse': 1475 - int((1475 - 1100) * 0.9),  # limit max mower to avoid burning out motor
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

    def __init__(self, name, rc_channel, motor_type=T100):
        self.name = name
        self.rc_channel = rc_channel
        if motor_type == T100:
            self.pwm_map = T100_PWM_MAP
        elif motor_type == SERVO:
            self.pwm_map = SERVO_PWM_MAP
        else:
            raise ValueError('Unknown motor_type')

        self._speed = 0
        self.duty_cycle = self.pwm_map['stopped']

        # add motor to the motor controller
        Channel(MOTOR_CONTROL_CHANNEL).send(
            {
                'cmd': 'add_motor',
                'params': {'name': self.name, 'channel': self.rc_channel}
            }
        )

    def __repr__(self):
        return 'Motor(name={}, rc_channel={})'.format(self.name, self.rc_channel)

    __str__ = __repr__

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
        self.duty_cycle = duty_cycle

        # update the motor conroller with the calculated duty cycle in microseconds
        Channel(MOTOR_CONTROL_CHANNEL).send(
            {
                'cmd': 'set_duty_cycle',
                'params': {'name': self.name, 'duty_cycle_us': duty_cycle}
            }
        )

    def forward(self, speed):
        self.speed = abs(speed)

    def reverse(self, speed):
        self.speed = -abs(speed)

    def stop(self):
        self.speed = 0


class MotorController(AsyncConsumer):
    """Manage each motor's initialization and updating duty cycle
    """
    channels = [MOTOR_CONTROL_CHANNEL]

    def __init__(self):
        self.motors = {}

    def add_motor(self, name, channel):
        logger.info('Adding Motor(name={}, channel={})'.format(name, channel))
        # we need to add one to the channel since they are 0 indexed in code
        # but 1 indexed on the navio2 board
        self.motors[name] = {'pwm': PWM(channel - 1), 'duty_cycle': T100_PWM_MAP['stopped'] / 1000, 'initialized': False}
        self.initialize_motor(name)

    def set_duty_cycle(self, name, duty_cycle_us):
        duty_cycle_ms = duty_cycle_us / 1000  # convert to milliseconds
        logger.info('Setting {} motor duty cycle to {}'.format(name, duty_cycle_ms))
        self.motors[name]['duty_cycle'] = duty_cycle_ms

    def initialize_motor(self, name):
        """Initialization sequence for each new motor

        This is a blocking method and should be run in a thread or proceess.
        """
        pwm = self.motors[name]['pwm']
        if pi:
            pwm.initialize()

            # setting the period is required before enabling the pwm channel
            pwm.set_period(PWM_FREQUENCY)
            pwm.enable()

            # To arm the ESC a "stop signal" is sent and held for 1s (up to 2s works too)
            # if you wait to long after the Arming process to send the fist command to the ESC,
            # it will shut off and you will have to re-initialize
            pwm.set_duty_cycle(self.motors[name]['duty_cycle'])
            time.sleep(1)
            self.motors[name]['initialized'] = True

    def turn_off_motor(self, name):
        pass  # TODO

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
        logger.info('Starting Motor Controller')
        await curio.spawn(self._update())
        await curio.spawn(self._read_commands())


motor_controller = MotorController()

if __name__ == '__main__':
    motor_controller.run()
