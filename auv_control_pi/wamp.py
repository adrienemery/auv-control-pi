import asyncio
import logging

from autobahn.asyncio import ApplicationSession as AutobahnApplicationSession

logger = logging.getLogger('wamp')


def subscribe(topic):
    if topic is None:
        raise ValueError('Must provide `topic `to subscribe to')

    def outer(fnc):
        def inner(*args, **kwargs):
            fnc(*args, **kwargs)
        inner.is_subcription = True
        inner.topic = topic
        return inner
    return outer


def rpc(rpc_uri=None):
    if rpc_uri is None:
        raise ValueError('Must provide rpc_uri')

    def outer(fnc):
        def inner(*args, **kwargs):
            fnc(*args, **kwargs)
        inner.is_rpc = True
        inner.rpc_uri = rpc_uri
        return inner
    return outer


class ApplicationSession(AutobahnApplicationSession):
    name = ''

    @classmethod
    def rpc_methods(cls):
        attrs = dir(cls)
        attrs.remove('rpc_methods')
        methods = [getattr(cls, attr) for attr in attrs if callable(getattr(cls, attr))]
        rpc_methods = [method for method in methods if getattr(method, 'is_rpc', False)]
        return {method.rpc_uri: method for method in rpc_methods}

    @classmethod
    def rpc_uris(cls):
        return cls.rpc_methods().keys()

    def subcribtion_handles(cls):
        attrs = dir(cls)
        attrs.remove('subcribtion_handles')
        methods = [getattr(cls, attr) for attr in attrs if callable(getattr(cls, attr))]
        handlers = [method for method in methods if getattr(method, 'is_subcription', False)]
        return {method.topic: method for method in handlers}

    async def onJoin(self, details):
        logger.info('Joined realm as {}'.format(self.name))
        for rpc_uri, method in self.rpc_methods().items():
            logger.debug('Registering RPC: {}'.format(rpc_uri))
            await self.register(method, rpc_uri)

        for topic, handler in self.subcribtion_handles().items():
            logger.debug('Subscribing To Topic: {}'.format(topic))
            await self.subscribe(handler, topic)

        loop = asyncio.get_event_loop()
        loop.create_task(self.update())

