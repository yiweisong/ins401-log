import sys
import os
import json

try:
    from app import utils
    from app.device import build_config_parameters_command_lines
except:
    sys.path.append(os.getcwd())
    from app import utils
    from app.device import build_config_parameters_command_lines

if __name__ == '__main__':
    app_conf={}
    with open(os.path.join(os.getcwd(), 'config.json')) as json_data:
        app_conf = (json.load(json_data))

    device_config_folder=os.path.join(os.getcwd(),'configs','devices')
    print(utils.list_files(device_config_folder))

    # load device config
    device_config_paths = utils.list_files(device_config_folder)
    
    for path in device_config_paths:
        with open(path) as json_data:
            device_conf = json.load(json_data)
            if not device_conf.__contains__('mac'):
                continue

            if not app_conf.__contains__('devices'):
                app_conf['devices'] = []
            
            app_conf['devices'].append(device_conf)

    for item in app_conf['devices']:
        if not item.__contains__('parameters') and \
            not isinstance(item.get('parameters'), list):
            continue
        
        print(item['mac'], isinstance(item['parameters'], list))
        command_lines = build_config_parameters_command_lines(item,app_conf['local'])
        for command_line in command_lines:
            print(command_line)
