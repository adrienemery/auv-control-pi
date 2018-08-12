import asyncio
import logging

import time
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from navio.rcinput import RCInput


logger = logging.getLogger(__name__)

RC_LOW = 999
RC_HIGH = 1999
STOP_RANGE = 50
REVERSE_THRESHOLD = 1500 - STOP_RANGE
FORWARD_THRESHOLD = 1500 + STOP_RANGE
LEFT_THRESHOLD = 1500 - STOP_RANGE
RIGHT_THRESHOLD = 1500 + STOP_RANGE
ARMED_THRESHOLD = 1500

RC_THROTTLE_CHANNEL = 2
RC_TURN_CHANNEL = 0
RC_ARM_CHANNEL = 6


class RCControler(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.armed = False
        self.rc_input = RCInput()

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, 'rc_control'))
        self.join(realm=self.config.realm)

    def onJoin(self, details):
        """Register functions for access via RPC and start update loops"""
        logger.info("Joined Crossbar Session")

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self._update())

    async def _update(self):
        """Broadcast current state on the auv update channel"""
        last_throttle_signal = None
        last_turn_signal = None

        while True:
            # main loop

            rc_armed = int(self.rc_input.read(ch=RC_ARM_CHANNEL))
            if rc_armed < ARMED_THRESHOLD and self.armed is True:
                logger.info('RC Control Disarmed')
                self.armed = False
            elif rc_armed > ARMED_THRESHOLD and self.armed is False:
                logger.info('RC Control Armed')
                self.armed = True

            if self.armed:
                rc_throttle = int(self.rc_input.read(ch=RC_THROTTLE_CHANNEL))
                rc_turn = int(self.rc_input.read(ch=RC_TURN_CHANNEL))

                # only update if the signal has changed
                if last_throttle_signal and rc_throttle != last_throttle_signal:
                    if rc_throttle < REVERSE_THRESHOLD:
                        self.call('auv.reverse_throttle', rc_throttle)
                    elif rc_throttle > FORWARD_THRESHOLD:
                        self.call('auv.forward_throttle', rc_throttle)
                    else:
                        self.call('auv.stop')

                # store the current reading for use next time around the loop
                last_throttle_signal = rc_throttle

                if last_turn_signal and rc_turn != last_turn_signal:
                    if rc_turn < LEFT_THRESHOLD:
                        self.call('auv.move_left', rc_turn)
                    elif rc_turn > RIGHT_THRESHOLD:
                        self.call('auv.move_right', rc_turn)
                    else:
                        self.call('auv.move_center')

            await asyncio.sleep(0.05)


if __name__ == '__main__':
    time.sleep(5)
    runner = ApplicationRunner(url='ws://crossbar:8080/ws', realm='realm1')
    runner.run(RCControler)
