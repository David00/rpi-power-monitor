# MQTT Documentation

#### Author: jmadden91

## Purpose

The MQTT plugin allows you to export power monitor data to a MQTT-capable system. 

## Setup & Usage
You'll need to install the v1 paho mqtt client to use this plugin:
    
    pip install paho-mqtt==1.6.1


The following configuration block needs to be added to the power monitor's `config.toml` file

```toml

[plugins.mqtt]
    enabled = true
    host = "192.168.x.x"
    username = "username"
    password = "password"
    prefix = "powermon"
    refresh = 5 # Refresh rate in seconds

```

This plugin will send all measurements for all channels to the host specified above.



## Support
Please post any issues or questions in the pull request thread located here:

https://github.com/David00/rpi-power-monitor/pull/104