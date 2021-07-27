import time
import os
import struct
import re
from scapy.all import (AsyncSniffer, sendp)
from scapy.packet import Packet
from . import message
from . import app_logger
from .ntrip_client import NTRIPClient

PING_RESULT = {}

PING_PKT = b'\x01\xcc'

ETHERNET_OUTPUT_PACKETS = [b'\x01\n', b'\x02\n',
                           b'\x03\n', b'\x04\n', b'\x05\n', b'\x06\n']


def convert_bytes_to_string(bytes_data, link=''):
    return link.join(['%02x' % b for b in bytes_data])


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
            split_text = info_text[0].split(' ')

            if len(split_text) >= 3:
                return {
                    'name': split_text[0],
                    'pn': split_text[1],
                    'sn': split_text[2]
                }

            return None
    except:
        return None


def handle_receive_packet(data: Packet):
    raw_data = bytes(data)
    src = raw_data[6:12]
    device_mac = convert_bytes_to_string(src, ':')

    PING_RESULT[device_mac] = raw_data


def create_device(device_mac, local_network):
    # filter_exp = 'ether src host {0} and ether[16:2] == 0x01cc'.format(
    #     device_mac)
    filter_exp = 'ether dst host {0} and ether[16:2] == 0x01cc'.format(
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
    time.sleep(1)
    async_sniffer.stop()

    if not PING_RESULT.__contains__(device_mac):
        return None

    info = parse_ping_info(PING_RESULT[device_mac])

    if info:
        iface = local_network["name"]
        machine_mac = local_network["mac"]
        return INS401(iface, machine_mac, device_mac, info.sn)

    return None


def nmea_checksum(self, data):
    data = data.replace("\r", "").replace("\n", "").replace("$", "")
    nmeadata, cksum = re.split('\*', data)
    calc_cksum = 0
    for s in nmeadata:
        calc_cksum ^= ord(s)
    return int(cksum, 16), calc_cksum


def try_parse_nmea(data):
    nmea_buffer = []
    nmea_sync = 0
    is_nmea_packet = False
    str_nmea = ''

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
                            if str_nmea.find("$GPGGA") != -1:
                                is_nmea_packet = True
                                break
                    except Exception as e:
                        # print('NMEA fault:{0}'.format(e))
                        pass
                nmea_buffer = []
                nmea_sync = 0

    return is_nmea_packet, str_nmea


def try_parse_ethernet_data(data):
    is_eth_100base_t1 = False
    ethernet_packet_type = data[16:18]

    if ETHERNET_OUTPUT_PACKETS.__contains__(ethernet_packet_type):
        is_eth_100base_t1 = True

    return is_eth_100base_t1, ethernet_packet_type


class INS401(object):
    def __init__(self, iface,  machine_mac, device_mac, sn):
        self._iface = iface
        self._machine_mac = machine_mac
        self._device_mac = device_mac
        self._user_logger = app_logger.create_logger(os.path.join(sn, 'user'))
        self._rtcm_rover_logger = app_logger.create_logger(
            os.path.join(sn, 'rtcm_rover'))

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
        is_nmea, str_nmea = try_parse_nmea(bytes_data)
        if is_nmea:
            if self._ntrip_client:
                self._ntrip_client.send(str_nmea)
                self._user_logger.append(bytes_data)
            return

        is_eth_100base_t1, ethernet_packet_type = try_parse_ethernet_data(
            bytes_data)
        if is_eth_100base_t1:
            if ethernet_packet_type == b'\x06\n':
                self._rtcm_rover_logger.append(bytes_data)
            else:
                self._user_logger.append(bytes_data)
            return

    def start(self):
        '''
            start log
        '''
        filter_exp = 'ether src host {0}'.format(self._mac)

        async_sniffer = AsyncSniffer(
            iface=self._iface,
            prn=self.handle_receive_packet,
            filter=filter_exp
        )

        async_sniffer.start()