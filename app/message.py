import struct

COMMAND_START = [0x55, 0x55]

PAYLOAD_MIN_LENGTH = 46


def calc_crc(payload):
    '''
    Calculates 16-bit CRC-CCITT
    '''
    crc = 0x1D0F
    for bytedata in payload:
        crc = crc ^ (bytedata << 8)
        i = 0
        while i < 8:
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            i += 1

    crc = crc & 0xffff
    crc_msb = (crc & 0xFF00) >> 8
    crc_lsb = (crc & 0x00FF)
    return [crc_msb, crc_lsb]


def build(dst_mac, src_mac, pkt, payload=[]):
    '''
    Build final packet
    '''
    packet = []
    packet.extend(payload)
    msg_len = len(payload)

    packet_len = struct.pack("<I", msg_len)

    packet.extend(packet_len)
    final_packet = packet + payload

    msg_len = len(COMMAND_START) + len(final_packet) + 2
    payload_len = struct.pack('<H', len(COMMAND_START) + len(final_packet) + 2)

    whole_packet = []
    header = dst_mac + src_mac + bytes(payload_len)
    whole_packet.extend(header)

    whole_packet.extend(COMMAND_START)
    whole_packet.extend(final_packet)
    whole_packet.extend(calc_crc(final_packet))
    if msg_len < PAYLOAD_MIN_LENGTH:
        fill_bytes = bytes(PAYLOAD_MIN_LENGTH-msg_len)
        whole_packet.extend(fill_bytes)

    return bytes(whole_packet)
