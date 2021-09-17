import os
import sys
import struct
from ctypes import *

try:
    from app import message
except:
    sys.path.append(os.getcwd())
    from app import message

if __name__ == '__main__':
    # load the shared object file
    utils = CDLL(os.path.join(os.getcwd(), 'libs/utils.so'))

    # Find sum of integers
    c_crc = utils.calc_crc(bytes([1, 2]), 2)

    py_crc = struct.unpack('<H', bytes(message.calc_crc([1, 2])))[0]

    print('CRC from c lib', c_crc)
    print('CRC from python', py_crc)
