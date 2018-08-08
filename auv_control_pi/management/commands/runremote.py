import logging

from django.core.management.base import BaseCommand
from auv_control_pi.remote_control import RemoteInterface
from auv_control_pi.config import config
from autobahn_autoreconnect import BackoffStrategy, ApplicationRunner

logging.basicConfig(level=logging.INFO)


class RetryForever(BackoffStrategy):
    """Retry increasingly until `max_interval` is reached

    Continue retrying forever with a delay of `max_interval`
    """

    def increase_retry_interval(self):
        """Increase retry interval until the max_interval is reached"""
        self._retry_interval = min(self._retry_interval * self._factor, self._max_interval)

    def retry(self):
        """Retry forever"""
        return True


class Command(BaseCommand):

    def handle(self, *args, **options):
        retry_strategy = RetryForever(max_interval=60)
        url = 'ws://localhost:8000/ws'
        # url = config.crossbar_url
        runner = ApplicationRunner(url=url, realm=config.crossbar_realm,
                                   retry_strategy=retry_strategy)
        runner.run(RemoteInterface)
