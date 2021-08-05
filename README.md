# Multiple INS401 device data logger

## Setup
The application has no automatic detect feature. So it has to setup the log machine's network MAC address and device MAC address

### Log machine's network MAC address
1. Open the `config.json`. Edit the `local` section.
2. If you don't know your log machine's network MAC address. Please run `ipconfig -all` to get the detailed information.

### Device MAC address
Go to the folder `configs/devices`, add your device configuration in the folder. There is a sample file, it is named `sample_device_json`. Please make sure your configuration should be a `json` file.

Field descritpion:

#### mac

It is the device's MAC address.

#### parameters

It is a list of supported parameter list of INS401. If you set the value for one parameter, the application will save the configured value to device before it starts log.