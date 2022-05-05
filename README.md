# Multiple INS401 device data logger

## Setup
The application has no automatic detect feature. So it has to setup the log machine's network MAC address and device MAC address

## Configuration

### config.json
This a configuration file for ins401-log application.

Field description:

`ntrip`

Fill the ntrip account. It is used to receive data from ntrip server.

`ignore_ntrip`

If you don't want some device receive ntrip server data, please add the serial number of the device.

`append_listen_packets`

There are some packet data could be listened by default. Here is the list.
| Name | Value |
| - | - |
| IMU | 0x010a |
| GNSS | 0x020a |
| INS | 0x030a |
| Odometer | 0x040a |
| Diagnosis | 0x050a |
| RTCM Rover | 0x060a |
| GNSS Solution Integrity | 0x4967 |
| FD | 0x6466 |
| Ping | 0x01cc |

If you need listen more packet type of data, please add it in this node. The sample value should be
```javascript
{
    "name":"DM", // display name
    "value":"0x444d" // Hex value, 2 bytes
}
```

### configs/devices
Go to the folder `configs/devices`, add your device configuration in the folder. There is a sample file, it is named `sample_device_json`. Please make sure your configuration should be a `json` file.

Field descritpion:

`mac`

It is the device's MAC address.

`parameters`

It is a list of supported parameter list of INS401. If you set the value for one parameter, the application will save the configured value to device before it starts log.