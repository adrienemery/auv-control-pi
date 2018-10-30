import asyncio
import logging
import time
from threading import Thread

from navio.pwm import PWM

try:
    import spidev
    pi = True
except ImportError:
    pi = False

pi = True  # TODO make this an enviornment var


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
        self.duty_cycle_ms = self.pwm_map['stopped'] / 1000

        self.pwm = PWM(self.rc_channel - 1)
        self.initialized = False
        Thread(target=self._update).start()

    def initialize(self):
        """Must call to initialize the motor"""
        Thread(target=self._initialize).start()

    def _initialize(self):
        if pi:
            self.pwm.initialize()

            # setting the period is required before enabling the pwm channel
            self.pwm.set_period(PWM_FREQUENCY)
            self.pwm.enable()

            # To arm the ESC a "stop signal" is sent and held for 1s (up to 2s works too)
            # if you wait too long after the arming process to send the fist command to the ESC,
            # it will shut off and you will have to re-initialize
            self.stop()
            self.pwm.set_duty_cycle(self.duty_cycle_ms)
            time.sleep(1)
        logger.debug('{} Motor: initialized'.format(self.name.title()))
        self.initialized = True

    def _update(self):
        while True:
            if pi and self.initialized:
                self.pwm.set_duty_cycle(self.duty_cycle_ms)
            time.sleep(0.1)

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
        self.duty_cycle_ms = duty_cycle / 1000  # convert to milliseconds
        logger.debug('{} Motor: speed updated to ({} %, {} us)'.format(self.name.title(), value, self.duty_cycle_ms))

    def forward(self, speed):
        self.speed = abs(speed)

    def reverse(self, speed):
        self.speed = -abs(speed)

    def stop(self):
        self.speed = 0

    def __repr__(self):
        return 'Motor(name={}, rc_channel={})'.format(self.name, self.rc_channel)

    __str__ = __repr__
