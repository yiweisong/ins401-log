import time
import os
import struct
import re
import threading
import json
import decimal
from scapy.all import (AsyncSniffer, sendp, NetworkInterface)
try:
    from scapy.arch.libpcap import open_pcap
except:
    def open_pcap(): return None
from scapy.packet import Packet

from scapy.data import MTU
from . import message
from . import app_logger
from .ntrip_client import NTRIPClient
from .context import APP_CONTEXT
from .debug import log_app

PING_RESULT = {}
GET_PARAMETER_RESULT = {}
MODULE_REFS = {
    'GLOBAL_CANCEL': False,
    'PING_RESULT': {}
}

IMU_PKT = b'\x01\n'
GNSS_PKT = b'\x02\n'
INS_PKT = b'\x03\n'
ODO_PKT = b'\x04\n'
DIAG_PKT = b'\x05\n'
RTCM_PKT = b'\x06\n'
PING_PKT = b'\x01\xcc'
GET_PARAMETER_PKT = b'\x02\xcc'
SET_PARAMETER_PKT = b'\x03\xcc'
SAVE_CONFIG_PKT = b'\x04\xcc'

ETHERNET_OUTPUT_PACKETS = [
    IMU_PKT,  # IMU
    GNSS_PKT,  # GNSS
    INS_PKT,  # INS
    ODO_PKT,  # Odometer
    DIAG_PKT,  # Diagnose
    RTCM_PKT,  # RTCM Rover
    PING_PKT  # Ping
]

ETHERNET_OUTPUT_PACKETS_MAPPING = {
    IMU_PKT: 'IMU',
    GNSS_PKT: 'GNSS',
    INS_PKT: "INS",
    ODO_PKT: "Odometer",
    DIAG_PKT: "Diagnose",
    RTCM_PKT: "RTCM Rover",
    PING_PKT: "Ping"
}


class INS401(object):
    def __init__(self, iface,  machine_mac, device_mac, data_log_info, device_info, app_info):
        self._iface = iface
        self._machine_mac = machine_mac
        self._device_mac = device_mac
        self._ntrip_client = None
        self._device_info = device_info
        self._app_info = app_info
        self._async_sniffer = None
        self._enable_send_parsed_nmea = False
        self._received_packet_info = {}

        self._data_log_path = data_log_info['data_log_path']
        self._user_logger = app_logger.create_logger(
            os.path.join(self._data_log_path, 'user_' + data_log_info['file_time']))
        self._rtcm_rover_logger = app_logger.create_logger(
            os.path.join(self._data_log_path, 'rtcm_rover_' + data_log_info['file_time']))
        self._rtcm_base_logger = app_logger.create_logger(
            os.path.join(self._data_log_path, 'rtcm_base_' + data_log_info['file_time']))
        # self._raw_logger = app_logger.create_logger(
        #    os.path.join(self._data_log_path, 'raw_' + data_log_info['file_time']))

        self._do_init()

    @property
    def device_info(self):
        return self._device_info

    @property
    def app_info(self):
        return self._app_info

    @property
    def data_log_path(self):
        return self._data_log_path

    @property
    def enable_send_parsed_nmea(self):
        return self._enable_send_parsed_nmea

    @enable_send_parsed_nmea.setter
    def enable_send_parsed_nmea(self, value: bool):
        self._enable_send_parsed_nmea = value

    def _do_init(self):
        for key in ETHERNET_OUTPUT_PACKETS:
            if key == RTCM_PKT:
                self._received_packet_info[key] = {
                    'size': 0,
                    'count': 0
                }
            else:
                self._received_packet_info[key] = 0

    def recv(self, data):
        if self._rtcm_base_logger:
            self._rtcm_base_logger.append(bytes(data))

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
        # try parse the data
        bytes_data = bytes(data)
        # for debug
        # self._raw_logger.append(bytes_data)

        is_nmea, str_gga, with_nmea_error = try_parse_nmea(bytes_data)
        if is_nmea:
            self._append_to_app_context_packet_data('nmea')

            self._user_logger.append(bytes_data)

            if self._ntrip_client and str_gga:
                self._ntrip_client.send(str_gga)
            return

        if with_nmea_error:
            log_app.error('{0}: Fail while parse a nmea packet. Reason:{1}'.format(
                self._device_info['sn'], with_nmea_error['message']))

        is_eth_100base_t1, packet_info = try_parse_ethernet_data(
            bytes_data)
        if is_eth_100base_t1:
            self._append_to_app_context_packet_data(
                str(packet_info['packet_type']))

            byte_packet_type = packet_info['packet_type']
            if byte_packet_type == RTCM_PKT:
                self._rtcm_rover_logger.append(packet_info['payload'])

                current_rtcm_log_info = self._received_packet_info[byte_packet_type]
                self._received_packet_info[byte_packet_type] = {
                    'size': current_rtcm_log_info['size'] + packet_info['payload_len'],
                    'count': current_rtcm_log_info['count']+1
                }
            else:
                self._user_logger.append(packet_info['raw'])
                self._received_packet_info[byte_packet_type] += 1
            return

    def _append_to_app_context_packet_data(self, str_key):
        if str_key in APP_CONTEXT.packet_data.keys():
            APP_CONTEXT.packet_data[str_key] += 1
        else:
            APP_CONTEXT.packet_data[str_key] = 1

    def update_received_packet_info(self):
        file_path = os.path.join(app_logger.LogContext.session_path,
                                 self._data_log_path, 'received_packet_info.json')

        received_packet_info = {}

        for key in self._received_packet_info.keys():
            key_desc = ETHERNET_OUTPUT_PACKETS_MAPPING.get(key)
            if key_desc:
                received_packet_info[key_desc] = self._received_packet_info[key]

        with open(file_path, 'w+') as outfile:
            json.dump(received_packet_info,
                      outfile,
                      indent=4,
                      ensure_ascii=False)

    def raw_sniff(self, handler, filter):
        try:
            ins = open_pcap(self._iface, MTU, 1, 100, None)
            ins.setfilter(filter)
            while True:
                if not self.continue_sniff:
                    break
                ts, pkt = ins.next()
                if not pkt:
                    continue

                handler(pkt)
        except KeyboardInterrupt:
            pass

    def start(self):
        '''
            start log
        '''
        filter_exp = 'ether src host {0}'.format(self._device_mac)

        # async_sniffer = AsyncSniffer(
        #     count=0,
        #     store=0,
        #     iface=self._iface,
        #     prn=self.handle_receive_packet,
        #     filter=filter_exp
        # )

        # async_sniffer.start()

        # self._async_sniffer = async_sniffer

        self.thread = threading.Thread(target=self.raw_sniff, args=(
            self.handle_receive_packet, filter_exp,))
        self.thread.setDaemon(True)
        self.continue_sniff = True
        self.thread.start()

    def stop(self):
        if self.thread:
            self.continue_sniff = False
            self.thread.join()


def handle_collect_device_packet(data: Packet):
    raw_data = bytes(data)
    src = raw_data[6:12]
    device_mac = convert_bytes_to_string(src, ':')

    MODULE_REFS['PING_RESULT'][device_mac] = raw_data


def raw_sniff(iface, handler, filter):
    try:
        ins = open_pcap(iface, MTU, 1, 100, None)
        ins.setfilter(filter)
        while not MODULE_REFS['GLOBAL_CANCEL']:
            ts, pkt = ins.next()
            if not pkt:
                continue

            handler(pkt)
    except KeyboardInterrupt:
        pass


def collect_devices(network_interface: NetworkInterface, timeout=5) -> dict:
    MODULE_REFS['PING_RESULT'] = {}
    MODULE_REFS['GLOBAL_CANCEL'] = False
    iface = network_interface.name
    machine_mac = network_interface.mac
    filter_exp = 'ether dst host {0} and ether[16:2] == 0x01cc'.format(
        machine_mac)

    thread = threading.Thread(target=raw_sniff, args=(
        network_interface,
        handle_collect_device_packet,
        filter_exp,))
    thread.start()

    time.sleep(.1)
    command_line = message.build("ff:ff:ff:ff:ff:ff", machine_mac, PING_PKT)
    sendp(command_line, iface=iface, verbose=0, count=1)

    if timeout:
        time.sleep(timeout)
    MODULE_REFS['GLOBAL_CANCEL'] = True

    PING_INFO = []

    for key in MODULE_REFS['PING_RESULT']:
        PING_INFO.append({'mac': key, 'info': MODULE_REFS['PING_RESULT'][key]})

    return PING_INFO


def convert_bytes_to_string(bytes_data, link=''):
    return link.join(['%02x' % b for b in bytes_data])


def parse_device_info(str_device_info, str_app_info):
    split_text = str_device_info.split(' ')

    app_split_text = str_app_info.split(' ')

    if len(str_device_info) >= 3:
        return {
            'name': split_text[0],
            'imu': split_text[0],
            'pn': split_text[1],
            "firmware_version": app_split_text[2],
            'sn': split_text[2]
        }
    return None


def parse_app_info(str_app_info):
    split_text = str_app_info.split(' ')

    if len(split_text) >= 2:
        return {
            'app_name': split_text[0],
            'version': str_app_info,
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

            device_info = parse_device_info(device_info_text, app_info_text)
            app_info = parse_app_info(app_info_text)

            return device_info, app_info
    except:
        return None, None


def handle_receive_packet(data: Packet):
    raw_data = bytes(data)
    src = raw_data[6:12]
    device_mac = convert_bytes_to_string(src, ':')

    PING_RESULT[device_mac] = raw_data


def build_config_parameters_command_lines(device_conf, local_network: NetworkInterface):
    command_lines = []
    device_mac = device_conf['mac']
    local_machine_mac = local_network.mac

    for parameter_config in device_conf['parameters']:
        if not parameter_config.__contains__('value'):
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


def build_save_config_command(device_conf, local_network: NetworkInterface):
    command_line = None
    device_mac = device_conf['mac']
    local_machine_mac = local_network.mac

    command_line = message.build(
        dst_mac=device_mac,
        src_mac=local_machine_mac,
        pkt=SAVE_CONFIG_PKT,
        payload=[])

    return command_line


def config_parameters(device_conf, local_network: NetworkInterface):
    '''
        1. set predefined parameters (done)
        2. load current parameters (need?)
        3. compare current parameters with predefined (need?)
    '''
    if not device_conf.__contains__('parameters') or \
            not isinstance(device_conf['parameters'], list):
        return

    command_lines = build_config_parameters_command_lines(
        device_conf, local_network)
    for command_line in command_lines:
        sendp(command_line, iface=local_network.name, verbose=0)
        time.sleep(0.1)

    command_line = build_save_config_command(device_conf, local_network)
    sendp(command_line, iface=local_network.name, verbose=0)
    time.sleep(0.2)


def handle_receive_get_parameter_packet(device_conf, data: Packet):
    raw_data = bytes(data)
    # payload_len_start=18
    payload_body_start = 22
    #payload_len = struct.unpack('<I', data[payload_len_start:payload_len_start+4])[0]
    parameter_id = struct.unpack(
        '<I', raw_data[payload_body_start:payload_body_start+4])[0]
    parameter_value = struct.unpack(
        '<f', raw_data[payload_body_start+4:payload_body_start+8])[0]

    decimal_wrapped = decimal.Decimal(parameter_value)
    try:
        parameter_value = float(round(decimal_wrapped, 4))
    except:
        parameter_value = 0

    parameter_name = next(
        (item['name'] for item in device_conf['parameters'] if item['paramId'] == parameter_id), 'unknown')

    GET_PARAMETER_RESULT[parameter_id] = {
        'name': parameter_name,
        'value': parameter_value
    }


def get_parameter(parameter_id, device_conf, local_network: NetworkInterface):
    if GET_PARAMETER_RESULT.__contains__(parameter_id):
        del GET_PARAMETER_RESULT[parameter_id]

    device_mac = device_conf['mac']

    filter_exp = 'ether src host {0} and ether[16:2] == 0x02cc'.format(
        device_mac.lower())

    payload = []
    parameter_id_bytes = struct.pack('<I', parameter_id)
    payload.extend(parameter_id_bytes)

    command_line = message.build(
        dst_mac=device_mac,
        src_mac=local_network.mac,
        pkt=GET_PARAMETER_PKT,
        payload=payload)

    async_sniffer = AsyncSniffer(
        iface=local_network,
        prn=lambda data: handle_receive_get_parameter_packet(
            device_conf, data),
        filter=filter_exp
    )

    async_sniffer.start()
    time.sleep(0.1)
    sendp(command_line, iface=local_network, verbose=0)
    time.sleep(0.3)
    async_sniffer.stop()

    if GET_PARAMETER_RESULT.__contains__(parameter_id):
        return GET_PARAMETER_RESULT[parameter_id]

    return None


def get_parameters(device_conf, local_network: NetworkInterface):
    all_parameters = []

    if not device_conf.__contains__('parameters'):
        return all_parameters

    for item in device_conf['parameters']:
        parameter_result = get_parameter(
            item['paramId'], device_conf, local_network)
        if parameter_result:
            all_parameters.append(parameter_result)

    return all_parameters


def save_device_info(device_conf, local_network: NetworkInterface, data_log_info, device_info, app_info):
    ''' Save device configuration
        File name: configuration.json
    '''
    result = get_parameters(device_conf, local_network)

    device_configuration = None
    file_path = os.path.join(app_logger.LogContext.session_path,
                             data_log_info['data_log_path'], 'configuration.json')

    dir_name = os.path.dirname(file_path)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    if not os.path.exists(file_path):
        device_configuration = []
    else:
        with open(file_path) as json_data:
            device_configuration = (list)(json.load(json_data))

    # if len(result) > 0:
    session_info = dict()
    session_info['time'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime())
    session_info['device'] = device_info
    session_info['app'] = app_info
    session_info['interface'] = '100base-t1'
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


def do_create_device(device_conf, ping_info, network_interface: NetworkInterface):
    device_info, app_info = parse_ping_info(ping_info)

    print('Initializing device {0}, SN:{1}, Partnumber:{2}, Firmware:{3}, MAC Address:{4}'.format(
          device_info['name'],
          device_info['sn'],
          device_info['pn'],
          device_info['firmware_version'],
          device_conf['mac']))

    time.sleep(1)

    if device_info:
        device_mac = device_conf['mac']
        current_time = time.localtime()
        dir_time = time.strftime(
            "%Y%m%d_%H%M%S", current_time)
        file_time = time.strftime(
            "%Y_%m_%d_%H_%M_%S", current_time)
        data_log_path = '{0}_log_{1}'.format('ins401', dir_time)

        data_log_info = {
            'file_time': file_time,
            'data_log_path': data_log_path
        }

        try:
            config_parameters(device_conf, network_interface)
        except Exception as ex:
            print('Fail in config parameter. Device mac {0}, sn {1}'.format(
                device_mac, device_info['sn']))
            raise

        try:
            save_device_info(device_conf, network_interface,
                             data_log_info, device_info, app_info)
        except Exception as ex:
            print('Fail in save device info. Device mac {0}, sn {1}'.format(
                device_mac, device_info['sn']))
            raise

        iface = network_interface.name
        machine_mac = network_interface.mac

        return INS401(iface, machine_mac, device_mac, data_log_info, device_info, app_info)


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
    with_error = None

    if data[14] != 0x24:
        return is_nmea_packet, str_gga, with_error

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
                        cksum, calc_cksum = nmea_checksum(str_nmea)
                        if cksum == calc_cksum:
                            is_nmea_packet = True
                            if str_nmea.find("$GPGGA") != -1 or str_nmea.find("$GNGGA") != -1:
                                str_gga = str_nmea
                                break
                        else:
                            with_error = {'message': 'CRC Error'}
                    except Exception as e:
                        # log_app.info('NMEA exception fault')
                        with_error = {'message': 'Parse with exception'}
                        pass
                nmea_buffer = []
                nmea_sync = 0

    return is_nmea_packet, str_gga, with_error


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
            'raw_len': packet_len,
            'payload': payload,
            'payload_len': packet_len,
            'packet_type': ethernet_packet_type
        }

    return is_eth_100base_t1, packet_info


def send_ping_command(device: INS401):
    command_line = message.build(
        dst_mac=device._device_mac,  # device_mac,
        src_mac=device._machine_mac,
        pkt=PING_PKT,
        payload=[])

    sendp(command_line, iface=device._iface, verbose=0, count=1)
