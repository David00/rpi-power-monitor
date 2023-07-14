# GPIO Controller Documentation

#### Author: David00

## Purpose
The GPIO Controller serves mainly as an example plugin to demonstrate how to build a plugin for this project.  However, it is a fully functional plugin, and as written, it will perform the following functions:

* Setup a single pin as an INPUT
* Setup a single pin as an OUTPUT
* Every 1 minute, set the output pin to 1/high if the power monitor's measurements are reporting a net-export of power.
* Every 1 minute, set the output pin to 0/low if the power monitor's measurements are reporting a net-import of power.

## Setup & Usage
This plugin requires RPi.GPIO to work. You can install it with the following command:
    
    pip install RPi.GPIO


The following configuration block needs to be added to the power monitor's `config.toml` file:

```toml
[plugins.gpio_controller_example_plugin]
    enabled = true
    pin_numbering_scheme = 'BCM'
    output_pin = 17
    input_pin = 27
    # Optional Config settings
    # log_level = 'INFO'  # This will override the logging level for the plugin, which normally gets the logging level from the main program.  
```

The input and output pins can use the "BCM" or the "BOARD" scheme. Here's the difference:

* BCM uses the "GPIO #" syntax: usually GPIO 1 through GPIO 26.
* BOARD uses the actual pin number on the header: 1 - 40

_See the "What do these numbers mean?" section on https://pinout.xyz/ for more info, and for a detailed header pinout map._

## Modifications
This plugin is a barebones example of how to write a plugin. Therefore, the actual logic of the plugin is fairly simple and may require modification to meet the needs of various users.  The entire logic of the plugin is contained inside [a `while` loop](https://github.com/David00/rpi-power-monitor/blob/develop/v0.3.0-plugins/rpi_power_monitor/plugins/gpio_controller_example_plugin/gpio_controller_example_plugin.py#L124) - this is where the decision is made to change the state of the output pin and is the likely place for you to expand the functionality of the plugin.

## Support
Please use [GitHub Discussions](https://github.com/David00/rpi-power-monitor/discussions) if you have questions about using or modifying this plugin.
