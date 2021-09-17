import random
import sys
import os
import time
import json
from scapy.all import (sendp, resolve_iface, Packet, PacketList)
from multiprocessing import Process
from multiprocessing.sharedctypes import (Value, Array)
from ctypes import c_char_p, create_string_buffer

try:
    from app.device import INS401
    from app import (message, app_logger)
    from tools.mac_to_sn import convert_mac_to_sn
    from app.device import (
        IMU_PKT, GNSS_PKT, INS_PKT, ODO_PKT, DIAG_PKT, RTCM_PKT
    )
    from app.context import APP_CONTEXT
except:
    sys.path.append(os.getcwd())
    from app.device import INS401
    from app import (message, app_logger)
    from tools.mac_to_sn import convert_mac_to_sn
    from app.device import (
        IMU_PKT, GNSS_PKT, INS_PKT, ODO_PKT, DIAG_PKT, RTCM_PKT
    )
    from app.context import APP_CONTEXT

app_conf = {}
with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
    app_conf = (json.load(json_data))

LOCAL_IFACE = app_conf['local']['name']

LOCAL_MAC_ADDRESS = app_conf['local']['mac']

RESOLVED_LOCAL_IFACE = resolve_iface(LOCAL_IFACE)


def create_device(name, device_mac_address, sn):
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
        'sn': sn
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
        print('{0} - {1}'.format(sn, mac_address))
        devices.append(
            create_device(
                '{0}-{1}'.format(name_prefix, sn),
                mac_address,
                sn
            )
        )
    return devices


def calc_packet_count(second, step=10):
    packet_count = 0

    frequency_policy = {
        IMU_PKT: 1,
        GNSS_PKT: 100,
        INS_PKT: 1,
        ODO_PKT: 10,
        DIAG_PKT: 100,
        RTCM_PKT: 1,
        'nmea': 100
    }

    total_steps = int(second/step)
    for i in range(total_steps):
        for key in frequency_policy:
            if i % frequency_policy[key] == 0:
                packet_count += 1

    return packet_count


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

    mock_nmea_bytes = '$GPGGA,051612.00,3129.6798000,N,12021.8016833,E,1,33,0.0,-15.409,M,6.809,M,0.0,*6E\r\n$GPZDA,051612.00,15,09,2021,00,00,*47'.encode()
    empty_bytes = bytes(300)

    while True:
        output_packet = {}
        for key in frequency_policy:
            if count % frequency_policy[key] == 0:
                if key != 'nmea':
                    output_packet[key] = empty_bytes
                else:
                    output_packet[key] = mock_nmea_bytes

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

    sendp(packet_list, iface=RESOLVED_LOCAL_IFACE, verbose=0)
    return packet_list


def gen_packet_to_devices(device_mac_addresses, packet):
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


def format_log_info(devices):
    for device in devices:
        device.update_received_packet_info()

    return ', '.join(['{0}: {1}'.format(key, APP_CONTEXT.packet_data[key]) for key in APP_CONTEXT.packet_data])


def create_devices_process(mock_mac_addresses, status_flag):
    app_logger.new_session()

    devices = create_mock_devices('mock-prefix', mock_mac_addresses)
    for device in devices:
        device.start()

    while True:
        # if status_flag.value == 1:
        #    print('Mock packet sent.')
        #    break
        if devices[0]._received_packet_info[IMU_PKT] >= 1000:
            print('[Device] Receive end: {0}'.format(time.time()))
            break
        time.sleep(1)

    format_log_info(devices)


def gen_output_process(mock_mac_addresses, status_flag):
    duration = 10  # minute as unit

    mock_packet_generator = gen_mock_packet()

    plan_gen_count = duration*calc_packet_count(1000)*len(mock_mac_addresses)
    plan_send_packet_list = []
    print('[Data Mocker] Plan mock packet count:', plan_gen_count)
    print('[Data Mocker] Prepare start: {0}'.format(time.time()))
    while plan_gen_count > 0:
        packet = next(mock_packet_generator)
        ethernet_packet_list = gen_packet_to_devices(
            mock_mac_addresses, packet)

        plan_gen_count -= len(ethernet_packet_list)
        plan_send_packet_list.append(ethernet_packet_list)
    print('[Data Mocker] Prepare end: {0}'.format(time.time()))

    print('[Data Mocker] Start send time: {0}'.format(time.time()))
    for batch_packet_list in plan_send_packet_list:
        sendp(batch_packet_list, iface=RESOLVED_LOCAL_IFACE, verbose=0)
        time.sleep(0.01)
    print('[Data Mocker] End send time: {0}'.format(time.time()))
    #print('Output packet count:{0}'.format(output_packet_count))

    status_flag.value = 1


if __name__ == '__main__':
    # 1. create shared parameters
    output_packet_count = 0
    mock_len = 15

    mock_mac_addresses = gen_mock_mac_addresses(mock_len)
    status_flag = Value('i', 0)
    # 2. create devices as receiver
    devices_process = Process(
        target=create_devices_process,
        args=(mock_mac_addresses, status_flag))
    devices_process.start()

    # 3. create data mocker as sender
    output_process = Process(
        target=gen_output_process,
        args=(mock_mac_addresses, status_flag))
    output_process.start()
    output_process.join()

    devices_process.join()
