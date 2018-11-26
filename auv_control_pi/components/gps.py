import os
import asyncio
import logging

from navio.gps import GPS
from ..models import GPSLog
from ..wamp import ApplicationSession, rpc

logger = logging.getLogger(__name__)
PI = os.getenv('PI', False)
SIMULATION = os.getenv('SIMULATION', False)


class GPSComponent(ApplicationSession):
    name = 'gps'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize the gps
        if PI and not SIMULATION:
            self.lat = None
            self.lng = None
            self.gps = GPS()
        elif SIMULATION:
            self.gps = None
            # Jericho Beach
            self.lat = 49.273008
            self.lng = -123.179694

        self.status = None
        self.height_ellipsoid = None
        self.height_sea = None
        self.horizontal_accruacy = None
        self.vertiacl_accruracy = None

    def onConnect(self):
        self.join(realm=self.config.realm)

    @rpc('gps.get_position')
    def get_position(self):
        return self.lat, self.lng

    @rpc('gps.get_status')
    def get_status(self):
        return self.status

    def _parse_msg(self, msg):
        """
        Update all local instance variables
        """
        if msg.name() == "NAV_POSLLH":
            self.lat = msg.Latitude / 10e6
            self.lng = msg.Longitude / 10e6
            self.height_ellipsoid = msg.height
            self.height_sea = msg.hMSL
            self.horizontal_accruacy = msg.hAcc
            self.vertiacl_accruracy = msg.vAcc

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
                # GPSLog.objects.create(**payload)

            await asyncio.sleep(0.1)
