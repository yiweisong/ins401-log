'''
 1. List all interface
    Confirm the interface, save selection for next running

 2. Start to listen data in the interface

 3. Ping device in 5s(may be need configure)
    Send ping command

 4. Collect response
    Return the mac address
'''
from typing import Dict
from app.bootstrap import Bootstrap
from app.decorator import receive_args
from app.device import collect_devices
from scapy.all import conf, resolve_iface, NetworkInterface
from terminal_layout import *
from terminal_layout.extensions.choice import *
import signal
import os
import json
import time


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

    description_list = [
        conf.ifaces[item].description for item in conf.ifaces if conf.ifaces[item].mac]

    if app_conf.__contains__('local'):
        local_mac = app_conf['local']['name']
        if local_mac in description_list and app_conf['local']['mac']:
            return resolve_iface(local_mac)

    ethernet_list = [
        conf.ifaces[item].name for item in conf.ifaces if conf.ifaces[item].mac]

    c = Choice('Which ehternet interface you are using?',
               ethernet_list,
               icon_style=StringStyle(fore=Fore.green),
               selected_style=StringStyle(fore=Fore.green), default_index=0)

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


def detect_devices(iface: NetworkInterface,args):
    step_next = False
    devices = []
    while not step_next:
        devices = collect_devices(iface)

        if args.keep_detect:
            if len(devices) == 0:
                time.sleep(15)
                continue
            return devices

        c = Choice('We have find {0} device(s), start to log?'.format(len(devices)),
                   ['Yes', 'No'],
                   icon_style=StringStyle(fore=Fore.green),
                   selected_style=StringStyle(fore=Fore.green),
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


def prepare(args):
    if args.reset:
        app_conf:Dict = {}
        config_file_path = os.path.join(os.getcwd(), 'config.json')
        try:
            with open(config_file_path) as json_data:
                app_conf = (json.load(json_data))
        except:
            print('Read configuration failed')
            return None

        try:
            if not app_conf.__contains__('local'):
                return None

            del app_conf['local']
            with open(config_file_path, 'w') as outfile:
                json.dump(app_conf, outfile, indent=4, ensure_ascii=False)
        except:
            print('Write configuration failed')
            return None

@receive_args
def main(**kwargs):
    prepare(kwargs['options'])
    iface = select_ethernet_interface()
    devices = detect_devices(iface,kwargs['options'])
    Bootstrap().start(iface, devices)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

    # Bootstrap().start()
