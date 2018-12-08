import asyncio
import logging
from functools import wraps

from autobahn.asyncio import ApplicationSession as AutobahnApplicationSession

logger = logging.getLogger('wamp')


def subscribe(topic):
    if topic is None:
        raise ValueError('Must provide `topic `to subscribe to')

    def outer(fnc):
        @wraps(fnc)
        def inner(self, *args, **kwargs):
            return fnc(self, *args, **kwargs)
        inner.is_subcription = True
        inner.topic = topic
        return inner
    return outer


def rpc(rpc_uri=None):
    if rpc_uri is None:
        raise ValueError('Must provide rpc_uri')

    def outer(fnc):
        @wraps(fnc)
        def inner(*args, **kwargs):
            return fnc(*args, **kwargs)
        inner.is_rpc = True
        inner.rpc_uri = rpc_uri
        return inner
    return outer


class ApplicationSession(AutobahnApplicationSession):
    name = ''

    @classmethod
    def rpc_methods(cls, instance=None):
        _cls = instance or cls
        attrs = dir(_cls)
        attrs.remove('rpc_methods')
        methods = [getattr(_cls, attr) for attr in attrs if callable(getattr(_cls, attr))]
        rpc_methods = [method for method in methods if getattr(method, 'is_rpc', False)]
        return {method.rpc_uri: method for method in rpc_methods}

    @classmethod
    def rpc_uris(cls, instance=None):
        return cls.rpc_methods(instance).keys()

    @classmethod
    def subcribtion_handlers(cls, instance=None):
        _cls = instance or cls
        attrs = dir(_cls)
        attrs.remove('subcribtion_handlers')
        methods = [getattr(_cls, attr) for attr in attrs if callable(getattr(_cls, attr))]
        handlers = [method for method in methods if getattr(method, 'is_subcription', False)]
        return {method.topic: method for method in handlers}

    def onConnect(self):
        logger.info('Connecting to {} as {}'.format(self.config.realm, self.name))
        self.join(realm=self.config.realm)

    async def onJoin(self, details):
        logger.info('Joined realm as {}'.format(self.name))
        for rpc_uri, method in self.rpc_methods(self).items():
            logger.debug('Registering RPC: {}'.format(rpc_uri))
            await self.register(method, rpc_uri)

        for topic, handler in self.subcribtion_handlers(self).items():
            logger.debug('Subscribing To Topic: {}'.format(topic))
            await self.subscribe(handler, topic)

        loop = asyncio.get_event_loop()
        loop.create_task(self.update())

