import logging

from autobahn.asyncio.component import Component, run
from ..config import config
from .ahrs import AHRS
from .auv_control import AUV
from .gps import GPSComponent
from .navigation import Navitgator


logger = logging.getLogger(__name__)


class RouterProxy:
    """A Proxy connect the remoute WAMP router to the local WAMP router

    This allows us to expose RPC + Pub/Sub to the internet for remote control,
    while still keeping a simple local interface where all local components
    just connect to the local WAMP router.

    When new RPC methods are added they need to be registered here.
    Similarly when new topics are published we need to add the topics here to
    "re-publish" them to the remote WAMP router.

    """
    rpc_proxy_classes = [
        AHRS,
        GPSComponent,
        AUV,
        Navitgator
    ]
    published_topics_proxy = [
        'auv.update',
        'nav.update',
        'ahrs.update',
        'rc_control.update',
        'gps.update',
        # add topics here to expose them to remote router
    ]

    def __init__(self, remote_component, local_component):
        self.remote_wamp = remote_component
        self.local_wamp = local_component
        self.remote_session = None  # None while we're disconnected from WAMP router
        self.local_session = None  # None while we're disconnected from WAMP router

        # associate ourselves with each WAMP session lifecycle
        self.remote_wamp.on('join', self.join_remote)
        # self.remote_wamp.on('challenge', self.on_remote_challenge)
        self.local_wamp.on('join', self.join_local)

    @property
    def rpc_proxy_list(self):
        rpcs = []
        for cls in self.rpc_proxy_classes:
            rpcs.extend(cls.rpc_uris())
        return rpcs

    async def register_rpc_proxies(self):
        """Register RPC methods on remote router that mirror RPC's on the local router

        This allows a remote component to call RPC's on the local WAMP router.
        """
        for rpc_name in self.rpc_proxy_list:
            logger.debug('Registering RPC to Proxy: {}'.format(rpc_name))

            class RPCProxy:

                def __init__(self, local_session, rpc_name):
                    self._local_session = local_session
                    self._rpc_name = rpc_name

                async def __call__(self, *args, **kwargs):
                    logger.debug('Proxying RPC {}, with args {}, kwargs {}'.format(self._rpc_name, args, kwargs))
                    return await self._local_session.call(self._rpc_name, *args, **kwargs)

            await self.remote_session.register(RPCProxy(self.local_session, rpc_name), rpc_name)

    async def register_pub_sub_proxies(self):
        """Publish data to remote router on topics that we are subscribed to locally

        This allows remote components to subscribe to topics that are published
        locally since they are being "re-published".
        """
        for topic in self.published_topics_proxy:

            class PubSubProxy:

                def __init__(self, remote_session, topic):
                    self._remote_session = remote_session
                    self._topic = topic

                async def __call__(self, *args, **kwargs):
                    self._remote_session.publish(self._topic, *args, **kwargs)

            # subscribe to the local topics published so they can be "re-published" on the remote session
            await self.local_session.subscribe(PubSubProxy(self.remote_session, topic), topic)

    async def register_proxies(self):
        # ensure we have both remote and local sessions setup before
        # registering proxy rpc's and pub/sub's
        if self.remote_session and self.local_session:
            await self.register_pub_sub_proxies()
            await self.register_rpc_proxies()

    async def join_remote(self, session, details):
        """Handle setup when we join the remote router
        """
        logger.info("Connected to Remote WAMP router")
        self.remote_session = session
        await self.register_proxies()

    async def join_local(self, session, details):
        """Handle setup when we join the local router
        """
        logger.info("Connected to Local WAMP router")
        self.local_session = session
        await self.register_proxies()


remote_comp = Component(
    transports=config.crossbar_url,
    realm=config.crossbar_realm,
    authentication={
        'ticket': {
            'ticket': config.auth_token,
            'authid': 'auv'
        }
    },
)

local_comp = Component(
    transports="ws://crossbar:8080/ws",
    realm="realm1",
)


def main():
    RouterProxy(remote_comp, local_comp)
    run([local_comp, remote_comp])


if __name__ == "__main__":
    main()

