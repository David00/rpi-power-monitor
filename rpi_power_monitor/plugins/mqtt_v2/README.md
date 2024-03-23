# MQTT Documentation

#### Author: jplord, based on jmadden91 v1 implementation

## Purpose

The MQTT plugin allows you to export power monitor data to a MQTT-capable system. 

## Setup & Usage
You'll need to install the paho mqtt v2 client to use this plugin:

    pip install paho-mqtt>=2


The following configuration block needs to be added to the power monitor's `config.toml` file

```toml

[plugins.mqtt_v2]
    enabled = true
    host = "xxx.xxx.xxx.xxx"
    # Leave Username and Password "" if you are not using authentification
    username = ""
    password = ""
    prefix = "powermon"
    power_change = 5
    voltage_change = 3
    current_change = 1
    pf_change = 0.05
    refresh_rate = 5 # Refresh rate in seconds
    max_publish_seconds = 600

```

This plugin will send all measurements for all channels to the host specified above.
Alter power_change, voltage_change, current_change, pf_change to define how much variation in the values will trigger a publish
Alter max_publish_seconds to define how often values are republished regardless of variation


## Support
Please post any issues or questions in the pull request thread located here:

https://github.com/David00/rpi-power-monitor/pull/124
