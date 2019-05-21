import asyncio
import logging
import shutil

import requests
from goprocam import GoProCamera
from datauri import DataURI

from ..models import Configuration
from ..wamp import ApplicationSession, rpc

logger = logging.getLogger(__name__)
config = Configuration.get_solo()


def download_image(url):
    resp = requests.get(url, stream=True)
    with open('img.jpg', 'wb') as f:
        resp.raw.decode_content = True
        shutil.copyfileobj(resp.raw, f)

    img_uri = DataURI.from_file('img.jpg')
    return img_uri


class Camera(ApplicationSession):
    """Main entry point for controling the Mothership and AUV
    """
    name = 'camera'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO check if gopro connected
        self.gopro = GoProCamera.GoPro()
        if not self.gopro._camera:
            logger.warning('Failed to connect to GoPro!')
            self.gopro = None
        else:
            logger.info('Connected to GoPro!')

    @rpc('camera.take_snapshot')
    def take_snapshot(self):
        if self.gopro:
            url = self.gopro.take_photo()
            img_uri = download_image(url)
            print(url)
        else:
            img_uri = DataURI.from_file('cat.jpg')
        return img_uri

    async def update(self):
        """Publish current state to anyone listening
        """
        while True:
            image = self.take_snapshot()

            payload = {
                'img': image,
                # 'timestamp': timezone.now().isoformat()
            }
            self.publish('camera.update', payload)

            await asyncio.sleep(0.1)
