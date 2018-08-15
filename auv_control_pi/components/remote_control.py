import logging

from autobahn.asyncio.component import Component, run

logger = logging.getLogger(__name__)


class RouterProxy:
    """A Proxy connect the remoute WAMP router to the local WAMP router

    This allows us to expose RPC + Pub/Sub to the internet for remote control,
    while still keeping a simple local interface where all local components
    just connect to the local WAMP router.

    When new RPC methods are added they need to be registered here.
    Similarly when new topics are published we need to add subscribers here to
    "re-publish" them to the remote WAMP router.

    """

    def __init__(self, remote_component, local_component):
        self.remote_wamp = local_component
        self.local_wamp = remote_component
        self.remote_session = None  # None while we're disconnected from WAMP router
        self.local_session = None  # None while we're disconnected from WAMP router

        # associate ourselves with each WAMP session lifecycle
        self.remote_wamp.on('join', self.join_remote)
        self.local_wamp.on('join', self.join_local)

    def join_remote(self, session, details):
        logger.info("Connected to Remote WAMP router")
        self.remote_session = session
        self.remote_session.register(self.auv_turn_left, 'auv.turn_left')
        self.remote_session.register(self.auv_turn_right, 'auv.turn_right')
        # TODO get list of all registered RPC's and register them on the remote wamp router

    def join_local(self, session, details):
        logger.info("Connected to Local WAMP router")
        self.local_session = session

    def auv_turn_right(self, *args, **kwargs):
        self.local_session.call('auv.turn_right', *args, **kwargs)

    def auv_turn_left(self, *args, **kwargs):
        self.local_session.call('auv.turn_left', *args, **kwargs)


# TODO get the url and realm from the configuration values in the database

remote_comp = Component(
    transports="ws://localhost:8080/ws",
    realm="realm1",
)

local_comp = Component(
    transports="ws://crossbar:8080/ws",
    realm="realm1",
)


def main():
    RouterProxy(remote_comp, local_comp)
    run([remote_comp, local_comp])


if __name__ == "__main__":
    main()

