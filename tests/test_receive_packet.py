import random
import sys
import os
import time
import json
from scapy.all import (sendp, resolve_iface, Packet, PacketList)
try:
    from app.device import INS401
    from app import (message, app_logger)
    from tools.mac_to_sn import convert_mac_to_sn
    from app.device import (
        IMU_PKT, GNSS_PKT, INS_PKT, ODO_PKT, DIAG_PKT, RTCM_PKT
    )
except:
    sys.path.append(os.getcwd())
    from app.device import INS401
    from app import (message, app_logger)
    from tools.mac_to_sn import convert_mac_to_sn
    from app.device import (
        IMU_PKT, GNSS_PKT, INS_PKT, ODO_PKT, DIAG_PKT, RTCM_PKT
    )

app_conf = {}
with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
    app_conf = (json.load(json_data))

LOCAL_IFACE = app_conf['local']['name']

LOCAL_MAC_ADDRESS = app_conf['local']['mac']

RESOLVED_LOCAL_IFACE = resolve_iface(LOCAL_IFACE)


def create_device(name, device_mac_address):
    current_time = time.localtime()
    dir_time = time.strftime(
        "%Y%m%d_%H%M%S", current_time)
    file_time = time.strftime(
        "%Y_%m_%d_%H_%M_%S", current_time)
    data_log_path = '{0}_log_{1}'.format(name, dir_time)

    data_log_info = {
        'file_time': file_time,
        'data_log_path': data_log_path
    }

    device_info = {
        'name': name,
        'imu': 'device imu',
        'pn': 'part number',
        "firmware_version": '1.0.0',
        'sn': '123456'
    }

    app_info = {
        'app_name': 'app',
        'version': '1.0.0',
    }

    return INS401(RESOLVED_LOCAL_IFACE, LOCAL_MAC_ADDRESS, device_mac_address, data_log_info, device_info, app_info)


def gen_mock_mac_address():
    cell_len = 6
    cell_array = []
    for i in range(cell_len):
        cell_array.append('{:02X}'.format(random.randint(1, 255)))
    return ':'.join(cell_array)


def gen_mock_mac_addresses(count):
    addresses = []
    for _ in range(count):
        addresses.append(gen_mock_mac_address())
    return addresses


def create_mock_devices(name_prefix, device_mac_address):
    devices = []
    for mac_address in device_mac_address:
        sn = convert_mac_to_sn(mac_address)
        print('{0}:{1}', sn, mac_address)
        devices.append(
            create_device(
                '{0}-{1}'.format(name_prefix, sn),
                mac_address
            )
        )
    return devices


def gen_mock_packet():
    count = 1
    frequency_policy = {
        IMU_PKT: 1,
        GNSS_PKT: 100,
        INS_PKT: 1,
        ODO_PKT: 10,
        DIAG_PKT: 100,
        RTCM_PKT: 1,
        'nmea': 100
    }

    mock_nmea = '$GPGGA,051612.00,3129.6798000,N,12021.8016833,E,1,33,0.0,-15.409,M,6.809,M,0.0,*6E\r\n$GPZDA,051612.00,15,09,2021,00,00,*47'

    while True:
        output_packet = {}
        for key in frequency_policy:
            if count % frequency_policy[key] == 0:
                if key != 'nmea':
                    output_packet[key] = bytes(200)
                else:
                    output_packet[key] = mock_nmea.encode()

        count += 1

        yield output_packet


def send_packet_to_devices(device_mac_addresses, packet):
    packet_list = PacketList()
    for mac_address in device_mac_addresses:
        for packet_type in packet:
            actual_packet_type = packet_type

            if packet_type == 'nmea':
                actual_packet_type = None

            command_line = message.build(
                dst_mac=LOCAL_MAC_ADDRESS,
                src_mac=mac_address,
                pkt=actual_packet_type,
                payload=packet[packet_type])
            packet_raw = Packet(command_line)
            packet_list.append(packet_raw)

    #sendp(packet_list, iface=RESOLVED_LOCAL_IFACE, verbose=0)
    return packet_list


if __name__ == '__main__':
    app_logger.new_session()

    # 1. create shared parameters
    output_packet_count = 0
    mock_len = 10
    duration = 1  # minute as unit
    mock_mac_addresses = gen_mock_mac_addresses(mock_len)

    # 2. create devices as receiver
    devices = create_mock_devices('mock-prefix', mock_mac_addresses)
    for device in devices:
        device.start()

    # 3. create data mocker as sender
    start_time = time.time()
    now_time = start_time

    mock_packet_generator = gen_mock_packet()
    print('Start time:{0}'.format(start_time))
    while now_time-start_time < duration*10:
        packet = next(mock_packet_generator)
        # send same packet
        ethernet_packet_list = send_packet_to_devices(
            mock_mac_addresses, packet)
        output_packet_count += len(ethernet_packet_list)
        now_time = time.time()
        time.sleep(0.001)
    print('End time:{0}'.format(now_time))
    print('Output packet count:{0}'.format(output_packet_count))
