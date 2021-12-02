import struct


def convert_mac_to_sn(mac_address: str):
    str_sn_parts = mac_address.split(':')[0:4]
    integer_sn_parts = [int(value, 16) for value in str_sn_parts]
    return struct.unpack('<I', bytes(integer_sn_parts))[0]


def convert_sn_to_mac(sn: int):
    suffix = '00:28'
    sn_mac = ':'.join(['%x' % x for x in struct.pack('<I', sn)])
    return '{0}:{1}'.format(sn_mac, suffix)


if __name__ == '__main__':
    mac_addresses = [
        'd2:e6:e0:81:00:28',
        'd5:e6:e0:81:00:28',
        'd7:e6:e0:81:00:28',
        'd8:e6:e0:81:00:28',
        'da:e6:e0:81:00:28',
        'db:e6:e0:81:00:28',
        'de:e6:e0:81:00:28',
        'df:e6:e0:81:00:28',
        'e0:e6:e0:81:00:28',
        'e5:e6:e0:81:00:28',
        'ca:e6:e0:81:00:28',
    ]
    for mac_address in mac_addresses:
        sn = convert_mac_to_sn(mac_address)
        print('{0} SN:{1}'.format(mac_address, sn))
