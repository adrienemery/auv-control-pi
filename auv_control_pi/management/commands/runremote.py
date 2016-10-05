import configparser
import logging

from django.core.management.base import BaseCommand
from auv_control_pi.remote_control import RemoteInterface, ApplicationRunner

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):

    def handle(self, *args, **options):

        crossbar_config = configparser.ConfigParser()
        crossbar_config.read('config.ini')
        url = crossbar_config['crossbar']['url']
        realm = crossbar_config['crossbar']['realm']
        runner = ApplicationRunner(url=url, realm=realm)
        runner.run(RemoteInterface)
