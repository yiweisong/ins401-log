import sys
import os
import time
import json
import threading

try:
    from app.ntrip_client import NTRIPClient
    from app import message
except:
    sys.path.append(os.getcwd())
    from app.ntrip_client import NTRIPClient
    from app import message


class Device:
    _name = ''
    _total = 0

    def __init__(self, name) -> None:
        self._name = name
        self._total = 0

    def recv(self, data):
        #print(self._name, 'recv')
        self._total+=len(data)
        print(self._name,'raw data length', self._total)
        msg = message.build(
            dst_mac='11:22:33:44:55:66',
            src_mac='66:55:44:33:22:11',
            pkt=b'\x02\x0b',
            payload=data)
        #print(msg)


def receive_data(device: Device):
    #print(device._name)
    return lambda data: device.recv(data)


if __name__ == '__main__':
    app_conf = {}
    with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
        app_conf = (json.load(json_data))

    devices = []
    devices.append(Device('name1'))
    #devices.append(Device('name2'))

    for device in devices:
        ntrip_client = NTRIPClient(app_conf['ntrip'])
        ntrip_client.on('parsed', receive_data(device))
        #ntrip_client.run()
        threading.Thread(target=lambda: ntrip_client.run()).start()

    while True:
        time.sleep(10)
