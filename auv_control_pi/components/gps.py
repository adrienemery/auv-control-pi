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
        self.gps = GPS()
        self.lat = None
        self.lon = None
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

        # create subtasks
        loop = asyncio.get_event_loop()
        loop.create_task(self.update())

    def _update(self, msg):
        """
        Update all local instance variables
        """
        if msg:
            self.lat = msg.lat
            self.lon = msg.lon
            self.height_ellipsoid = msg.heightEll
            self.height_sea = msg.heightSea
            self.horizontal_accruacy = msg.horAcc
            self.vertiacl_accruracy = msg.verAcc

    async def update(self):
        if PI:
            self.gps.update()

            # TODO parse gps msg

            payload = {
                'lat': self.lat,
                'lon': self.lon,
                'height_sea': self.height_sea,
                'height_ellipsoid': self.height_ellipsoid,
                'horizontal_accruacy': self.horizontal_accruacy,
                'vertiacl_accruracy': self.vertiacl_accruracy,
            }
            self.publish('gps.update', payload)
            GPSLog.objects.create(**payload)
        await asyncio.sleep(1)
