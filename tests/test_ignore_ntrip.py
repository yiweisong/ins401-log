import sys
import os
import time
import json
import threading

try:
    from main import select_ethernet_interface
    from app.bootstrap import Bootstrap
    from app import message
except:
    sys.path.append(os.getcwd())
    from main import select_ethernet_interface
    from app.bootstrap import Bootstrap
    from app import message

def build_ping_packet(data: str)->bytes:
    PING_PKT = b'\x01\xcc'

    return message.build(
            dst_mac='11:22:33:44:55:66',
            src_mac='66:55:44:33:22:11',
            pkt=PING_PKT,
            payload=bytes(data,'utf-8'))

def mock_devices():
    
    return [
        {'mac':'11:22:33:44:55:66', 'info':build_ping_packet('Mock mock-pn 2179000151 RTK_INS App v28.01.13 Bootloader v01.01 IMU330ZA FW v27.00.10 STA9100 FW v5.10.16')},
        {'mac':'12:22:33:44:55:66', 'info':build_ping_packet('Mock mock-pn 2179000152 RTK_INS App v28.01.13 Bootloader v01.01 IMU330ZA FW v27.00.10 STA9100 FW v5.10.16')},
        {'mac':'13:22:33:44:55:66', 'info':build_ping_packet('Mock mock-pn 2179000160 RTK_INS App v28.01.13 Bootloader v01.01 IMU330ZA FW v27.00.10 STA9100 FW v5.10.16')},
        {'mac':'14:22:33:44:55:66', 'info':build_ping_packet('Mock mock-pn 2179000180 RTK_INS App v28.01.13 Bootloader v01.01 IMU330ZA FW v27.00.10 STA9100 FW v5.10.16')},
    ]

if __name__ == '__main__':
    try:
        iface = select_ethernet_interface()
        devices = mock_devices()
        Bootstrap().start_v2(iface, devices)
    except KeyboardInterrupt:
        pass