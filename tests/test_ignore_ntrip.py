import sys
import os

try:
    from main import select_ethernet_interface
    from app.bootstrap import Bootstrap
    from app import message
    from tools.mac_to_sn import convert_sn_to_mac
except:
    sys.path.append(os.getcwd())
    from main import select_ethernet_interface
    from app.bootstrap import Bootstrap
    from app import message
    from tools.mac_to_sn import convert_sn_to_mac


PING_PKT = b'\x01\xcc'
MOCK_PING = 'Mock mock-pn {0} RTK_INS App v28.01.13 Bootloader v01.01 IMU330ZA FW v27.00.10 STA9100 FW v5.10.16'

def build_ping_packet(sn: int) -> bytes:    
    bytes_data = bytes(MOCK_PING.format(sn), 'utf-8')
    return message.build(
        dst_mac='11:22:33:44:55:66',
        src_mac='66:55:44:33:22:11',
        pkt=PING_PKT,
        payload=bytes_data)


def mock_devices():
    sn_list = [2179000151, 2179000152, 2179000160, 2179000180]
    return [{'mac': convert_sn_to_mac(x), 'info': build_ping_packet(x)} for x in sn_list]


if __name__ == '__main__':
    try:
        iface = select_ethernet_interface()
        devices = mock_devices()
        Bootstrap().start_v2(iface, devices)
    except KeyboardInterrupt:
        pass
