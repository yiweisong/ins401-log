'''
 1. List all interface
    Confirm the interface, save selection for next running

 2. Start to listen data in the interface

 3. Ping device in 5s(may be need configure)
    Send ping command

 4. Collect response
    Return the mac address
'''
from app.bootstrap import Bootstrap
from app.device import collect_devices
from scapy.all import conf, resolve_iface, NetworkInterface
from terminal_layout import *
from terminal_layout.extensions.choice import *
import signal
import os
import json


def kill_app(signal_int, call_back):
    '''Kill main thread
    '''
    os.kill(os.getpid(), signal.SIGTERM)


def select_ethernet_interface():
    '''
     load local network interface from config.json
     if set use the configured one, else scan the network interfaces
    '''
    app_conf = {}
    config_file_path = os.path.join(os.getcwd(), 'config.json')
    try:
        with open(config_file_path) as json_data:
            app_conf = (json.load(json_data))
    except:
        print('Read configuration failed')
        return None

    if app_conf.__contains__('local'):
        return resolve_iface(app_conf['local']['name'])

    ethernet_list = [conf.ifaces[item].name for item in conf.ifaces]
    c = Choice('Which ehternet interface you are using?',
               ethernet_list,
               icon_style=StringStyle(fore=Fore.blue),
               selected_style=StringStyle(fore=Fore.blue), default_index=0)

    choice = c.get_choice()
    if choice:
        index, value = choice
        # save to config.json

        network_interface = resolve_iface(value)
        app_conf['local'] = {
            'name': network_interface.description,
            'mac': network_interface.mac
        }
        try:
            with open(config_file_path, 'w') as outfile:
                json.dump(app_conf, outfile, indent=4, ensure_ascii=False)
            return network_interface
        except:
            print('Write configuration failed')
            return None

    return None


def build_ping_info(iface: NetworkInterface):
    step_next = False
    devices = []
    while not step_next:
        devices = collect_devices(iface)
        c = Choice('We have find {0} device(s), need rescan?'.format(len(devices)),
                   ['No', 'Yes'],
                   icon_style=StringStyle(fore=Fore.blue),
                   selected_style=StringStyle(fore=Fore.blue),
                   default_index=0)

        choice = c.get_choice()
        if choice:
            index, _ = choice
            if index == 0:
                step_next = True
            else:
                step_next = False
                print('Rescaning...')

    return devices


def data_collect(network_interface, devices):
    '''
    device: dict({'mac','info'})
    '''
    Bootstrap().start_v2(network_interface, devices)


if __name__ == '__main__':
    try:
        iface = select_ethernet_interface()
        devices = build_ping_info(iface)
        data_collect(iface, devices)
    except KeyboardInterrupt:
        pass

    # Bootstrap().start()
