import functools
import importlib
from threading import Thread
from multiprocessing import Process, Event
import logging
import sys

class Plugin():
    '''Represents a plugin for the Power Monitor for Raspberry Pi.'''

    def __init__(self, name, config):
        '''Creates a plugin instance.'''

        self.name = name
        self.config = config
        self.stop_flag = Event()
        self.running = False
        self.process = None

        self.setup_logging()
        

        try:        
            self._module = importlib.import_module(f'plugins.{name}.{name}')

            if not ( hasattr(self._module, 'start_plugin') and hasattr(self._module, 'stop_plugin') ):
                self.logger.warning(f"Plugin {name} does not have the start_plugin or stop_plugin functions defined.")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to import enabled plugin {name}. Detail for failure: ")
            self.logger.debug(f"Exception: {e}")
            self._module = None



    def start(self, results, *args, **kwargs):
        '''Starts the plugin.'''

        start_plugin = getattr(self._module, 'start_plugin')
        if not start_plugin:
            self.logger.warning(f"Plugin {self.name} is missing the start_plugin function. Unable to start plugin.")
            return False
        
        p = Process(target=start_plugin, args=(results, self.stop_flag, self.config, self.logger))
        p.start()
        self.process = p
        self.running = True
    
    def stop(self, *args, **kwargs):
        '''Stops the plugin.'''
        self.stop_flag.set()
        if self.process:
            self.process.join(timeout=30)
            if not self.process.is_alive():
                return True # Process stopped successfully
                self.running = False
            else:
                return False
        else:   # Plugin was never started
            return True

    def setup_logging(self, *args, **kwargs):
        '''Creates the plugin-level logger.'''

        # The plugin logger will pull the same logging level as the power monitor class' level, unless log_level is specified in the plugin's config.
        self.logger = logging.getLogger(f'plugin_{self.name}')

        if self.config.get('log_level'):
            log_level = self.config.get('log_level')

        else:
            log_level = logging.getLevelName(logging.getLogger('power_monitor').level)
        
        try:
            self.logger.setLevel(log_level)
            pch = logging.StreamHandler(sys.stdout)
            pch.setLevel(log_level)
            pch_formatter = logging.Formatter('%(name)s : %(asctime)s : %(levelname)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            pch.setFormatter(pch_formatter)        
            self.logger.addHandler(pch)
        except:
            logging.getLogger('power_monitor').warning(f"Failed to setup logging for plugin {self.name}. Invalid logging level value ({log_level}).")
        
    def __repr__(self):
        return f'Plugin(Name: {self.name}, Running: {self.running})'