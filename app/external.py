import struct
import can
import time
import threading
import random
from typing import List
from datetime import datetime
from scapy.all import (sendp, Packet, PacketList, resolve_iface)
from pyee import EventEmitter
from .typings import (EthOptions, CanOptions)
from . import message
from . import utils
from .can_parser import CanParserFactory


def print_message(msg, *args):
    format_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    print('{0} - {1}'.format(format_time, msg), *args)


def build_eth_commands(devices_mac, local_mac, packet_type_bytes, message_bytes):
    commands = []
    for dest_mac in devices_mac:
        command = message.build(dest_mac, local_mac,
                                packet_type_bytes,
                                message_bytes)
        commands.append(command)
    return commands


def build_speed(speed_data) -> float:
    avg_speed = (speed_data[2]+speed_data[3])/2
    return avg_speed


class Eth100BaseT1Transfer:
    def __init__(self, options: EthOptions) -> None:
        self._options = options

    def send(self, data):
        sendp(data, iface=self._options.iface, verbose=0)

    def send_batch(self, batches):
        packets_len = len(batches)
        if packets_len == 0:
            return

        packet_list = PacketList()
        for pkt in batches:
            packet_raw = Packet(pkt)
            packet_list.append(packet_raw)

        sendp(packet_list, iface=self._options.iface, verbose=0)


class WindowsCANReceiver(EventEmitter):
    def __init__(self, options: CanOptions) -> None:
        super(WindowsCANReceiver, self).__init__()

        self.can = can.interface.Bus(
            channel=options.channel, bustype='canalystii', bitrate=options.bitrate)
        # set up Notifier
        simple_listener = SimpleListener(self)
        self.notifier = can.Notifier(self.can, [simple_listener])


class SimpleListener(can.Listener):
    _receiver = None

    def __init__(self, receiver: WindowsCANReceiver) -> None:
        super().__init__()
        self._receiver = receiver

    def on_message_received(self, msg):
        self._receiver.emit('data', msg)

    def on_error(self, exc):
        print(exc)


class MockCanMessage:
    arbitration_id = 0
    data = []
    timestamp = 0


class MockReceiver(EventEmitter):
    def __init__(self):
        super(MockReceiver, self).__init__()
        threading.Thread(target=self._receive).start()

    def _receive(self):
        frequency = 20/1000
        while True:
            message = self._mock_speed_message()
            self.emit('data', message)
            time.sleep(frequency)

    def _mock_speed_message(self):
        speed_data = []
        for _ in range(8):
            speed_data.append(random.randint(1, 255))

        msg = MockCanMessage()
        msg.arbitration_id = 0xAA
        msg.timestamp = time.time()
        msg.data = speed_data
        return msg


class OdometerSource:
    _eth_100base_t1_transfer = None
    _iface: str
    _machine_mac: str

    def __init__(self, conf, devices_mac: list, can_parser_type=None):
        self._iface = resolve_iface(conf['name'])
        self._machine_mac = conf['mac']
        self._devices_mac = devices_mac
        self._can_parser = CanParserFactory.create(can_parser_type)

    def start(self):
        self._eth_100base_t1_transfer = Eth100BaseT1Transfer(
            EthOptions(self._iface, self._machine_mac, self._devices_mac))

        try:
            print_message('[Info] CAN log task started')
            # MockReceiver()
            can_log_receiver = WindowsCANReceiver(CanOptions(0, 500000))
            can_log_receiver.on('data', self.receiver_handler)
        except Exception as ex:
            print_message('[Error] CAN log task has error')
            print_message('[Error] Reason:{0}'.format(ex))

    @utils.throttle(seconds=0.05)
    def handle_wheel_speed_data(self, data):
        # parse wheel speed
        parse_error, parse_result = self._can_parser.parse('WHEEL_SPEED', data.data)
        if parse_error:
            return

        speed = build_speed(parse_result)

        # append_to_speed_queue(speed)
        commands = build_eth_commands(self._devices_mac, self._machine_mac,
                                      bytes([0x01, 0x0b]),
                                      list(struct.pack("<f", speed)))

        if self._eth_100base_t1_transfer:
            self._eth_100base_t1_transfer.send_batch(commands)

        # log timestamp
        # can_speed_log.append('{0}, {1}'.format(data.timestamp, speed))

    def receiver_handler(self, data):
        if self._can_parser.need_handle_speed_data(data.arbitration_id):
            self.handle_wheel_speed_data(data)
