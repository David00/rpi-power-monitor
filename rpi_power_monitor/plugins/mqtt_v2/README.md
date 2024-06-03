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

## Configuration options

    enabled

Needs to be set to true to enable the plugin.

    username
    password

Specify the required username and password for MQTT. Leave "" if you are not using MQTT authentification.

    prefix

Specify the prefix of the mqtt topic used to publish the values.

    power_change
    voltage_change
    current_change
    pf_change

Define these values to determine the required variation in power, voltage, current or pf that will force an MQTT publish of the new value if detected over a period of less than the configured max_publish_seconds.
For example, with a configuration of voltage_change = 3, if the voltage is stable at 122.00 volt and it drops to 118.00 volt over a period of time that is less than the configured max_publish_seconds, the 118.00 volt value will be published to MQTT immediately and as soon as detected as it is a delta of 4 volt which is greater than the configured 3 volt. The same would occur if 118.00 volt is measured and an increase to 122.00 volt occurs over a time period of less than max_publish_seconds.

    max_publish_seconds

Define this value to force a publish of the refreshed and most up to date values of all measurements regardless of if they changed of not.

    refresh_rate

How often this plugin will read current values from the samples provided by rpi-power-monitor.

## Support
Please post any issues or questions in the pull request thread located here:

https://github.com/David00/rpi-power-monitor/pull/124
