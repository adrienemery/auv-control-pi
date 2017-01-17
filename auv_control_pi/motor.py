from navio.pwm import PWM


T100 = 't100'
SERVO = 'servo'

# map of duty cycle settings in nanoseconds
# for more info on the T100 controller specs see
# https://www.bluerobotics.com/store/thrusters/besc-30-r1/
T100_PWM_MAP = {
    'max_forward': 1900 * 1e3,
    'min_forward': 1525 * 1e3,
    'stopped': 1500 * 1e3,
    'min_reverse': 1475 * 1e3,
    'max_reverse': 1100 * 1e3,
}

SERVO_PWM_MAP = T100_PWM_MAP  # TODO impliment with servo


class Motor:

    def __init__(self, channel, motor_type=T100, test=False):
        """

        Args:
            channel (int): PWM 0-13 channels are available
        """
        if motor_type == T100:
            self.pwm_map = T100_PWM_MAP
        elif motor_type == SERVO:
            self.pwm_map = SERVO_PWM_MAP
        else:
            raise ValueError('Unknown motor_type')
        self.channel = channel
        self.pwm = PWM(self.channel, test=test)
        self._speed = 0
        self.pwm.set_duty_cycle(self.pwm_map['stopped'])

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

        if value == 0:
            self.pwm.set_duty_cycle(self.pwm_map['stopped'])

        elif value > 0:
            duty_cycle = _calculate_value_in_range(
                min_val=self.pwm_map['min_forward'],
                max_val=self.pwm_map['max_forward'],
                percentage=value / 100,
            )
            self.pwm.set_duty_cycle(duty_cycle)

        elif value < 0:
            duty_cycle = _calculate_value_in_range(
                min_val=self.pwm_map['min_reverse'],
                max_val=self.pwm_map['max_reverse'],
                percentage=value / 100,
            )
            self.pwm.set_duty_cycle(duty_cycle)

        self._speed = value

    def forward(self, speed):
        self.speed = abs(speed)

    def reverse(self, speed):
        self.speed = -abs(speed)

    def stop(self):
        self.speed = 0


def _calculate_value_in_range(min_val, max_val, percentage):
    """Get the value within a range based on percentage.

    Example:
        A percentage 0.0 maps to min_val
        A percentage of 1.0 maps to max_val
    """
    range = max_val - min_val
    return min_val + int(percentage * range)
