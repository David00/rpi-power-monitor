# Plugin for the Power Monitor for Raspberry Pi
# Plugin Name: plugin_name
# Author: Your name/username/nickname
# Description: Brief description (<= 1 paragraph... more detail can be added to your README.md)

# Python Imports
from .. import sleep_for    # Leave this import, and use sleep_for() instead of time.sleep() to put your plugin to sleep. See the docs for more details about sleep_for().

def start_plugin(data, stop_flag, config, logger, *args, **kwargs):
    '''This function will be called if the plugin is enabled in the power monitor's config.toml, and it will be started as a child process, owned by the main power monitor process.
    
    The data, stop_flag, config, and logger arguments are required, so please don't change the function definition. 
    '''  

    # Plugin Startup Routine - any necessary initialization can be done here, before the while loop below.

    
    while not stop_flag.is_set():
        # The actual work for your plugin will likely go here, inside this while loop.
        
        # Sleep for 60 seconds, using the provided sleep_for() function. (60 seconds is just an example - you can change the sleep value as needed for your function to do its job.)
        sleep_for(60, stop_flag)

    stop_plugin()
    return

def stop_plugin():
    '''This function should stop your plugin and execute any required cleanup procedures.
    
    The function will be called if the power monitor stops, so it must be included in your plugin. However, if you don't have any cleanup procedures, simply leave the definition empty, with the return statement below.
    '''

    return