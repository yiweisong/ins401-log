import time
import json
import os
import threading
from typing import List
from multiprocessing import Process
from scapy.interfaces import NetworkInterface
from . import app_logger
from .debug import (track_log_status, log_app)
from .ntrip_client import NTRIPClient
from .device import (do_create_device,
                     send_ping_command, INS401)
from .context import APP_CONTEXT
from .utils import (list_files, extend_default)
from .decorator import handle_application_exception
from .external import OdometerSource


def format_app_context_packet_data():
    return ', '.join(['{0}: {1}'.format(key, APP_CONTEXT.packet_data[key]) for key in APP_CONTEXT.packet_data])


def gen_odometer_process(conf, devices_mac: list, can_parser_type, logger_ctx):
    app_logger.LogContext.update(logger_ctx)
    odo_source = OdometerSource(conf, devices_mac, can_parser_type)
    odo_source.start()


class Bootstrap(object):
    _devices: List[INS401] = []
    _conf = {}

    def __init__(self):
        self._devices = []

        # prepare logger
        app_logger.new_session()

        file_time = time.strftime(
            "%Y_%m_%d_%H_%M_%S", time.localtime())

    def _load_conf(self):
        app_conf = {}
        with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
            app_conf = (json.load(json_data))

        extend_default(app_conf, {
            'devices': [],
            'ntrip': None,
            'can_parser': 'DefaultParser',
            'use_odo_transfer': False,
            'ignore_ntrip': []
        })

        # load device config
        device_config_paths = list_files(
            os.path.join(os.getcwd(), 'configs', 'devices'))

        for path in device_config_paths:
            with open(path) as json_data:
                device_conf = json.load(json_data)
                if not device_conf.__contains__('mac'):
                    continue

                if not app_conf.__contains__('devices'):
                    app_conf['devices'] = []

                app_conf['devices'].append(device_conf)

        return app_conf

    def _create_devices(self, network_interface: NetworkInterface, devices: list):
        self._conf = self._load_conf()
        self._devices = []
        for device in devices:
            DEFAULT_ITEM = {'mac': device['mac']}
            device_conf = next(
                (item for item in self._conf['devices'] if item['mac'] == device['mac']), DEFAULT_ITEM)

            device = do_create_device(
                device_conf, device['info'], network_interface)
            if device:
                self._devices.append({
                    'device': device,
                    'conf': device_conf
                })

        if len(self._devices) == 0:
            print('No device detected')
            return

        for item in self._devices:
            item['device'].start()

    def _handle_parse_ntrip_data(self, device):
        return lambda data: device.recv(data)

    def _start_ntrip_client(self):
        if len(self._devices) == 0:
            return

        for item in self._devices:
            device_conf = item['conf']
            device = item['device']

            if self._conf['ignore_ntrip'].__contains__(int(device.device_info['sn'])):
                print('NTRIP:[ingore sn]', device.device_info['sn'])
                continue

            ntrip_conf = device_conf['ntrip'] if device_conf.__contains__(
                'ntrip') else self._conf['ntrip']

            if not ntrip_conf:
                continue

            ntrip_client = NTRIPClient(ntrip_conf)
            ntrip_client.on('parsed', self._handle_parse_ntrip_data(device))
            sn = device.device_info['sn']
            pn = device.device_info['pn']
            ntrip_client.set_connect_headers({
                'Ntrip-Sn': sn,
                'Ntrip-Pn': pn
            })

            device.set_ntrip_client(ntrip_client)

            threading.Thread(target=lambda: ntrip_client.run()).start()

    def _start_debug_track(self):
        # track the log status per second
        check_count = 0
        while True:
            time.sleep(1)
            check_count += 1
            try:
                str_log_info = self.format_log_info()
                track_log_status(str_log_info)

                # Send ping command to device per 60s to check if device is alive
                if check_count == 60:
                    for item in self._devices:
                        send_ping_command(item['device'])
                    check_count = 0
            except Exception as ex:
                log_app.error(ex)

    def format_log_info(self):
        for item in self._devices:
            item['device'].update_received_packet_info()

        return ', '.join(['{0}: {1}'.format(key, APP_CONTEXT.packet_data[key]) for key in APP_CONTEXT.packet_data])

    @handle_application_exception
    def start(self):
        ''' prepare
            1. ping device from configuration
            2. collect the ping result, start log client
            3. start ntrip client
        '''
        # self._ping_devices()

        self._start_ntrip_client()

        # thread to start debug track
        threading.Thread(target=lambda: self._start_debug_track()).start()

        devices_mac = [item._device_mac for item in self._devices]
        odometer_process = Process(
            target=gen_odometer_process,
            args=(self._conf['local'], devices_mac, ))
        odometer_process.start()

        print('Application started')

        while True:
            time.sleep(10)

    @handle_application_exception
    def start_v2(self, network_interface: NetworkInterface, devices: list):
        self._create_devices(network_interface, devices)
        self._start_ntrip_client()
        threading.Thread(target=lambda: self._start_debug_track()).start()

        use_odo_transfer = self._conf['use_odo_transfer']
        if use_odo_transfer:
            devices_mac = [
                item['device']._device_mac for item in self._devices]

            odometer_process = Process(
                target=gen_odometer_process,
                args=(self._conf['local'], devices_mac, self._conf['can_parser'], app_logger.LogContext.to_dict()))
            odometer_process.start()

        print('Application started')

        while True:
            time.sleep(10)
