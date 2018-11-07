import asyncio
import logging

import time
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from navio.rcinput import RCInput


logger = logging.getLogger(__name__)

RC_LOW = 999  # the lower limit of rc input vlaues
RC_HIGH = 1999  # the upper limit of rc input values

# the stop range sets the width within the rc input values
# that are considered a stop command (in the case of forward/reverse throttle)
# and a no turn command (in the case of left/right turn input)
STOP_RANGE = 50

# forward and reverse thresholds set the limit on when a command will begin
# to increse the throttle in the forward and reverse direction respectively
FORWARD_THRESHOLD = 1500 + STOP_RANGE
REVERSE_THRESHOLD = 1500 - STOP_RANGE

# left and right thresholds set the limit on when a command will begin
# to increse the turn command in the left and right direction respectively
LEFT_THRESHOLD = 1500 - STOP_RANGE
RIGHT_THRESHOLD = 1500 + STOP_RANGE

# RC input below the armed threshold will disarm the rc controller
# and it will not respond to any control input
# RC input above the armed threshold will arm the rc controller and thus
# respond to subsequent commands
ARMED_THRESHOLD = 1500

# define the channels for rc input
RC_THROTTLE_CHANNEL = 2
RC_TURN_CHANNEL = 0
RC_ARM_CHANNEL = 6
RC_TRIM_CHANNEL = 3

# the debounce range value is used to ignore changes in rc input
# that are within the debounce range
DEBOUNCE_RANGE = 5
TRIM_DEBOUNCE_RANGE = 3


class RCControler(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.armed = False
        self.rc_input = RCInput()
        self.last_throttle_signal = None
        self.last_turn_signal = None
        self.update_frequency = 10
        self.trim_center = None

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'rc_control'))
        self.join(realm=self.config.realm)

    def onJoin(self, details):
        """Register functions for access via RPC and start update loops
        """
        logger.info("Joined Crossbar Session")

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self.run())
        loop.create_task(self.update())

    async def update(self):
        while True:
            self.publish(
                'rc_control.update',
                {
                    'armed': self.armed,
                    'throttle': self.last_throttle_signal,
                    'turn': self.last_turn_signal,
                    'trim_center': self.trim_center
                }
            )
            await asyncio.sleep(1 / self.update_frequency)

    async def run(self):
        """Main controll loop
        """
        while True:
            # check if the armed button is on/off
            rc_armed = int(self.rc_input.read(ch=RC_ARM_CHANNEL))
            if rc_armed < ARMED_THRESHOLD and self.armed is True:
                logger.info('RC Control: Disarmed')
                self.call('auv.stop')
                self.armed = False

            elif rc_armed > ARMED_THRESHOLD and self.armed is False:
                logger.info('RC Control: Armed')
                self.armed = True
                self.trim_center = int(self.rc_input.read(RC_TRIM_CHANNEL))

            # TODO when initially armed it would be useful to force the user to zero
            # the throttle and turn inputs before any new commands are registered
            # This will prevent connecting via the RC controller and having the throttle
            # already engaged which could cause unexpected behaviour.

            # only respond to commands when the rc is armed
            if self.armed:
                rc_throttle = int(self.rc_input.read(ch=RC_THROTTLE_CHANNEL))
                rc_turn = int(self.rc_input.read(ch=RC_TURN_CHANNEL))
                rc_trim = int(self.rc_input.read(ch=RC_TRIM_CHANNEL))

                # the rc controller doesn't have any "buttons" that can easily be used for trim
                # however it does have builtin trim buttons that adjust the value being sent for
                # a given control axis. We use the x-axis trim on the left joystick as a trim input
                # button. By updating the trim center point we can track a change in either the
                # left (negative) or right (posative) direction and treat it as a "button press"
                # which we use to call the `trim_left` and `trim_right` commands.
                if abs(rc_trim - self.trim_center) > TRIM_DEBOUNCE_RANGE:
                    if rc_trim > self.trim_center:
                        self.trim_center = rc_trim
                        self.call('auv.trim_right')
                    else:
                        self.trim_center = rc_trim
                        self.call('auv.trim_left')

                # only update if the signal has changed
                if self.last_throttle_signal is not None and abs(rc_throttle - self.last_throttle_signal) > DEBOUNCE_RANGE:
                    if rc_throttle < REVERSE_THRESHOLD:
                        throttle = int(100 * abs(rc_throttle - REVERSE_THRESHOLD) / abs(RC_LOW - REVERSE_THRESHOLD))
                        self.call('auv.reverse_throttle', throttle)
                    elif rc_throttle > FORWARD_THRESHOLD:
                        throttle = int(100 * abs(rc_throttle - FORWARD_THRESHOLD) / abs(RC_HIGH - FORWARD_THRESHOLD))
                        self.call('auv.forward_throttle', throttle)
                    else:
                        self.call('auv.stop')

                    # store the current reading for use next time around the loop
                    self.last_throttle_signal = rc_throttle

                if self.last_throttle_signal is None:
                    self.last_throttle_signal = rc_throttle

                if self.last_turn_signal is not None and abs(rc_turn - self.last_turn_signal) > DEBOUNCE_RANGE:
                    if rc_turn < LEFT_THRESHOLD:
                        turn = int(100 * abs(rc_turn - LEFT_THRESHOLD) / abs(RC_LOW - LEFT_THRESHOLD))
                        self.call('auv.move_left', turn)
                    elif rc_turn > RIGHT_THRESHOLD:
                        turn = int(100 * abs(rc_turn - RIGHT_THRESHOLD) / abs(RC_HIGH - RIGHT_THRESHOLD))
                        self.call('auv.move_right', turn)
                    else:
                        self.call('auv.move_center')

                    # store the current reading for use next time around the loop
                    self.last_turn_signal = rc_turn

                if self.last_turn_signal is None:
                    self.last_turn_signal = rc_turn

            # wait a little bit until reading in a new command to prevent twichy controls
            await asyncio.sleep(0.05)
