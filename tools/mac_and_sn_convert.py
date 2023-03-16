import struct
import argparse

def _build_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Input args command:', allow_abbrev=False)

    parser.add_argument("-s", "--sn", dest="sn", help="Serial Number")
    parser.add_argument("-m", "--mac", dest="mac", help="Mac address")

    return parser.parse_args()

def convert_sn_to_mac(sn: int):
    suffix = '00:28'
    sn_mac = ':'.join(['%02x' % x for x in struct.pack('<I', sn)])
    return '{0}:{1}'.format(sn_mac, suffix)

def convert_mac_to_sn(mac_address: str):
    str_sn_parts = mac_address.split(':')[0:4]
    integer_sn_parts = [int(value, 16) for value in str_sn_parts]
    return struct.unpack('<I', bytes(integer_sn_parts))[0]

if __name__ == '__main__':
    options = _build_args()

    if options.sn:
        mac_address = convert_sn_to_mac(int(options.sn))
        print('{0} MAC: {1}'.format(options.sn, mac_address))

    if options.mac:
        sn = convert_mac_to_sn(options.mac)
        print('{0} SN: {1}'.format(options.mac, sn))