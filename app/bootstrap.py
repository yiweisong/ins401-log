import time
import json
import os
import threading
from . import app_logger
from .ntrip_client import NTRIPClient
from .device import (create_device, INS401)
from .debug import track_log_status
from .context import APP_CONTEXT
from .utils import list_files 

def format_app_context_packet_data():
    return ', '.join(['{}: {}'.format(key,APP_CONTEXT.packet_data[key]) for key in APP_CONTEXT.packet_data])

class Bootstrap(object):
    _devices = None
    _rtcm_logger = None
    _conf = None

    def __init__(self):
        self._devices = []

        # prepare logger
        app_logger.new_session()

        file_time = time.strftime(
            "%Y_%m_%d_%H_%M_%S", time.localtime())
        self._rtcm_logger = app_logger.create_logger('rtcm_base_' + file_time)

    def _load_conf(self):
        app_conf = {}
        with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
            app_conf = (json.load(json_data))

        # load device config
        device_config_paths = list_files(os.path.join(os.getcwd(),'configs','devices'))

        for path in device_config_paths:
            with open(path) as json_data:
                device_conf = json.load(json_data)
                if not device_conf.__contains__('mac'):
                    continue

                if not app_conf.__contains__('devices'):
                    app_conf['devices'] = []
                
                app_conf['devices'].append(device_conf)

        return app_conf

    def _ping_devices(self):
        self._conf = self._load_conf()

        for item in self._conf["devices"]:
            device = create_device(item, self._conf["local"])
            if device:
                self._devices.append(device)

        if len(self._devices)==0:
            print('No device detected')
            return

        for device in self._devices:
            device.start()

    def _handle_parse_ntrip_data(self, data):
        # log to rtcm_rover.log
        if self._rtcm_logger:
            self._rtcm_logger.append(bytes(data))

        # send data to device list
        for device in self._devices:
            device.recv(data)

    def start_debug_track(self):
        # track the log status per second
        while True:
            try:
                str_log_info = format_app_context_packet_data()
                track_log_status(str_log_info)
                time.sleep(1)
            except Exception as ex:
                track_log_status(ex)

                return

    def start(self):
        ''' prepare
            1. ping device from configuration
            2. collect the ping result, start log client
            3. start ntrip client
        '''
        self._ping_devices()
        self._ntrip_client = NTRIPClient(self._conf['ntrip'])
        self._ntrip_client.on('parsed', self._handle_parse_ntrip_data)

        for device in self._devices:
            device.set_ntrip_client(self._ntrip_client)

        # thread to start ntrip client
        threading.Thread(target=lambda: self._ntrip_client.run()).start()
        # thread to start debug track
        threading.Thread(target=lambda: self.start_debug_track()).start()


        print('Application started')

        while True:
            time.sleep(10)
