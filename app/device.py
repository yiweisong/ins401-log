import time
import os
import struct
import re
import threading
import json
from scapy.all import (AsyncSniffer, sendp)
from scapy.packet import Packet
from . import message
from . import app_logger
from .ntrip_client import NTRIPClient
from .context import APP_CONTEXT

PING_RESULT = {}

GET_PARAMETER_RESULT = {}

PING_PKT = b'\x01\xcc'

GET_PARAMETER_PKT = b'\x02\xcc'

SET_PARAMETER_PKT = b'\x03\xcc'

SAVE_CONFIG_PKT = b'\x04\xcc'

ETHERNET_OUTPUT_PACKETS = [b'\x01\n', b'\x02\n',
                           b'\x03\n', b'\x04\n', b'\x05\n', b'\x06\n']


def convert_bytes_to_string(bytes_data, link=''):
    return link.join(['%02x' % b for b in bytes_data])


def parse_device_info(str_device_info):
    split_text = str_device_info.split(' ')

    if len(str_device_info) >= 3:
        return {
            'name': split_text[0],
            'pn': split_text[1],
            'sn': split_text[2]
        }
    return None


def parse_app_info(str_app_info):
    split_text = str_app_info.split(' ')

    if len(split_text) >= 5:
        return {
            'app_name': split_text[0],
            'app_version': split_text[1] + split_text[2],
            'bootloader_version': split_text[3] + split_text[4],
        }

    return None


def parse_ping_info(bytes_data: bytes):
    data_buffer = None

    if bytes_data:
        packet_raw = bytes_data[14:]
        packet_type = packet_raw[2:4]
        if packet_type == PING_PKT:
            packet_length = struct.unpack('<I', packet_raw[4:8])[0]
            data_buffer = packet_raw[8: 8 + packet_length]

    try:
        str_data = data_buffer.decode()
        info_text = str_data.split(' RTK_INS')
        if len(info_text) > 0:
            device_info_text = info_text[0]
            app_info_text = 'RTK_INS' + info_text[1]

            device_info = parse_device_info(device_info_text)
            app_info = parse_app_info(app_info_text)

            return device_info, app_info
    except:
        return None, None


def handle_receive_packet(data: Packet):
    raw_data = bytes(data)
    src = raw_data[6:12]
    device_mac = convert_bytes_to_string(src, ':')

    PING_RESULT[device_mac] = raw_data


def build_config_parameters_command_lines(device_conf, local_network):
    command_lines = []
    device_mac = device_conf['mac']
    local_machine_mac = local_network['mac']
    local_machine_iface = local_network["name"]
    for parameter_config in device_conf['parameters']:
        if not parameter_config.get('value'):
            continue

        payload = []
        parameter_id = struct.pack('<I', parameter_config['paramId'])
        parameter_value = struct.pack('<f', parameter_config['value'])
        payload.extend(parameter_id)
        payload.extend(parameter_value)

        command_line = message.build(
            dst_mac=device_mac,
            src_mac=local_machine_mac,
            pkt=SET_PARAMETER_PKT,
            payload=payload)
        command_lines.append(command_line)

    return command_lines


def build_save_config_command(device_conf, local_network):
    command_line = None
    device_mac = device_conf['mac']
    local_machine_mac = local_network['mac']

    command_line = message.build(
        dst_mac=device_mac,
        src_mac=local_machine_mac,
        pkt=SAVE_CONFIG_PKT,
        payload=[])

    return command_line


def config_parameters(device_conf, local_network):
    '''
        1. set predefined parameters (done)
        2. load current parameters (need?)
        3. compare current parameters with predefined (need?)
    '''
    if not device_conf.__contains__('parameters') and \
            not isinstance(device_conf['parameters'], list):
        return

    command_lines = build_config_parameters_command_lines(
        device_conf, local_network)
    for command_line in command_lines:
        sendp(command_line, iface=local_network["name"], verbose=0)
        time.sleep(0.2)

    command_line = build_save_config_command(device_conf, local_network)
    sendp(command_line, iface=local_network["name"], verbose=0)
    time.sleep(0.2)


def handle_receive_get_parameter_packet(device_conf, data: Packet):
    raw_data = bytes(data)
    # payload_len_start=18
    payload_body_start = 22
    #payload_len = struct.unpack('<I', data[payload_len_start:payload_len_start+4])[0]

    parameter_id = struct.unpack(
        '<I', data[payload_body_start:payload_body_start+4])[0]
    parameter_value = struct.unpack(
        '<f', data[payload_body_start+4:payload_body_start+12])[0]

    parameter_name = next(
        (item['name'] for item in device_conf['parameters'] if item['paramId'] == parameter_id), 'unknown')

    GET_PARAMETER_RESULT[parameter_id] = {
        'name': parameter_name,
        'value': parameter_value
    }


def get_parameter(parameter_id, device_conf, local_network):
    device_mac = device_conf['mac']

    filter_exp = 'ether src host {0} and ether[16:2] == 0x02cc'.format(
        device_mac)

    payload = []
    parameter_id_bytes = struct.pack('<I', parameter_id)
    payload.extend(parameter_id_bytes)

    command_line = message.build(
        dst_mac=device_mac,
        src_mac=local_network['mac'],
        pkt=GET_PARAMETER_PKT,
        payload=payload)

    async_sniffer = AsyncSniffer(
        iface=local_network["name"],
        prn=lambda data: handle_receive_get_parameter_packet(
            device_conf, data),
        filter=filter_exp
    )

    async_sniffer.start()
    sendp(command_line, iface=local_network["name"], verbose=0)
    time.sleep(0.2)
    async_sniffer.stop()

    return GET_PARAMETER_RESULT[parameter_id]


def get_parameters(device_conf, local_network):
    GET_PARAMETER_RESULT = {}

    all_parameters = []
    for item in device_conf['parameters']:
        parameter_result = get_parameter(
            item['paramId'], device_conf, local_network)
        all_parameters.append(parameter_result)

    return all_parameters


def save_device_info(device_conf, local_network, data_log_info, device_info, app_info):
    ''' Save device configuration
        File name: configuration.json
    '''
    result = get_parameters(device_conf, local_network)

    device_configuration = None
    file_path = os.path.join(
        data_log_info['data_log_path'], 'configuration.json')

    if not os.path.exists(file_path):
        device_configuration = []
    else:
        with open(file_path) as json_data:
            device_configuration = (list)(json.load(json_data))

    if len(result) > 0:
        session_info = dict()
        session_info['time'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.localtime())
        session_info['device'] = device_info
        session_info['app'] = app_info
        session_info['interface'] = '100bast-t1'
        parameters_configuration = dict()
        for item in result:
            param_name = item['name']
            param_value = item['value']
            parameters_configuration[param_name] = param_value

        session_info['parameters'] = parameters_configuration
        device_configuration.append(session_info)

        with open(file_path, 'w') as outfile:
            json.dump(device_configuration,
                      outfile,
                      indent=4,
                      ensure_ascii=False)


def create_device(device_conf, local_network):
    # filter_exp = 'ether src host {0} and ether[16:2] == 0x01cc'.format(
    #     device_mac)
    device_mac = device_conf['mac']
    filter_exp = 'ether src host {0} and ether[16:2] == 0x01cc'.format(
        device_mac)

    command_line = message.build(
        dst_mac="ff:ff:ff:ff:ff:ff",  # device_mac,
        src_mac=local_network['mac'],
        pkt=PING_PKT,
        payload=[])

    async_sniffer = AsyncSniffer(
        iface=local_network["name"],
        prn=handle_receive_packet,
        filter=filter_exp
    )

    async_sniffer.start()
    sendp(command_line, iface=local_network["name"], verbose=0)
    time.sleep(2)
    async_sniffer.stop()

    if not PING_RESULT.__contains__(device_mac):
        return None

    device_info, app_info = parse_ping_info(PING_RESULT[device_mac])
    print(device_info)

    if device_info:
        file_time = time.strftime(
            "%Y_%m_%d_%H_%M_%S", time.localtime())
        data_log_path = '{0}_log_{1}'.format('ins401', file_time)

        data_log_info = {
            'file_time': file_time,
            'data_log_path': data_log_path
        }

        try:
            config_parameters(device_conf, local_network)
        except:
            print('Fail in config parameter. Device mac {0}, sn {1}'.format(
                device_mac, device_info['sn']))

        try:
            save_device_info(device_conf, local_network,
                             data_log_info, device_info, app_info)
        except:
            print('Fail in save device info. Device mac {0}, sn {1}'.format(
                device_mac, device_info['sn']))

        iface = local_network["name"]
        machine_mac = local_network["mac"]

        return INS401(iface, machine_mac, device_mac, data_log_info, device_info, app_info)

    return None


def nmea_checksum(data):
    if data is not None:
        data = data.replace("\r", "").replace("\n", "").replace("$", "")
        nmeadata, cksum = re.split('\*', data)
        calc_cksum = 0
        for s in nmeadata:
            calc_cksum ^= ord(s)
        return int(cksum, 16), calc_cksum
    else:
        return None


def try_parse_nmea(data):
    nmea_buffer = []
    nmea_sync = 0
    is_nmea_packet = False
    str_nmea = None
    str_gga = None

    for bytedata in data:
        if bytedata == 0x24:
            nmea_buffer = []
            nmea_sync = 0
            nmea_buffer.append(chr(bytedata))
        else:
            nmea_buffer.append(chr(bytedata))
            if nmea_sync == 0:
                if bytedata == 0x0D:
                    nmea_sync = 1
            elif nmea_sync == 1:
                if bytedata == 0x0A:
                    try:
                        str_nmea = ''.join(nmea_buffer)
                        cksum, calc_cksum = nmea_checksum(
                            str_nmea)
                        if cksum == calc_cksum:
                            is_nmea_packet = True
                            if str_nmea.find("$GPGGA") != -1:
                                str_gga = str_nmea
                                break
                    except Exception as e:
                        #print('NMEA fault:{0}'.format(e))
                        pass
                nmea_buffer = []
                nmea_sync = 0

    return is_nmea_packet, str_gga


def try_parse_ethernet_data(data):
    is_eth_100base_t1 = False
    ethernet_packet_type = data[16:18]
    packet_info = None

    if ETHERNET_OUTPUT_PACKETS.__contains__(ethernet_packet_type):
        is_eth_100base_t1 = True
        packet_len = struct.unpack('<H', data[12:14])[0]
        raw = data[14:14+packet_len]
        payload_len = struct.unpack('<I', data[18:22])[0]
        payload = data[22:22+payload_len]
        packet_info = {
            'raw': raw,
            'payload': payload,
            'packet_type': ethernet_packet_type
        }

    return is_eth_100base_t1, packet_info


class INS401(object):
    def __init__(self, iface,  machine_mac, device_mac, data_log_info, device_info, app_info):
        self._iface = iface
        self._machine_mac = machine_mac
        self._device_mac = device_mac
        self._ntrip_client = None
        self._device_info = device_info
        self._app_info = app_info

        self._data_log_path = data_log_info['data_log_path']
        self._user_logger = app_logger.create_logger(
            os.path.join(self._data_log_path, 'user_' + data_log_info['file_time']))
        self._rtcm_rover_logger = app_logger.create_logger(
            os.path.join(self._data_log_path, 'rtcm_rover_' + data_log_info['file_time']))

    @property
    def device_info(self):
        return self._device_info

    @property
    def app_info(self):
        return self._app_info

    @property
    def data_log_path(self):
        return self._data_log_path

    def recv(self, data):
        # send rtcm to device
        wrapped_packet_data = message.build(
            dst_mac=self._device_mac,
            src_mac=self._machine_mac,
            pkt=b'\x02\x0b',
            payload=data)

        sendp(wrapped_packet_data, iface=self._iface, verbose=0)

    def set_ntrip_client(self, ntrip_client: NTRIPClient):
        self._ntrip_client = ntrip_client

    def handle_receive_packet(self, data):
        # parse the data
        bytes_data = bytes(data)

        is_nmea, str_gga = try_parse_nmea(bytes_data)
        if is_nmea:
            self._append_to_app_context_packet_data('nmea')

            self._user_logger.append(bytes_data)
            self._user_logger.flush()

            if self._ntrip_client and str_gga:
                self._ntrip_client.send(str_gga)
            return

        is_eth_100base_t1, packet_info = try_parse_ethernet_data(
            bytes_data)
        if is_eth_100base_t1:
            self._append_to_app_context_packet_data(
                str(packet_info['packet_type']))

            if packet_info['packet_type'] == b'\x06\n':
                self._rtcm_rover_logger.append(packet_info['payload'])
                self._rtcm_rover_logger.flush()
            else:
                self._user_logger.append(packet_info['raw'])
                self._user_logger.flush()
            return

    def _append_to_app_context_packet_data(self, str_key):

        if str_key in APP_CONTEXT.packet_data.keys():
            APP_CONTEXT.packet_data[str_key] += 1
        else:
            APP_CONTEXT.packet_data[str_key] = 0

    def start(self):
        '''
            start log
        '''
        filter_exp = 'ether src host {0}'.format(self._device_mac)

        async_sniffer = AsyncSniffer(
            count=0,
            store=0,
            iface=self._iface,
            prn=self.handle_receive_packet,
            filter=filter_exp
        )

        async_sniffer.start()
