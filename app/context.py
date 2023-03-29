IMU_PKT = b'\x01\n'
GNSS_PKT = b'\x02\n'
INS_PKT = b'\x03\n'
ODO_PKT = b'\x04\n'
DIAG_PKT = b'\x05\n'
RTCM_PKT = b'\x06\n'
RTCM_PKT2 = b'\x0c\n'
GI_PKT = b'\x49\x67'
PING_PKT = b'\x01\xcc'
FD_PKT = b'\x64\x66'
GET_PARAMETER_PKT = b'\x02\xcc'
SET_PARAMETER_PKT = b'\x03\xcc'
SAVE_CONFIG_PKT = b'\x04\xcc'

ETHERNET_OUTPUT_PACKETS = [
    IMU_PKT,  # IMU
    GNSS_PKT,  # GNSS
    INS_PKT,  # INS
    ODO_PKT,  # Odometer
    DIAG_PKT,  # Diagnose
    RTCM_PKT,  # RTCM Rover1
    RTCM_PKT2, # RTCM Rover2
    PING_PKT,  # Ping
    GI_PKT,  # GNSS solution integrity packet
    FD_PKT,  # FD
]

ETHERNET_OUTPUT_PACKETS_MAPPING = {
    IMU_PKT: 'IMU',
    GNSS_PKT: 'GNSS',
    INS_PKT: "INS",
    ODO_PKT: "Odometer",
    DIAG_PKT: "Diagnose",
    RTCM_PKT: "RTCM Rover1",
    RTCM_PKT2: "RTCM Rover2",
    PING_PKT: "Ping",
    GI_PKT: "GNSS Integrity",
    FD_PKT: "FD",
}


class APP_CONTEXT:
    packet_data = {}
    output_packets = ETHERNET_OUTPUT_PACKETS
    output_packets_mapping = ETHERNET_OUTPUT_PACKETS_MAPPING
