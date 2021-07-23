import time
import os
import struct
from scapy.all import (AsyncSniffer, sendp)
from scapy.packet import Packet
from . import message
from . import app_logger

PING_RESULT = {}

PING_PKT = b'\x01\xcc'


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
    filter_exp = 'ether src host {0} and ether[16:2] == 0x01cc'.format(
        device_mac)

    command_line = message.build(
        dst_mac=device_mac,
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


class INS401(object):
    def __init__(self, iface,  machine_mac, device_mac, sn):
        self._iface = iface
        self._machine_mac = machine_mac
        self._device_mac = device_mac
        self._user_logger = app_logger.create_logger(os.path.join(sn, 'user'))

    def recv(self, data):
        # send rtcm to device
        wrapped_packet_data = message.build(
            dst_mac=self._device_mac,
            src_mac=self._machine_mac,
            pkt=b'\x02\x0b',
            payload=data)

        sendp(wrapped_packet_data, iface=self._iface, verbose=0)

    def handle_receive_packet(self, data):
        self._user_logger.append(bytes(data))

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
