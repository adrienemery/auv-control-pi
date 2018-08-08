import asyncio
import logging
import time

from autobahn.asyncio import ApplicationSession
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

    def __init__(self, name, rc_channel, wamp_session=None, motor_type=T100):
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
        if wamp_session is None:
            # TODO use wampy or other means to make rpc calls
            pass
        else:
            self.wamp_session = wamp_session
        self.initialized = False

    def initialize(self):
        self.wamp_session.call('motor_control.add_motor', self.name, self.rc_channel)
        self.initialized = True

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
        if self.initialized:
            self.wamp_session.call('motor_control.set_duty_cycle', self.name, duty_cycle)

    def forward(self, speed):
        self.speed = abs(speed)

    def reverse(self, speed):
        self.speed = -abs(speed)

    def stop(self):
        self.speed = 0

    def __repr__(self):
        return 'Motor(name={}, rc_channel={})'.format(self.name, self.rc_channel)

    __str__ = __repr__


class MotorController(ApplicationSession):
    """Manage each motor's initialization and updating duty cycle
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motors = {}

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'motor_control'))
        self.join(realm=self.config.realm)

    def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")

        self.register(self.add_motor, 'motor_control.add_motor')
        self.register(self.set_duty_cycle, 'motor_control.set_duty_cycle')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    def add_motor(self, name, channel):
        logger.info('Adding Motor(name={}, channel={})'.format(name, channel))
        # we need to add one to the channel since they are 0 indexed in code
        # but 1 indexed on the navio2 board
        self.motors[name] = {'pwm': PWM(channel - 1), 'duty_cycle': T100_PWM_MAP['stopped'] / 1000, 'initialized': False}
        self._initialize_motor(name)

    def set_duty_cycle(self, name, duty_cycle_us):
        duty_cycle_ms = duty_cycle_us / 1000  # convert to milliseconds
        logger.info('Setting {} motor duty cycle to {}'.format(name, duty_cycle_ms))
        self.motors[name]['duty_cycle'] = duty_cycle_ms

    def _initialize_motor(self, name):
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
            # if you wait too long after the arming process to send the fist command to the ESC,
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
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(data['pwm'].set_duty_cycle, data['duty_cycle'])
            await asyncio.sleep(0.05)


motor_controller = MotorController()

if __name__ == '__main__':
    motor_controller.run()
