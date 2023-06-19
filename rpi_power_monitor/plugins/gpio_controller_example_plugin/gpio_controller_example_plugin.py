# Plugin for the Power Monitor for Raspberry Pi
# Plugin Name: GPIO Controller (Example)
# Author: David00
# Description: This plugin is an example plugin for developers to reference when adding or extending the functionality of the base RPI Power Monitor project. 
# It will set the state of a GPIO pin based on the last reading of the power monitor.
# The plugin demonstrates several key components:
# - accessing the plugin configuration from config.toml
# - accessing the latest power monitor data
# - logging to the terminal
#
# See the docs for more info on writing plugins: https://david00.github.io/rpi-power-monitor/docs/v0.3.0/plugins.html

import RPi.GPIO as GPIO
from time import sleep
from datetime import timedelta
from .. import sleep_for

def start_plugin(data, stop_flag, config, logger, *args, **kwargs):
    '''This function should start your plugin and contain a While True loop if your plugin is designed to be constantly running.
    
    This function will be called if the plugin is enabled in the power monitor's config.toml, and it will be started as a child process, owned by the main power monitor process.

    The following parameters are provided from the power monitor itself:
        - data: a dictionary containing the latest power monitor data. See below for the structure.
        - stop_flag: a multiprocessing.Event() object that your plugin must check the status for in order to know when to stop.
        - config: the plugins config from config.toml, parsed into a dictionary.
        - logger: a Python logger object, specific this plugin. Your plugin can use this logger to log any important messages or debugs to the console.

    A plugin's while loop should run until either:
        - the stop_flag is set, or
        - your plugin has finished its task and is not intended to run indefinitely.

    The main config.toml file should have the following config section defined for this plugin:

    [plugins.gpio_controller_example_plugin]
    enabled = true
    pin_numbering_scheme = 'BCM'
    output_pin = 17
    input_pin = 27
    # Optional Config settings
    # log_level = 'INFO'  # This will override the logging level for the plugin, which normally gets the logging level from the main program.  

    Here is the full structure of the data dictionary, with real sample values. 

    Here are the units used:
        'power'   : Always in Watts
        'pf'      : A float between the range of -1.0 and 1.0
        'current' : Always in Amperes
        'voltage' : Always in Volts

        {
            "cts":{
                "1":{
                    "power":-0.15614170241133654,
                    "pf":-0.008707578629557584,
                    "current":-0.01341197029282334,
                    "voltage":133.23533164737233
                },
                "2":{
                    "power":-0.018413940715636623,
                    "pf":-0.0008359884096381318,
                    "current":-0.1405852064282471,
                    "voltage":133.2450403146403
                },
                "3":{
                    "power":-0.3871674075367957,
                    "pf":-0.020716933660741007,
                    "current":0.1413622934508677,
                    "voltage":133.2428933653774
                },
                "4":{
                    "power":-0.18666605908420159,
                    "pf":-0.009948353174774924,
                    "current":0.14011308998509991,
                    "voltage":133.24793799600786
                },
                "5":{
                    "power":-0.20825052262125632,
                    "pf":-0.01114300361840111,
                    "current":0.14088852673526656,
                    "voltage":133.2452814824922
                },
                "6":{
                    "power":0.05813865566604561,
                    "pf":0.0030650506064272562,
                    "current":0.14096820400791774,
                    "voltage":133.24494676750146
                }
            },
            "production":{
                "power":0.0,
                "pf":0.0,
                "current":0.0
            },
            "home-consumption":{
                "power":-0.1745556431269732,
                "current":0.15399717672107044
            },
            "net":{
                "power":-0.1745556431269732,
                "current":0.15399717672107044
            },
            "voltage":133.23533164737233
        }
    '''    

    logger.info("Starting GPIO Example Plugin")


    # GPIO Setup

    if config.get('pin_numbering_scheme') == 'BCM':
        GPIO.setmode(GPIO.BCM)
    elif config.get('pin_numbering_scheme') == 'BOARD':
        GPIO.setmode(GPIO.BOARD)

    input_pin = config.get('input_pin')
    output_pin = config.get('output_pin')
    
    GPIO.setup(input_pin, GPIO.IN)
    GPIO.setup(output_pin, GPIO.OUT)


    while not stop_flag.is_set():
        # Check the latest net power status. If the power monitor is reporting an overall net-export, then set the configured GPIO output pin high.
        # If the power monitor is reporting an overall net-import, set the GPIO output pin low.

        try:
            if data['net']['power'] < 0:
                # To prevent rapid GPIO state changes, the current time will be compared to the time of the last state change.
                GPIO.output(output_pin, GPIO.HIGH)
                logger.debug(f"Setting pin {output_pin} high because net power is {data['net']['power']}")
                
            else:
                GPIO.output(output_pin, GPIO.LOW)
                logger.debug(f"Setting pin {output_pin} low because net power is {data['net']['power']}")

        except KeyError:
            logger.debug(f"Failed to get the net power from the data dictionary. If the power monitor just started, this is normal.")

        # Sleep for 60 seconds, using the provided sleep_for() function.
        sleep_for(60, stop_flag)

    stop_plugin()
    return


def stop_plugin():
    '''This function should stop your plugin and execute any required cleanup procedures.
    
    The function will be called if the power monitor stops, so it must be included in your plugin. However, if you don't have any cleanup procedures, simply leave the definition empty, with the return statement below.
    '''

    GPIO.cleanup()

    return