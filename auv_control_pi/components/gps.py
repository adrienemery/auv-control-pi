import os
import asyncio
import logging

from autobahn.asyncio import ApplicationSession
from navio.gps import GPS
from ..models import GPSLog

logger = logging.getLogger(__name__)
PI = os.getenv('PI', False)


class GPSComponent(ApplicationSession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize the gps
        if PI:
            self.lat = None
            self.lng = None
            self.gps = GPS()
        else:
            self.gps = None
            self.lat = 49.2827
            self.lng = -123.1207

        self.status = None
        self.height_ellipsoid = None
        self.height_sea = None
        self.horizontal_accruacy = None
        self.vertiacl_accruracy = None

    def onConnect(self):
        self.join(realm=self.config.realm)

    async def onJoin(self, details):
        """Register functions for access via RPC and start update loops
        """
        logger.info("GPS Component: Joined Crossbar Session")

        # register rpc methods
        await self.register(self.get_position, 'gps.get_position')
        await self.register(self.get_status, 'gps.get_status')

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self.update())

    def get_position(self):
        return self.lat, self.lng

    def get_status(self):
        return self.status

    def _parse_msg(self, msg):
        """
        Update all local instance variables
        """
        if self.msg.name() == "NAV_POSLLH":
            outstr = str(self.msg).split(",")[1:]
            outstr = "".join(outstr)
            print(outstr)
            print(msg._fields)

            self.lat = msg.lat / 10e6
            self.lng = msg.lon / 10e6
            self.height_ellipsoid = msg.heightEll
            self.height_sea = msg.heightSea
            self.horizontal_accruacy = msg.horAcc
            self.vertiacl_accruracy = msg.verAcc

    async def update(self):
        while True:
            if PI:
                msg = self.gps.update()
                self._parse_msg(msg)

            payload = {
                'lat': self.lat,
                'lng': self.lng,
                'height_sea': self.height_sea,
                'height_ellipsoid': self.height_ellipsoid,
                'horizontal_accruacy': self.horizontal_accruacy,
                'vertiacl_accruracy': self.vertiacl_accruracy,
            }

            self.publish('gps.update', payload)

            if PI and self.lat is not None:
                payload['lon'] = payload.pop('lng')
                GPSLog.objects.create(**payload)

            await asyncio.sleep(1)
