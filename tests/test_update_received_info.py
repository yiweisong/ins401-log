import sys
import os
import time
try:
    from app import app_logger
    from app.device import INS401
except:
    sys.path.append(os.getcwd())
    from app import app_logger
    from app.device import INS401


def create_device(name):
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

    return INS401('mock', 'mock', 'mock', data_log_info, device_info, app_info)


def create_devices():
    devices = []
    for i in range(10):
        devices.append(create_device('device_{0}'.format(i)))
    return devices


if __name__ == '__main__':
    app_logger.new_session()
    devices = create_devices()
    
    for device in devices:
        device.update_received_packet_info()
