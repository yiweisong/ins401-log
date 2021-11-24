import sys
import os
import time
import json
import threading

try:
    from app.ntrip_client import NTRIPClient
except:
    sys.path.append(os.getcwd())
    from app.ntrip_client import NTRIPClient


class Device:
    _name = ''

    def __init__(self, name) -> None:
        self._name = name

    def recv(self, data):
        print(self._name, 'recv')


def receive_data(device: Device):
    print(device._name)
    return lambda data: device.recv(data)


if __name__ == '__main__':
    app_conf = {}
    with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
        app_conf = (json.load(json_data))

    devices = []
    devices.append(Device('name1'))
    devices.append(Device('name2'))

    for device in devices:
        ntrip_client = NTRIPClient(app_conf['ntrip'])
        ntrip_client.on('parsed', receive_data(device))
        #ntrip_client.run()
        threading.Thread(target=lambda: ntrip_client.run()).start()

    while True:
        time.sleep(10)
