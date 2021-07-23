import time

from . import app_logger
from .ntrip_client import NTRIPClient
from .device import (create_device, INS401)


class Bootstrap(object):
    _devices: list[INS401]
    _rtcm_logger = None

    def __init__(self):
        self._devices = []

        # prepare logger
        app_logger.new_session()
        
        self._rtcm_logger = app_logger.create_logger('rtcm_rover')

    def _load_conf(self):
        return {}

    def _ping_devices(self):
        conf = self._load_conf()
        for item in conf["devices"]:
            device = create_device(item, conf["local"])
            if device:
                self._devices.append(device)

        for device in self._devices:
            device.start()

    def _handle_parse_ntrip_data(self, data):
        # log to rtcm_rover.log
        if self._rtcm_logger:
            self._rtcm_logger.append(data)

        # send data to device list
        for device in self._devices:
            device.recv(data)

    def start(self):
        ''' prepare
            1. ping device from configuration
            2. collect the ping result, start log client
            3. start ntrip client
        '''
        self._ping_devices()
        self._ntrip_client = NTRIPClient()
        self._ntrip_client.on('parsed', self._handle_parse_ntrip_data)
        self._ntrip_client.start()

        print('Application started')

        while True:
            time.sleep(10)
