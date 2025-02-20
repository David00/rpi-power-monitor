import csv
import logging
import os
import subprocess
import sys
import timeit
from datetime import datetime, timezone
from math import sqrt, cos
from socket import AF_INET, SOCK_DGRAM, socket, getaddrinfo
import ipaddress
from textwrap import dedent
import tomli
import spidev
from prettytable import PrettyTable
import argparse
import pathlib
from multiprocessing import Manager, Event
import signal
from copy import deepcopy
import os
from typing import Union
import atexit

from rpi_power_monitor.plotting import plot_data
from rpi_power_monitor.influx_helpers.tasks import _add_task




# Logging Config
logger = logging.getLogger('power_monitor')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch_formatter = logging.Formatter('%(levelname)s : %(message)s')
ch.setFormatter(ch_formatter)
if len(logger.handlers) == 0:
    logger.addHandler(ch)

module_root = pathlib.Path(__file__).parent

parser = argparse.ArgumentParser(description='Power Monitor CLI Interface', epilog='Please see the project documentation at https://github.com/david00/rpi-power-monitor#readme for further usage instructions.')
parser.add_argument('--mode', type=str, help="Operating Mode. Defaults to 'main' if not specified.", default='main', required=False, choices=['main', 'terminal', 'plot'])
parser.add_argument('--samples', type=int, help="Optionally specify the number of samples to capture in plot mode.", required=False)
parser.add_argument('--title', type=str, help="Optionally specify the title of the generated plot.", required=False)
parser.add_argument('--config', type=pathlib.Path, help='path to config.toml file.', default= os.path.join(module_root, 'config.toml'), required=False)
parser.add_argument('-v', '--verbose', help='Increases verbosity of program output.', action='store_true')
parser.add_argument('-V', '--version', help='Displays the power monitor software version and exits.', action='store_true')

# Retention Policy Settings
retention_policies = {
    'rp_5min' : {
        'duration' : 'INF'
    },
    'autogen' : {      # This is the default retention policy.
        'duration' : '30d'
    }
}



class RPiPowerMonitor:
    """ Class to take readings from the MCP3008 and calculate power for up to 8 ADC channels.
    
    Arguments:

        - config: str|dict, if `config` is a string, it should be a path to the config (relative paths to this module are okay). If `config` is a dict, it should follow the structure below.
          (See the Configuration Reference Manual for details on these settings)
          https://david00.github.io/rpi-power-monitor/docs/latest/configuration.html#configuration-reference-manual

        {
            'general' : {
                'name' : 'Power-Monitor'
                },
            'database' : {
                'enabled' : true,
                'host' : 'localhost',
                'port' : 8086,
                'username' : 'root',
                'password' : 'password',
                'database_name' : 'power_monitor'
            },
            'grid_voltage' : {
                'grid_voltage' : 120.1,
                'ac_transformer_output_voltage' : 10.51,
                'frequency' : 60,
                'voltage_calibration' : 1.0
                },
            'current_transformers' : {
                'channel_1' : {
                    'name' : 'Channel 1',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
                'channel_2' : {
                    'name' : 'Channel 2',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
                'channel_3' : {
                    'name' : 'Channel 3',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
                'channel_4' : {
                    'name' : 'Channel 4',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
                'channel_5' : {
                    'name' : 'Channel 5',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
                'channel_6' : {
                    'name' : 'Channel 6',
                    'rating' : 100,
                    'type' : 'consumption',
                    'two_pole' : false,
                    'enabled' : true,
                    'calibration' : 1.0,
                    'amps_cutoff_threshold' : 0,
                    'reversed' : false,
                    'phase_angle' : 0
                },
            },
            # Backups are optional - no need to include this unless you want to use them.
            'backups' : {
                'backup_device' : '/dev/sda1',
                'folder_name' : 'power_monitor_backups',
                'mount_path' : '/media/backups',
                'backup_count' : 2    
            },
            # Plugins are optional - no need to include this section unless there are plugins you want to use.
            'plugins' : {
                'mqtt_v2' : {
                    # Specific plugin options go here - for example:
                    'enabled' : true,
                    'host' : '192.168.0.10'
                }
            }
            
        }
        

        - mode: str, one of the following options ['plot', 'terminal' , 'main']. See docs for more info on each mode:
          https://david00.github.io/rpi-power-monitor/docs/v0.3.0/advanced-usage.html#--mode
    
    """
    
    _halt_flag = Event()
    
    def __init__(self, mode='main', config=os.path.join(module_root, 'config.toml'), spi=None) -> None:
        self._setup_signal_handlers()        
        self.pid = os.getpid()
        self.imported_plugins = dict()
        
        self._load_config(config)
        atexit.register(self._cleanup)

        if not self.config.get('disable_dup_process_check'):
            duplicate = self._check_dup_process()
            if duplicate:
                self._cleanup()
        
        if spi:
            self.spi = spi
        else:
            self.spi = spidev.SpiDev()
            try:
                self.spi.open(0, 0)
            except Exception as e:
                logger.critical("Unable to open SPI interface. Is SPI enabled on this device?")
                self._cleanup()
            self.spi.max_speed_hz = 1750000

        # Check sample rate:
        self._measure_sample_rate()
        
        # If database is enabled in config, initialize the InfluxDB connection.
        # The 'enabled' configuration option for 'database' was added in v0.4.0. Because of this, users running a config file from v0.3.x or earlier will not have 
        # the 'enabled' option in their config.  Therefore, when we attempt to load the setting below, 'enabled' will be one of the following:
        #   - None if the user doesn't have the option (ie, using an old config). In this case, the database should be assumed enabled/wanted.
        #   - False if the user explicitely disabled the database connection.
        #   - True if the user is using a new config as of v0.4.0 (as True is the default setting).

        config_db_value = self.config['database'].get('enabled')
        if config_db_value in (True, None):
            self.DB_ENABLED = True
            self._get_db_client()
            if config_db_value is None:
                logger.warning("It appears you may be running an old config file for this version of the power monitor code. Please see for the link to the latest config file: https://david00.github.io/rpi-power-monitor/docs/latest/configuration.html#configuration-reference-manual")
            if not self.client:
                logger.error(f"Failed to connect to InfluxDB server at {self.config['database']['host']}:{self.config['database']['port']}. Please make sure it's reachable and try again.")
                self._cleanup(-1)
        else:
            self.DB_ENABLED = False
        self.points_buffer = [] # A buffer to hold sublists of points so that they can be written altogether (reduces DB overhead)
        self.def_cal = 0.88     # This is the default calibration factor for all CTs from my shop.
        self.terminal_mode = False
        self.PF_DELTA = 20      # This value enforces a minimum amperage waveform quality in order to calculate PF. 
                                # If the measured waveform peak-trough delta is less than this value, PF will not be calculated and will be set to zero.

        # Plugin Loading
        if self.config.get('plugins') is not None:
            self._load_plugins(self.config.get('plugins'))   # Note: Plugins are initialized here, but they are only started when the power monitor routine starts.

    
    def _validate_cqs(self) -> None:
        '''Ensures that the continuous queries exist in the configured Influx v1 database, and creates them if not.'''

        retention_policies = {
            '5m' : 'rp_5min'
        }

        try:
            db_name = self.config['database']['database_name']
            cqs = self.client.get_list_continuous_queries()
            existing_cqs = []
            for db in cqs:
                if db_name in db.keys():
                    if len(db[db_name]) > 0:
                        existing_cqs = [cq['name'] for cq in db[db_name]]
            
            # Home Power, Energy
            if 'cq_home_power_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_home_power_{duration}', f'SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."home_load_{duration}" FROM "home_load" GROUP BY time({duration})')
                    logger.debug(f"Created continuous query: cq_home_power_{duration}")
            
            if 'cq_home_energy_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_home_energy_{duration}', f'''SELECT integral("power") / 3600000 AS "energy" INTO "{rp_name}"."home_energy_{duration}" FROM "home_load" GROUP BY time({duration})''')
                    logger.debug(f"Created continuous query: cq_home_energy_{duration}")

            # Net Power, Energy
            if 'cq_net_power_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_net_power_{duration}', f'SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."net_power_{duration}" FROM "net" GROUP BY time({duration})')
                    logger.debug(f"Created continuous query: cq_net_power_{duration}")

            if 'cq_net_energy_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_net_energy_{duration}', f'''SELECT integral("power") / 3600000 AS "energy" INTO "{rp_name}"."net_energy_{duration}" FROM "net" GROUP BY time({duration})''')
                    logger.debug(f"Created continuous query: cq_net_energy_{duration}")

            # Solar Power, Energy
            if 'cq_solar_power_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_solar_power_{duration}', f'SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."solar_power_{duration}" FROM "solar" GROUP BY time({duration})')
                    logger.debug(f"Created continuous query: cq_solar_power_{duration}")
            
            if 'cq_solar_energy_5m' not in existing_cqs:
                for duration, rp_name in retention_policies.items():
                    self.client.create_continuous_query(f'cq_solar_energy_{duration}', f'''SELECT integral("power") / 3600000 AS "energy" INTO "{rp_name}"."solar_energy_{duration}" FROM "solar" GROUP BY time({duration})''')
                    logger.debug(f"Created continuous query: cq_solar_energy_{duration}")

             # Individual CT Energies
            for chan in range(1, 7):
                if f'cq_ct{chan}_power_5m' not in existing_cqs:
                    for duration, rp_name in retention_policies.items():
                        self.client.create_continuous_query(f'cq_ct{chan}_power_{duration}', f'''SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."ct{chan}_power_{duration}" FROM "raw_cts" WHERE "ct" = '{chan}' GROUP BY time({duration})''')
                        logger.debug(f"Created continuous query: cq_ct{chan}_power_{duration}")

                # Individual CT Power, Energy
                if f'cq_ct{chan}_energy_5m' not in existing_cqs:
                    for duration, rp_name in retention_policies.items():
                        self.client.create_continuous_query(f'cq_ct{chan}_energy_{duration}', f'''SELECT integral("power") / 3600000 AS "energy" INTO "{rp_name}"."ct{chan}_energy_{duration}" FROM "raw_cts" WHERE "ct" = '{chan}' GROUP BY time({duration})''')
                        logger.debug(f"Created continuous query: cq_ct{chan}_energy_{duration}")

        except Exception as e:
            logger.error(f"Failed to create one or more continuous queries. Message: {e}")
        
        return

    def _validate_rps(self) -> None:
        '''Ensures that the retention policies exist in the configured Influx v1 database, and creates them if not.'''

        # Validate retention policies and continuous queries.
        try:
            existing_rps = self.client.get_list_retention_policies()
            rp_names = [rp['name'] for rp in existing_rps]
        except Exception as e:
            logger.warning(f"Failed to retrieve InfluxDB Retention Policies. Is Influx running?")
            self._cleanup(-1)
        
        try:
            for rp in retention_policies.keys():
                if rp not in rp_names:
                    self.client.create_retention_policy(rp, retention_policies[rp]['duration'], 1, default = (True if rp == 'autogen' else False))
                    logger.debug(f"Created retention policy {rp}")
        except Exception as e:
            logger.warning("Failed to create one or more retention policies!")
        
        return

    def _validate_influx_v2_tasks(self, client, bucket, org_name, org_id) -> None:
        '''Ensures that the tasks to automatically downsample the measurements are created in InfluxDB'''
        
        task_api = client.tasks_api()
        existing_tasks = task_api.find_tasks()
        existing_tasks_by_name = {task.name : task for task in existing_tasks}
        existing_task_names = [task.name for task in existing_tasks]

        org_api = client.organizations_api()
        Org = org_api.find_organization(org_id)

        if 'powermon_high_res_downsample' not in existing_task_names:
            task = _add_task(task_api, 'powermon_high_res_downsample', 'high-res-5m-downsample', bucket, org_name, org_id, Org)

        if 'powermon_calculate_5m_energy' not in existing_task_names:
            successful = _add_task(task_api, 'powermon_calculate_5m_energy', 'calculate-5m-energy', bucket, org_name, org_id, Org)

    def _validate_influx_v2_bucket(self, client, bucket, org) -> None:
        '''Ensures that the configured bucket name (and a bucket to hold the downsampled points created from tasks) is created.'''
        # Check for bucket and try to create if it doesn't exist.
        bucket_api = client.buckets_api()
        existing_buckets = bucket_api.find_buckets()
        existing_buckets = [bucket.name for bucket in existing_buckets.buckets]
    
        downsample_bucket_name = f'{bucket}_downsampled'
        
        if bucket not in existing_buckets:
            logger.debug(f"  Creating bucket name {bucket} in InfluxDB v2 instance.")
            successful = self._create_influx_v2_bucket(bucket_api, bucket, org)
            if not successful:
                self._cleanup()

        if downsample_bucket_name not in existing_buckets:
            successful = self._create_influx_v2_bucket(bucket_api, downsample_bucket_name, org)
            if not successful:
                logger.warning(f"  Failed to create the bucket to hold downsampled data (named {downsample_bucket_name})")
                self._cleanup()
        
        

    def _load_config(self, config) -> None:
        '''Loads the provided config and validates contents.
        
        config can be either a os.path, string, or a dictionary.
        '''

        invalid_settings = False
        if isinstance(config, (pathlib.PosixPath, str)):
            logger.debug(f"Attempting to load config from {config}")            
            if not os.path.exists(config): 
                logger.error(f"Could not find your config.toml file at rpi_power_monitor/config.toml. Please ensure it exists, or, provide the config location with the -c flag when launching the program.")
            try:
                with open(config, 'rb') as f:
                    config = tomli.load(f)
            except FileNotFoundError:
                self._cleanup(-1)
            
            except tomli.TOMLDecodeError:
                logger.warning("The file config.toml appears to have a TOML syntax error. Please run the config through a TOML validator, make corrections, and try again.")
                self._cleanup(-1)
        
        elif isinstance(config, dict):
            logger.debug(f"Attempting to parse the provided config dictionary.")
            # Check for bare-minimum config keys:            
            if not config.get('current_transformers'):
                # `current_transformers` is required due to subsequent config processing that happens for each CT channel defined underneath the `current_transformers` key.
                logger.critical("Invalid config setting. Unable to find the required 'current_transformers' key in the config dict.")
                invalid_settings = True
            
            if not config.get('grid_voltage'):
                # `grid_voltage` is required due to subsequent config processing that happens for each CT channel defined underneath the `grid_voltage` key.
                logger.critical("Invalid config setting. Unable to find the required 'grid_voltager' key in the config dict.")
                invalid_settings = True
            
            if invalid_settings:
                self._cleanup(-1)

        self.config = config
        self.grid_voltage = config.get('grid_voltage').get('grid_voltage')
        self.ac_transformer_output_voltage = config.get('grid_voltage').get('ac_transformer_output_voltage')
        self.voltage_calibration = config.get('grid_voltage').get('voltage_calibration')
        self.name = config['general'].get('name')

        # Enabled Channels
        try:
            self.enabled_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['enabled'] ]
        except Exception as e:
            logger.warning("Invalid config setting. A CT channel is missing the 'enabled' configuration setting.")
            invalid_settings = True
        if len(self.enabled_channels) == 0:
            invalid_settings = True
            logger.warning("Invalid config setting: No channels have been enabled!")
        else:
            logger.debug(f"Sampling enabled for {len(self.enabled_channels)} channels.")
        
        ADC_CHANNELS = {
            1 : 0,  # PCB channel # : ADC channel #
            2 : 1,
            3 : 2,
            4 : 3,
            5 : 6,
            6 : 7
            }

        self.enabled_adc_ct_channels = {pcb_chan : adc_chan for pcb_chan, adc_chan in ADC_CHANNELS.items() if pcb_chan in self.enabled_channels}

        # CT Type Check
        for ct_channel, settings in config['current_transformers'].items():
            if settings['type'] not in ('consumption', 'production', 'mains'):
                logger.warning(f"Invalid config setting: 'type' for {ct_channel} should be 'consumption' or 'production', or 'mains'. It is currently set to: '{config['current_transformers'][ct_channel]['type']}'.")
                invalid_settings = True


        # Mains assignment
        self.mains_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'mains' and settings['enabled'] == True]
        if len(self.mains_channels) > 0:
            logger.debug(f"Identified mains channels: {self.mains_channels}")
        else:
            logger.debug("No mains channels configured.")

        if invalid_settings:
            logger.critical("Invalid settings detected in the provided configuration. Please review any warning messages above and correct the issue.")
            self._cleanup(-1)

        # Production sources assignment
        self.production_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'production' and settings['enabled'] == True]
        logger.debug(f"Identified {len(self.production_channels)} production channels: ({self.production_channels})")
    
        # Consumption sources assignment
        self.consumption_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'consumption' and settings['enabled'] == True]
        logger.debug(f"Identified {len(self.consumption_channels)} consumption channels: ({self.consumption_channels})")

        # CT Channel Settings Validation
        for channel, settings in config['current_transformers'].items():
            if 'rating' not in settings.keys():
                logger.warning(f"{channel.capitalize()} is missing the `rating` configuration. Please add the `rating` option to this channel in your configuration.")
                invalid_settings = True
            if 'two_pole' not in settings.keys():
                logger.debug(f"{channel.capitalize()} is missing the two_pole setting in the config. Using the default value of two_pole = False for {channel.capitalize()}")
                config['current_transformers'][channel]['two_pole'] = False


        # Optional Settings
        
        # Check for the config setting `disable_dup_process_check`. Set it to False if the config setting doesn't exist, or if it is already False/None.
        if not config.get('disable_dup_process_check'):
            config['disable_dup_process_check'] = False

        if invalid_settings:
            logger.critical("Invalid settings detected in the provided configuration. Please review any warning messages above and correct the issue.")
            self._cleanup(-1)
        
        return

    def _setup_influx_v1(self) -> None:
        '''Initializes a connection to Influx v1.'''

        from influxdb import InfluxDBClient    
        
        host = self.config['database']['host']
        port = self.config['database']['port']
        username = self.config['database']['username']
        password = self.config['database']['password']
        logger.debug(f"Trying to connect to the Influx database at {host}:{port}...")        

        try:
            client = InfluxDBClient(
                host=host,
                port=port,
                username=self.config['database']['username'],
                password=self.config['database']['password'],
                database=self.config['database']['database_name'],
                timeout=7,
                retries=2)
            self.client = client

        except Exception as e:
            logger.warning(f"Failed to connect to InfluxDB database at {host}:{port}")
            self.client = None
            self._cleanup(-1)

        # Test Client
        try:
            self.client.create_database(self.config['database']['database_name'])
        except ConnectionRefusedError:
            logger.warning("DB connection refused - is Influx running?")
            self._cleanup(-1)
        except Exception as e:
            logger.warning(f"Failed to connect to the Influx database at {host}:{port}.")
            logger.debug(f"Error message:\n{e}")
            self._cleanup(-1)
        
        logger.debug(f"Successfully connected to Influx at {host}:{port}")
        return

    def  _setup_influx_v2(self) -> None:
        '''Initializes a connection to Influx v2.'''
        
        import influxdb_client
        from influxdb_client.client.write_api import SYNCHRONOUS

        try:
            v2_config = self.config.get('database').get('influx_v2')
        except Exception as e:
            logger.warning(f"Failed to load Influx v2 configuration.")
            return

        bucket = v2_config.get('bucket')
        org = v2_config.get('org')
        token = v2_config.get('token')
        url = v2_config.get('url')

        if not (bucket and org and token and url):
            logger.warning(f"Influx version 2 is specified, but you're missing one or more Influx v2 config options.")
            logger.warning(f"Please ensure your [database.influx_v2] includes the bucket, org, token, and url options.")
            self.client = None
            return

        client = influxdb_client.InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)
        self.client = write_api
        self.influx_bucket = bucket
        
        # Create Tasks, which require the Org ID associated with this org.
        org_id = self._get_influx_v2_org_id(client, org)
        if not org_id:
            self._cleanup()
        
        self._validate_influx_v2_bucket(client, bucket, org)
        self._validate_influx_v2_tasks(client, bucket, org, org_id)        
        
        logger.debug("Influx version 2 database checks/setup complete.")

    def _create_influx_v2_bucket(self, bucket_api, bucket_name, org):
        '''Creates the bucket `bucket_name` via the provided `bucket_api`'''
        
        try:
            bucket_api.create_bucket(bucket_name=bucket_name, org=org)
            return True
        except Exception as e:
            logger.warning("  Influx v2 - there was a problem when creating the bucket. Message:")
            logger.warning(e)
            logger.info("Please review the above message and either: ")
            logger.info(f"  - Investigate why the requested bucket name ({bucket_name}) cannot be used, or")
            logger.info("  - Change the bucket name in your configuration.")
            return False
    
    def _get_influx_v2_org_id(self, client, org) -> str:
        '''Retrieves the Org ID (needed for creating Tasks) associated with the provided Organization name.'''

        from influxdb_client.rest import ApiException
        
        org_api = client.organizations_api()
        try:
            this_org = org_api.find_organizations(org=org)
            org_id = this_org[0].id
            return org_id
                        
        # The InfluxDB library raises an exception to indicate HTTP 404 not found. Odd, but okay.
        except ApiException:
            logger.warning(f"Unable to get Organization ID associated with the Organization {org}. (Is your InfluxDB instance)")
            return None
        
        
        
    def _build_write_wrapper(self, influx_version) -> None:
        '''This is a wrapper function that abstracts the InfluxDB write API based on the Influx version specified.
        
        The RPiPowerMonitor class should already have self.client defined if Influx is going to be used (via _setup_influx_v# functions).
        
        This function simply creates a writer function to work with either the V1 or V2 influx client libraries.
        The writer function is responsible for accepting the batch of data and getting into the configured InfluxDB instance.
        '''
        
        def _rpi_influx_v1_writer(*args, **kwargs) -> None:
            '''This function wraps the InfluxDB v2 client libary to present a common Influx interface to the RPI Power Monitor.
            
            Note that the datapoints come from the class attribute self.points_buffer.
            
            Calling this function will write the points to the configured InfluxDB instance.
            '''

            try:
                self.client.write_points(self.points_buffer, time_precision='ms')
            except ConnectionError:
                logger.warning(f'Failed to write data to Influx. Reason: {e}')
        
        def _rpi_influx_v2_writer(*args, **kwargs) -> None:
            '''This function wraps the InfluxDB v2 client libary to present a common Influx interface to the RPI Power Monitor.
            
            Note that the datapoints come from the class attribute self.points_buffer.
            
            Calling this function will write the points to the configured InfluxDB instance.
            '''
            
            # Note that self.client, for Influx v2, is an Influx client.write_api instance.
            try:
                self.client.write(self.influx_bucket, record=self.points_buffer)
            except Exception as e:
                logger.warning(f"There was a problem writing data to InfluxDB v2. The exception message is: ")
                logger.warning(e)
            
        if influx_version == 1 or influx_version == None:
            self.influx_writer = _rpi_influx_v1_writer
            
        elif influx_version == 2:
            self.influx_writer = _rpi_influx_v2_writer

    def _get_db_client(self) -> None:
        '''Creates an InfluxDB Client using the loaded configuration.'''

        influx_version = self.config['database'].get('influx_version')

        # The `influx_version` config setting will not exist on pre-v0.4.x deployments.
        # In this case, assume Influx version 1 is expected.
        if influx_version == 2:
            self._setup_influx_v2()

        else:
            self._setup_influx_v1()
            # Other Initializations
            # Validate continuous queries and retention policies
            self._validate_rps()
            self._validate_cqs()
        
        self._build_write_wrapper(influx_version)

    def _dump_data(self, dump_type, samples) -> None:
        """ Writes raw data to a CSV file titled 'data-dump-<current_time>.csv' """
        speed_kHz = self.spi.max_speed_hz / 1000
        now = datetime.now().strftime('%m-%d-%Y-%H-%M')
        filename = f'data-dump-{now}.csv'
        with open(filename, 'w') as f:
            headers = ["Sample#", "ct1", "ct2", "ct3", "ct4", "ct5", "ct6", "voltage"]
            writer = csv.writer(f)
            writer.writerow(headers)
            # samples contains lists for each data sample.
            for i in range(0, len(samples[0])):
                ct1_data = samples[0]
                ct2_data = samples[1]
                ct3_data = samples[2]
                ct4_data = samples[3]
                ct5_data = samples[4]
                ct6_data = samples[5]
                v_data = samples[-1]
                writer.writerow([i, ct1_data[i], ct2_data[i], ct3_data[i], ct4_data[i], ct5_data[i], ct6_data[i], v_data[i]])
        logger.info(f"CSV written to {filename}.")

    def _get_board_voltage(self) -> float:
        """ Take 10 sample readings and return the average board voltage from the +3.3V rail. """
        samples = []
        while len(samples) <= 10:
            data = self._read_adc(4) # channel 4 is the 3.3V ref voltage
            samples.append(data)

        avg_reading = sum(samples) / len(samples)
        board_voltage = (avg_reading / 1024) * 3.31 * 2
        return board_voltage

    def _read_adc(self, adc_num) -> int:
        """ Read SPI data from the MCP3008, 8 channels in total. """
        r = self.spi.xfer2([1, 8 + adc_num << 4, 0])
        data = ((r[1] & 3) << 8) + r[2]
        return data

    def _collect_data(self, num_samples, channel_num=None) -> dict:
        """  Takes <num_samples> readings from the ADC for each ADC channel and returns a dictionary containing the CT channel number as the key, and a list of that channel's sample data.
        
        Arguments:
          - num_samples:    int, the number of samples to collect for each channel.
          - channel_num:    int|None, a specific channel to sample from. If None, all currently enabled channels (according to the config) will be sampled.

        Returns a dictionary where the keys are ct1 - ct6, voltage, and time, and the value of each key is a list of that channel's samples (except for 'time', which is a UTC datetime)
        """
        now = datetime.now(timezone.utc) # Get time of reading

        samples = dict()
        if channel_num:
            samples[f'ct{channel_num}'] = []
            samples[f'v{channel_num}'] = []
            start = timeit.default_timer()
            for _ in range(num_samples):
                samples[f'ct{channel_num}'].append(self._read_adc(channel_num))
                samples[f'v{channel_num}'].append(self._read_adc(5))
            stop = timeit.default_timer()
            duration = stop - start
        else:
            for pcb_chan in self.enabled_channels:
                samples[f'ct{pcb_chan}'] = []
                samples[f'v{pcb_chan}'] = []

            start = timeit.default_timer()
            for _ in range(num_samples):
                for pcb_chan, adc_chan in self.enabled_adc_ct_channels.items():
                    samples[f'ct{pcb_chan}'].append(self._read_adc(adc_chan))
                    samples[f'v{pcb_chan}'].append(self._read_adc(5))
            stop = timeit.default_timer()
            duration = stop - start
       
        samples['time'] = now
        samples['duration'] = duration
        return samples
    

    def get_single_channel_measurements(self, channel=None, duration=1) -> dict:
        """ (Added in v0.4.0) User-level interface to sample a single channel for an approximate number of seconds.
        
        Arguments:
          - channel_num:    int, the channel number that you want to sample (1-6)
          - duration:       int|float, the number of seconds that you want to sample for. (Default is 1 second)
        """

        # The number of samples collected over N seconds is relative to the number of enabled channels and the overall sample rate. The approximate number of samples
        # collected in `duration` seconds must first be calculated below before calling _collect_data()`
        
        if not channel:
            print("You must provide a channel when calling this function. Example:\n")
            print("rpm.get_single_channel_measurements(channel=1)")
            return None
        num_samples = _convert_duration_to_num_samples(duration, self.sample_rate, 1)
        samples = self._collect_data(num_samples, channel_num=channel)
        results = self._calculate_power(samples, self._get_board_voltage())
        return results

    def get_power_measurements(self, duration=1) -> dict:
        """ (Added in v0.4.0) User-level interface to sample all enabled channels for an approximate number of seconds.
        
        Arguments:
          - duration:   int, the number of seconds that you want to sample for. (Default is 1 second)
        """
        
        enabled_channels = self.enabled_channels
        num_samples = _convert_duration_to_num_samples(duration, self.sample_rate, 1)
        samples = self._collect_data(num_samples)
        results = self._calculate_power(samples, self._get_board_voltage())
        return results
        


    def _calculate_power(self, samples, board_voltage) -> dict:
        """ Calculates amperage, real power, power factor, and voltage
        
        Arguments:
          - samples: dict, a dictionary containing lists of each channel's sample data, and a voltage wave that's been collected for each corresponding channel.

        Returns a dictionary containing a dictionary for each channel, with the following structure:
        {
            'ct1': {
                'type': 'consumption',
                'power': <Real Power (float) for this channel>,
                'current': <RMS Current (float) for this channel>,
                'voltage': <RMS Voltage (float)>,
                'pf': <Power Factor (float) for this channel>
            },
            ... ,
            'ct6' : { ... }
        }
        """
        ct1_samples = samples.get('ct1')        # current samples for ct1
        ct2_samples = samples.get('ct2')        # current samples for ct2
        ct3_samples = samples.get('ct3')        # current samples for ct3
        ct4_samples = samples.get('ct4')        # current samples for ct4
        ct5_samples = samples.get('ct5')        # current samples for ct5
        ct6_samples = samples.get('ct6')        # current samples for ct6
        v_samples_1 = samples.get('v1')      # voltage wave specifically for ct1
        v_samples_2 = samples.get('v2')      # voltage wave specifically for ct2
        v_samples_3 = samples.get('v3')      # voltage wave specifically for ct3
        v_samples_4 = samples.get('v4')      # voltage wave specifically for ct4
        v_samples_5 = samples.get('v5')      # voltage wave specifically for ct5
        v_samples_6 = samples.get('v6')      # voltage wave specifically for ct6

        # Variable Initialization
        sum_inst_power_ct1 = 0
        sum_inst_power_ct2 = 0
        sum_inst_power_ct3 = 0
        sum_inst_power_ct4 = 0
        sum_inst_power_ct5 = 0
        sum_inst_power_ct6 = 0
        sum_squared_current_ct1 = 0
        sum_squared_current_ct2 = 0
        sum_squared_current_ct3 = 0
        sum_squared_current_ct4 = 0
        sum_squared_current_ct5 = 0
        sum_squared_current_ct6 = 0
        sum_raw_current_ct1 = 0
        sum_raw_current_ct2 = 0
        sum_raw_current_ct3 = 0
        sum_raw_current_ct4 = 0
        sum_raw_current_ct5 = 0
        sum_raw_current_ct6 = 0
        sum_squared_voltage_1 = 0
        sum_squared_voltage_2 = 0
        sum_squared_voltage_3 = 0
        sum_squared_voltage_4 = 0
        sum_squared_voltage_5 = 0
        sum_squared_voltage_6 = 0
        sum_raw_voltage_1 = 0
        sum_raw_voltage_2 = 0
        sum_raw_voltage_3 = 0
        sum_raw_voltage_4 = 0
        sum_raw_voltage_5 = 0
        sum_raw_voltage_6 = 0

        # Scaling factors
        vref = board_voltage / 1024
        ct1_scaling_factor = vref * self.config['current_transformers']['channel_1']['calibration'] * int(self.config['current_transformers']['channel_1']['rating']) * self.def_cal
        ct2_scaling_factor = vref * self.config['current_transformers']['channel_2']['calibration'] * int(self.config['current_transformers']['channel_2']['rating']) * self.def_cal
        ct3_scaling_factor = vref * self.config['current_transformers']['channel_3']['calibration'] * int(self.config['current_transformers']['channel_3']['rating']) * self.def_cal
        ct4_scaling_factor = vref * self.config['current_transformers']['channel_4']['calibration'] * int(self.config['current_transformers']['channel_4']['rating']) * self.def_cal
        ct5_scaling_factor = vref * self.config['current_transformers']['channel_5']['calibration'] * int(self.config['current_transformers']['channel_5']['rating']) * self.def_cal
        ct6_scaling_factor = vref * self.config['current_transformers']['channel_6']['calibration'] * int(self.config['current_transformers']['channel_6']['rating']) * self.def_cal
        ac_voltage_ratio = (self.grid_voltage / self.ac_transformer_output_voltage) * 11  # Rough approximation
        voltage_scaling_factor = vref * ac_voltage_ratio * self.voltage_calibration

        # Get the number of samples by checking the length of one of the sample buffers.
        for chan_num in range(1, 7):
            if f'ct{chan_num}' in samples.keys():
                num_samples = len(samples[f'ct{chan_num}'])
                break

        for i in range(0, num_samples):
            if ct1_samples:
                ct1 = (int(ct1_samples[i]))
                voltage_1 = (int(v_samples_1[i]))
                sum_raw_current_ct1 += ct1
                sum_raw_voltage_1 += voltage_1
                inst_power_ct1 = ct1 * voltage_1
                sum_inst_power_ct1 += inst_power_ct1
                squared_voltage_1 = voltage_1 * voltage_1
                sum_squared_voltage_1 += squared_voltage_1
                sq_ct1 = ct1 * ct1
                sum_squared_current_ct1 += sq_ct1
                

            if ct2_samples:
                ct2 = (int(ct2_samples[i]))
                voltage_2 = (int(v_samples_2[i]))
                sum_raw_current_ct2 += ct2
                sum_raw_voltage_2 += voltage_2
                inst_power_ct2 = ct2 * voltage_2
                sum_inst_power_ct2 += inst_power_ct2
                squared_voltage_2 = voltage_2 * voltage_2
                sum_squared_voltage_2 += squared_voltage_2
                sq_ct2 = ct2 * ct2
                sum_squared_current_ct2 += sq_ct2
                

            if ct3_samples:
                ct3 = (int(ct3_samples[i]))
                voltage_3 = (int(v_samples_3[i]))
                sum_raw_current_ct3 += ct3
                sum_raw_voltage_3 += voltage_3
                inst_power_ct3 = ct3 * voltage_3
                sum_inst_power_ct3 += inst_power_ct3
                squared_voltage_3 = voltage_3 * voltage_3
                sum_squared_voltage_3 += squared_voltage_3
                sq_ct3 = ct3 * ct3
                sum_squared_current_ct3 += sq_ct3
                

            if ct4_samples:
                ct4 = (int(ct4_samples[i]))
                voltage_4 = (int(v_samples_4[i]))
                sum_raw_current_ct4 += ct4
                sum_raw_voltage_4 += voltage_4
                inst_power_ct4 = ct4 * voltage_4
                sum_inst_power_ct4 += inst_power_ct4
                squared_voltage_4 = voltage_4 * voltage_4
                sum_squared_voltage_4 += squared_voltage_4
                sq_ct4 = ct4 * ct4
                sum_squared_current_ct4 += sq_ct4
                

            if ct5_samples:
                ct5 = (int(ct5_samples[i]))
                voltage_5 = (int(v_samples_5[i]))
                sum_raw_current_ct5 += ct5
                sum_raw_voltage_5 += voltage_5
                inst_power_ct5 = ct5 * voltage_5
                sum_inst_power_ct5 += inst_power_ct5
                squared_voltage_5 = voltage_5 * voltage_5
                sum_squared_voltage_5 += squared_voltage_5
                sq_ct5 = ct5 * ct5
                sum_squared_current_ct5 += sq_ct5
                

            if ct6_samples:
                ct6 = (int(ct6_samples[i]))
                voltage_6 = (int(v_samples_6[i]))
                sum_raw_current_ct6 += ct6
                sum_raw_voltage_6 += voltage_6
                inst_power_ct6 = ct6 * voltage_6
                sum_inst_power_ct6 += inst_power_ct6
                squared_voltage_6 = voltage_6 * voltage_6
                sum_squared_voltage_6 += squared_voltage_6
                sq_ct6 = ct6 * ct6
                sum_squared_current_ct6 += sq_ct6

        results = dict()

        if ct1_samples:
            avg_raw_current_ct1 = sum_raw_current_ct1 / num_samples
            avg_raw_voltage_1 = sum_raw_voltage_1 / num_samples
            real_power_1 = ((sum_inst_power_ct1 / num_samples) - (avg_raw_current_ct1 * avg_raw_voltage_1))  * ct1_scaling_factor * voltage_scaling_factor
            mean_square_current_ct1 = sum_squared_current_ct1 / num_samples
            mean_square_voltage_1 = sum_squared_voltage_1 / num_samples
            rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
            rms_voltage_1 = sqrt(mean_square_voltage_1 - (avg_raw_voltage_1 * avg_raw_voltage_1)) * voltage_scaling_factor
            apparent_power_1 = rms_voltage_1 * rms_current_ct1
            try:
                power_factor_1 = real_power_1 / apparent_power_1
                power_factor_1 = abs(power_factor_1)
            except ZeroDivisionError:
                power_factor_1 = 0
            if self.config['current_transformers']['channel_1']['two_pole']:
                real_power_1 = real_power_1 * 2
            if self.config['current_transformers']['channel_1'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_1 = real_power_1 * -1
            if real_power_1 < 0:
                rms_current_ct1 = abs(rms_current_ct1) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct1_samples) - min(ct1_samples)
            if delta < self.PF_DELTA:
                power_factor_1 = 0
                
            results[1] = {
                'type': self.config['current_transformers']['channel_1']['type'],
                'power': real_power_1,
                'current': rms_current_ct1,
                'pf': power_factor_1
            }
            results['voltage'] = rms_voltage_1

        if ct2_samples:
            avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
            avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
            real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor
            mean_square_current_ct2 = sum_squared_current_ct2 / num_samples
            mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
            rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
            rms_voltage_2 = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
            apparent_power_2 = rms_voltage_2 * rms_current_ct2
            try:
                power_factor_2 = real_power_2 / apparent_power_2
                power_factor_2 = abs(power_factor_2)
            except ZeroDivisionError:
                power_factor_2 = 0
            if self.config['current_transformers']['channel_2']['two_pole']:
                real_power_2 = real_power_2 * 2
            if self.config['current_transformers']['channel_2'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_2 = real_power_2 * -1
            if real_power_2 < 0:
                rms_current_ct2 = abs(rms_current_ct2) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct2_samples) - min(ct2_samples)
            if delta < self.PF_DELTA:
                power_factor_2 = 0
                
            results[2] = {
                'type': self.config['current_transformers']['channel_2']['type'],
                'power': real_power_2,
                'current': rms_current_ct2,
                'pf': power_factor_2
            }
            results['voltage'] = rms_voltage_2

        if ct3_samples:
            avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
            avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
            real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor
            mean_square_current_ct3 = sum_squared_current_ct3 / num_samples
            mean_square_voltage_3 = sum_squared_voltage_3 / num_samples
            rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
            rms_voltage_3 = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor
            apparent_power_3 = rms_voltage_3 * rms_current_ct3
            try:
                power_factor_3 = real_power_3 / apparent_power_3
                power_factor_3 = abs(power_factor_3)
            except ZeroDivisionError:
                power_factor_3 = 0
            if self.config['current_transformers']['channel_3']['two_pole']:
                real_power_3 = real_power_3 * 2
            if self.config['current_transformers']['channel_3'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_3 = real_power_3 * -1
            if real_power_3 < 0:
                rms_current_ct3 = abs(rms_current_ct3) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct3_samples) - min(ct3_samples)
            if delta < self.PF_DELTA:
                power_factor_3 = 0
                
            results[3] = {
                'type': self.config['current_transformers']['channel_3']['type'],
                'power': real_power_3,
                'current': rms_current_ct3,                
                'pf': power_factor_3
            }
            results['voltage'] = rms_voltage_3

        if ct4_samples:
            avg_raw_current_ct4 = sum_raw_current_ct4 / num_samples
            avg_raw_voltage_4 = sum_raw_voltage_4 / num_samples
            real_power_4 = ((sum_inst_power_ct4 / num_samples) - (avg_raw_current_ct4 * avg_raw_voltage_4))  * ct4_scaling_factor * voltage_scaling_factor
            mean_square_current_ct4 = sum_squared_current_ct4 / num_samples
            mean_square_voltage_4 = sum_squared_voltage_4 / num_samples
            rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor
            rms_voltage_4 = sqrt(mean_square_voltage_4 - (avg_raw_voltage_4 * avg_raw_voltage_4)) * voltage_scaling_factor
            apparent_power_4 = rms_voltage_4 * rms_current_ct4
            try:
                power_factor_4 = real_power_4 / apparent_power_4
                power_factor_4 = abs(power_factor_4)
            except ZeroDivisionError:
                power_factor_4 = 0
            if self.config['current_transformers']['channel_4']['two_pole']:
                real_power_4 = real_power_4 * 2
            if self.config['current_transformers']['channel_4'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_4 = real_power_4 * -1
            if real_power_4 < 0:
                rms_current_ct4 = abs(rms_current_ct4) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct4_samples) - min(ct4_samples)
            if delta < self.PF_DELTA:
                power_factor_4 = 0
                
            results[4] = {
                'type': self.config['current_transformers']['channel_4']['type'],
                'power': real_power_4,
                'current': rms_current_ct4,
                'pf': power_factor_4
            }
            results['voltage'] = rms_voltage_4

        if ct5_samples:
            avg_raw_current_ct5 = sum_raw_current_ct5 / num_samples
            avg_raw_voltage_5 = sum_raw_voltage_5 / num_samples
            real_power_5 = ((sum_inst_power_ct5 / num_samples) - (avg_raw_current_ct5 * avg_raw_voltage_5))  * ct5_scaling_factor * voltage_scaling_factor
            mean_square_current_ct5 = sum_squared_current_ct5 / num_samples
            mean_square_voltage_5 = sum_squared_voltage_5 / num_samples
            rms_current_ct5 = sqrt(mean_square_current_ct5 - (avg_raw_current_ct5 * avg_raw_current_ct5)) * ct5_scaling_factor
            rms_voltage_5 = sqrt(mean_square_voltage_5 - (avg_raw_voltage_5 * avg_raw_voltage_5)) * voltage_scaling_factor
            apparent_power_5 = rms_voltage_5 * rms_current_ct5
            try:
                power_factor_5 = real_power_5 / apparent_power_5
                power_factor_5 = abs(power_factor_5)
            except ZeroDivisionError:
                power_factor_5 = 0
            if self.config['current_transformers']['channel_5']['two_pole']:
                real_power_5 = real_power_5 * 2
            if self.config['current_transformers']['channel_5'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_5 = real_power_5 * -1
            if real_power_5 < 0:
                rms_current_ct5 = abs(rms_current_ct5) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct5_samples) - min(ct5_samples)
            if delta < self.PF_DELTA:
                power_factor_5 = 0
                
            results[5] = {
                'type': self.config['current_transformers']['channel_5']['type'],
                'power': real_power_5,
                'current': rms_current_ct5,
                'pf': power_factor_5
            }
            results['voltage'] = rms_voltage_5

        if ct6_samples:
            avg_raw_current_ct6 = sum_raw_current_ct6 / num_samples
            avg_raw_voltage_6 = sum_raw_voltage_6 / num_samples
            real_power_6 = ((sum_inst_power_ct6 / num_samples) - (avg_raw_current_ct6 * avg_raw_voltage_6))  * ct6_scaling_factor * voltage_scaling_factor
            mean_square_current_ct6 = sum_squared_current_ct6 / num_samples
            mean_square_voltage_6 = sum_squared_voltage_6 / num_samples
            rms_current_ct6 = sqrt(mean_square_current_ct6 - (avg_raw_current_ct6 * avg_raw_current_ct6)) * ct6_scaling_factor
            rms_voltage_6 = sqrt(mean_square_voltage_6 - (avg_raw_voltage_6 * avg_raw_voltage_6)) * voltage_scaling_factor
            apparent_power_6 = rms_voltage_6 * rms_current_ct6
            try:
                power_factor_6 = real_power_6 / apparent_power_6
                power_factor_6 = abs(power_factor_6)
            except ZeroDivisionError:
                power_factor_6 = 0        
            if self.config['current_transformers']['channel_6']['two_pole']:
                real_power_6 = real_power_6 * 2
            if self.config['current_transformers']['channel_6'].get('reversed'):
                # Change the sign of the power calculation, and then make the current calculation match.
                real_power_6 = real_power_6 * -1
            if real_power_6 < 0:
                rms_current_ct6 = abs(rms_current_ct6) * -1

            # Filter out PF if the amperage data is not sufficient.
            delta = max(ct6_samples) - min(ct6_samples)
            if delta < self.PF_DELTA:
                power_factor_6 = 0
                
            results[6] = {
                'type': self.config['current_transformers']['channel_6']['type'],
                'power': real_power_6,
                'current': rms_current_ct6,
                'pf': power_factor_6
            }
            results['voltage'] = rms_voltage_6

        # Software Noise Filtering - Amps & Watts
        # amps_cutoff_threshold (added in v0.3.2)
        #   When the amperage reading falls below the specified value, all readings for the channel will be ignored.
        #   `amps_cutoff_threshold` is preferred - `watts_cutoff_threshold` is deprecated as of v0.3.2 and will be removed in a future release.
        #   `watts_cutoff_threshold` will be ignored if `amps_cutoff_threshold` is specified.
    
    
        # Check to see if amps_cutoff_threshold is defined in the config. If not, fallback to using watts_cutoff_threshold.
        for chan_num in results.keys():
            if chan_num in self.enabled_channels:
                if self.config['current_transformers'][f'channel_{chan_num}'].get('amps_cutoff_threshold'):
                    cutoff = float(self.config['current_transformers'][f'channel_{chan_num}']['amps_cutoff_threshold'])
                else:
                    cutoff = 0
                    
                if cutoff != 0:
                    if abs(results[chan_num]['power']) < cutoff:
                        results[chan_num]['power'] = 0
                        results[chan_num]['current'] = 0
                        results[chan_num]['pf'] = 0
        return results
    
    def run_main(self) -> None:
        """ Starts the main power monitor loop and launches plugins. """
        logger.info("... Starting Raspberry Pi Power Monitor")
        logger.info("Press Ctrl-c to quit...")
        # The following empty dictionaries will hold the respective calculated values at the end
        # of each polling cycle, which are then averaged prior to storing the value to the DB.
        production_values = dict(power=[], pf=[], current=[])
        home_consumption_values = dict(power=[], pf=[], current=[])
        net_values = dict(power=[], current=[])
        ct_dict = {channel : {'power' : [], 'pf' : [], 'current' : []} for channel in self.enabled_channels}
        rms_voltages = []
        SMA_Data = {channel : {'power' : [], 'pf' : [], 'current' : []} for channel in self.enabled_channels}
        # Add 'production', 'home-consumption', and 'net' figures to the SMA_Data dictionary:
        SMA_Data.update({
            'cts' : ct_dict,
            'production' : {'power' : [], 'pf': [], 'current': []},
            'home-consumption' : {'power': [], 'current': []},
            'net' : {'power': [], 'current': []},
            'voltage' : [],
            })
        SMA_Values = {
            'cts' : deepcopy(ct_dict),
            'production' : {'power' : None, 'pf' : None, 'current' : None},
            'home-consumption' : {'power' : None, 'current' : None},
            'net' : {'power' : None, 'current' : None},
            'voltage' : None
        }
        SMA_Window = 2      # This is the total number of calculations that are included in the simple-moving-average.
        write_threshold = 2 # This controls how many SMA_Data updates are processed before the resulting simple-moving-average values are sent to be stored in the database.
        write_threshold_counter = 0 # Counter that keeps track of the number of SMA updates processed. When write_threshold_counter == write_threshold, the current SMA values will be sent to influx DB cache for eventual storage.
        num_samples = 500

        # Start plugins that have been imported.
        if len(self.imported_plugins.keys()) > 0:
            self.result_manager = Manager()
            self.latest_results = self.result_manager.dict()

            for plugin_name, plugin in self.imported_plugins.items():
                plugin['plugin'].start(self.latest_results)
        
        else:
            self.latest_results = dict()


        # Get the expected sample count for the current configuration.
        samples = self._collect_data(num_samples)
        sample_count = sum([len(samples[x]) for x in samples.keys() if type(samples[x]) == list])
        
        while not self._halt_flag.is_set():
            board_voltage = self._get_board_voltage()
            samples = self._collect_data(num_samples)
            poll_time = samples['time']
            duration = samples['duration']
            sample_rate = round((sample_count / duration) / num_samples, 2)
            per_channel_sample_rate = round(sample_rate / (2 * len(self.enabled_channels)), 2)

            results = self._calculate_power(samples, board_voltage)
            voltage = results.pop('voltage')
            

            # Determine Production, Home Consumption, and Net Values
            
            # Home Consumption
            # Home consumption power is the total power that the home is using. This is typically the mains plus the production sources. 
            # However, if you haven't setup any mains channels in config.toml, this will be the sum of all 'consumption' channels + 'production' channels
            home_consumption_power = 0
            home_consumption_current = 0
            if len(self.mains_channels) == 0:   # No mains have been configured, so sum all channels with type == consumption
                for chan_num in self.consumption_channels:
                    home_consumption_power += results[chan_num]['power']
                    home_consumption_current += results[chan_num]['current']
            else:   # Mains have been configured, so sum them and subtract (rather, add the negative) production sources.
                for chan_num in self.mains_channels:
                    home_consumption_power += results[chan_num]['power']
                    home_consumption_current += results[chan_num]['current']
                for chan_num in self.production_channels:
                    home_consumption_power += results[chan_num]['power']
                    if self.config['current_transformers'][f'channel_{chan_num}']['two_pole']:
                        home_consumption_current += ( 2 * results[chan_num]['current'])
                    else:
                        home_consumption_current += results[chan_num]['current']

            # Production
            # Find the total power and current from all production sources.
            production_power = 0
            production_current = 0
            production_pf = 0   # Average power factor from all production sources

            for chan_num in self.production_channels:                    
                production_power += results[chan_num]['power']
                production_current += results[chan_num]['current']
                production_pf += results[chan_num]['pf']
            
            # Average the production power factor
            if len(self.production_channels) > 0:
                production_pf = production_pf / len(self.production_channels)

            # Net
            net_power = 0
            net_current = 0
            if len(self.mains_channels) == 0:
                net_power = home_consumption_power
                net_current = home_consumption_current
            else:
                for chan_num in self.mains_channels:
                    net_power += results[chan_num]['power']
                    net_current += results[chan_num]['current']                
                
            if net_power < 0:
                current_status = "Producing"
            else:
                current_status = "Consuming"


            # Initial SMA Construction
            if len(SMA_Data['cts'][self.enabled_channels[0]]['power']) < SMA_Window:
                for chan in results.keys():
                    for figure, value in results[chan].items():
                        if figure != 'type':
                            SMA_Data['cts'][chan][figure].append(value)
                
                # Voltage, Net, Home Power, and Production SMAs
                SMA_Data['voltage'].append(voltage)
                SMA_Data['home-consumption']['power'].append(home_consumption_power)
                SMA_Data['home-consumption']['current'].append(home_consumption_current)
                SMA_Data['net']['power'].append(net_power)
                SMA_Data['net']['current'].append(net_current)
                SMA_Data['production']['power'].append(production_power)
                SMA_Data['production']['current'].append(production_current)
                SMA_Data['production']['pf'].append(production_pf)
            
            else:
                for chan in results.keys():
                    for figure, value in results[chan].items():
                        if figure != 'type': 
                            SMA_Data['cts'][chan][figure].pop(0)
                            SMA_Data['cts'][chan][figure].append(value)
                
                SMA_Data['voltage'].pop(0)
                SMA_Data['home-consumption']['power'].pop(0)
                SMA_Data['home-consumption']['current'].pop(0)
                SMA_Data['net']['power'].pop(0)
                SMA_Data['net']['current'].pop(0)
                SMA_Data['production']['power'].pop(0)
                SMA_Data['production']['current'].pop(0)
                SMA_Data['production']['pf'].pop(0)

                SMA_Data['voltage'].append(voltage)
                SMA_Data['home-consumption']['power'].append(home_consumption_power)
                SMA_Data['home-consumption']['current'].append(home_consumption_current)
                SMA_Data['net']['power'].append(net_power)
                SMA_Data['net']['current'].append(net_current)
                SMA_Data['production']['power'].append(production_power)
                SMA_Data['production']['current'].append(production_current)
                SMA_Data['production']['pf'].append(production_pf)

                # Calculate SMA
                for chan in SMA_Data['cts'].keys():
                    for figure, values in SMA_Data['cts'][chan].items():
                        SMA_Values['cts'][chan][figure] = sum(values) / len(values)
                
                for summary_figure in ('home-consumption', 'net', 'production'):
                    try:
                        for measurement, values in SMA_Data[summary_figure].items():
                            SMA_Values[summary_figure][measurement] = sum(values) / len(values)
                    except ZeroDivisionError:
                        SMA_Values[summary_figure][measurement] = 0
                    
                # Update Voltage SMA separately since it is not a dictionary.
                SMA_Values['voltage'] = sum(SMA_Data['voltage']) / len(SMA_Data['voltage'])
            
                # Determine if the system is net producing or net consuming right now by looking at the panel mains.
                # Since the current measured is always positive,
                # we need to add a negative sign to the amperage value if we're exporting power.
                for chan_num in self.mains_channels:
                    # Only change the sign on the current field if it doesn't match the sign of the real power measurement.
                    if SMA_Values['cts'][chan_num]['power'] < 0 and SMA_Values['cts'][chan_num]['current'] > 0:
                        SMA_Values['cts'][chan_num]['current'] = SMA_Values['cts'][chan_num]['current'] * -1

                # Prepare values for database storage if DB is enabled.
                if self.DB_ENABLED:
                    if write_threshold_counter == write_threshold:
                        self._queue_for_influx(SMA_Values, poll_time)
                        write_threshold_counter = 0
                    else:
                        write_threshold_counter += 1

                # Expose data to plugins
                self.latest_results.update(SMA_Values)

                if self.terminal_mode:
                    self.print_results(SMA_Values, sample_rate)

        # _halt flag set
        self._cleanup()

    def _queue_for_influx(self, SMA_Values, poll_time) -> None:
        '''Creates Point() objects from the measured values, and caches them into a small batch before writing to Influx.'''

        # Create Points() for every measurement.
        ct_points = []
        for chan_num in self.enabled_channels:
            values = SMA_Values['cts'][chan_num]
            ct_points.append(Point('ct', num=chan_num, power=values['power'], current=values['current'], pf=values['pf'], time=poll_time, name=self.name)._to_dict())

        home_load = Point('home_load', power=SMA_Values['home-consumption']['power'], current=SMA_Values['home-consumption']['current'], time=poll_time, name=self.name)
        production = Point('solar', power=SMA_Values['production']['power'], current=SMA_Values['production']['current'], pf=SMA_Values['production']['pf'], time=poll_time, name=self.name)
        net = Point('net', power=SMA_Values['net']['power'], current=SMA_Values['net']['current'], time=poll_time, name=self.name)
        v = Point('voltage', voltage=SMA_Values['voltage'], v_input=0, time=poll_time, name=self.name)

        points = [
            home_load._to_dict(),
            production._to_dict(),
            net._to_dict(),
            v._to_dict(),
        ]
        points += ct_points

        self.points_buffer += points
        batch_size = 25
        if len(self.points_buffer) >= batch_size:
            self.influx_writer()
            self.points_buffer = []


    def _check_dup_process(self, *args, **kwargs) -> bool:
        '''Checks the host to see if the power monitor is already running in a separate process.
        
        Returns True if a duplicate process is found.
        Returns False if no duplicate process is found, or if the environment POWERMON_DEBUG is set to True.
        '''

        if os.getenv("POWERMON_DEBUG"):
            logger.debug("Environment variable POWERMON_DEBUG is True - skipping duplicate copy check.")
            return False

        # Check to see if there is already a power monitor process running.
        c = subprocess.run('sudo systemctl status power-monitor.service | grep "Main PID"', shell=True, capture_output=True)
        output = c.stdout.decode('utf-8').lower()
        if str(self.pid) not in output and len(output) > 10 and 'code=' not in output:
                logger.warning("It appears the power monitor is already running in the background via systemd. Please stop the power monitor with the following command:\n'sudo systemctl stop power-monitor'")
                return True

        # Check process list in case user is running the power monitor manually in an SSH session.
        c = subprocess.run('sudo ps -aux | grep "power_monitor.py" | grep -v "grep"', shell=True, capture_output=True)
        output = c.stdout.decode('utf-8').lower()
        if len(output.splitlines()) > 1:
            if 'power_monitor.py' in c.stdout.decode('utf-8').lower():
                for _ in range(6):
                    output = output.replace('  ', ' ')
                output = output.split(' ')
                user, pid = output[0], output[1]
                logger.warning(f"It appears that the user {user} is already running the power monitor in another session (process ID {pid}). You should not run two copies at the same time because they will compete with each other for access to the PCB.")
                logger.warning(f"If you're not sure where or how the other power monitor session is running, you can kill it with the following command: sudo kill -9 {pid}")
                return True

        return False


    def _cleanup(self, *args, **kwargs) -> None:
        '''Performs necessary termination/shutdown procedures and exits the program.'''

        if not self._halt_flag.is_set():
            logger.info("\nStopping the power monitor gracefully - please wait.")
            self._halt_flag.set()
        try:
            if self.spi:
                self.spi.close()
        except AttributeError:
            pass
        try:
            if self.client:
                self.client.close()
        except AttributeError:
            pass
    
        # Stop plugins
        for plugin_name, plugin in self.imported_plugins.items():
            logger.debug(f"Stopping plugin {plugin['plugin'].name}")
            stopped = plugin['plugin'].stop()
            if not stopped:
                logger.debug(f"... there was a problem stopping the {plugin} plugin.")
    
        exit(0)
        
    def _load_plugins(self, plugins) -> None:
        '''Handles the import of custom plugins.'''

        for plugin_name, config in plugins.items():
            if config['enabled']:
                p = Plugin(plugin_name, config)
                if not p:
                    logger.warning(f"There was a problem importing plugin {plugin_name}. Please review the plugin logs.")
                    continue

                if p._module:   # Plugin was found and successfully imported
                    self.imported_plugins[plugin_name] = {
                        'status' : 'imported',
                        'plugin' : p
                    }
        return
    
    def _measure_sample_rate(self) -> None:
        '''This function gatheres a small amount of sample data and calculates the overall sample rate in samples-per-second.'''

        logger.debug("Checking sample rate...")
        sample_rates = []
        for _ in range(5):
            samples = self._collect_data(100)
            sample_count = sum([len(samples[x]) for x in samples.keys() if type(samples[x]) == list])
            duration = samples['duration']
            sample_rate = round((sample_count / duration), 2)
            sample_rates.append(sample_rate)
        
        
        avg_sample_rate = sum(sample_rates) / len(sample_rates)
        self.sample_rate = round(avg_sample_rate, 2)
        
        logger.debug(f'Sample Rate: {self.sample_rate} samples per second.')
        return
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._cleanup)
        signal.signal(signal.SIGTERM, self._cleanup)

    @staticmethod
    def print_results(SMA_Values, sample_rate) -> None:
        t = PrettyTable(['', 'ct1', 'ct2', 'ct3', 'ct4', 'ct5', 'ct6'])
        t.add_row(['Watts',
                   round(SMA_Values['cts'][1]['power'] if SMA_Values['cts'].get(1) else 0, 3),
                   round(SMA_Values['cts'][2]['power'] if SMA_Values['cts'].get(2) else 0, 3),
                   round(SMA_Values['cts'][3]['power'] if SMA_Values['cts'].get(3) else 0, 3),
                   round(SMA_Values['cts'][4]['power'] if SMA_Values['cts'].get(4) else 0, 3),
                   round(SMA_Values['cts'][5]['power'] if SMA_Values['cts'].get(5) else 0, 3),
                   round(SMA_Values['cts'][6]['power'] if SMA_Values['cts'].get(6) else 0, 3)])
        t.add_row(['Current',
                   round(SMA_Values['cts'][1]['current'] if SMA_Values['cts'].get(1) else 0, 3),
                   round(SMA_Values['cts'][2]['current'] if SMA_Values['cts'].get(2) else 0, 3),
                   round(SMA_Values['cts'][3]['current'] if SMA_Values['cts'].get(3) else 0, 3),
                   round(SMA_Values['cts'][4]['current'] if SMA_Values['cts'].get(4) else 0, 3),
                   round(SMA_Values['cts'][5]['current'] if SMA_Values['cts'].get(5) else 0, 3),
                   round(SMA_Values['cts'][6]['current'] if SMA_Values['cts'].get(6) else 0, 3)])
        t.add_row(['P.F.',
                   round(SMA_Values['cts'][1]['pf'] if SMA_Values['cts'].get(1) else 0, 3),
                   round(SMA_Values['cts'][2]['pf'] if SMA_Values['cts'].get(2) else 0, 3),
                   round(SMA_Values['cts'][3]['pf'] if SMA_Values['cts'].get(3) else 0, 3),
                   round(SMA_Values['cts'][4]['pf'] if SMA_Values['cts'].get(4) else 0, 3),
                   round(SMA_Values['cts'][5]['pf'] if SMA_Values['cts'].get(5) else 0, 3),
                   round(SMA_Values['cts'][6]['pf'] if SMA_Values['cts'].get(6) else 0, 3)])
        t.add_row(['Voltage', round(SMA_Values['voltage'], 3), '', '', '', '', ''])
        t.add_row(['Sample Rate', sample_rate, 'kSPS', '', '', '', ''])

        summary_table = PrettyTable(['Summary Name', 'Watts', 'Amps', 'Power Factor'])
        summary_table.add_row(['Home Consumption', f"{round(SMA_Values['home-consumption']['power'], 3)} W", f"{round(SMA_Values['home-consumption']['current'], 3)} A", '--'])
        summary_table.add_row(['Production', f"{round(SMA_Values['production']['power'], 3)} W", f"{round(SMA_Values['production']['current'], 3)} A", f"{round(SMA_Values['production']['pf'], 2)}"])
        summary_table.add_row(['Net', f"{round(SMA_Values['net']['power'], 3)} W", f"{round(SMA_Values['net']['current'], 3)} A", '--'])
        summary_string = summary_table.get_string()
        s = t.get_string()
        logger.info(f"\n{s}\n{summary_string}")
        return

    @staticmethod
    def get_ip() -> Union[str, None]:
        """ Determines your Pi's local IP address so that it can be displayed to the user for ease of accessing generated plots. 
        
        Returns a string representing the Pi's local IP address that's associated with the default route.
        """
        
        s = socket(AF_INET, SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = None
        finally:
            s.close()
        return ip

class Point:
    def __init__(self, p_type, *args, **kwargs) -> None:

        self.identifier = kwargs['name']    # Power Monitor Identifier, set in config.toml via 'name'

        if p_type == 'home_load':
            self.power = kwargs['power']
            self.current = kwargs['current']
            self.p_type = p_type
            self.time = kwargs['time']
        
        elif p_type == 'solar':
            self.power = kwargs['power']
            self.current = kwargs['current']
            self.pf = kwargs['pf']
            self.p_type = p_type
            self.time = kwargs['time']
            
        elif p_type == 'net': 
            '''
            This type represents the current net power situation at the time of sampling. 
            self.power   : the real net power
            self.current : the rms current as measured
            self.p_type  : the type of point [home_load, solar, net, ct, voltage]
            self.time    : timestamp from when the data was sampled
            '''
            self.power = kwargs['power']
            self.current = kwargs['current']
            self.p_type = p_type
            self.time = kwargs['time']
        
        
        elif p_type == 'ct':
            '''
            This type represents a CT reading.
            self.power   : the real power as calculated in the _calculate_power() function
            self.current : the rms current as measured
            self.p_type  : the type of point [home_load, solar, net, ct, voltage]
            self.ct_num  : the CT number [0-6]
            self.time    : timestamp from when the data was sampled
            '''
            self.power = kwargs['power']
            self.current = kwargs['current']
            self.p_type = p_type
            self.pf = kwargs['pf']
            self.ct_num = kwargs['num']
            self.time = kwargs['time']

        elif p_type == 'voltage':
            '''
            This type represents a voltage reading. 
            The self.voltage is self explanatory.
            The v_input represents the identifier of the voltage input. This is setting up for multiple voltage inputs in the future.
            '''
            self.voltage = kwargs['voltage']
            self.v_input = kwargs['v_input']
            self.time = kwargs['time']
            self.p_type = p_type

    def _to_dict(self) -> Union[str, None]:
        if self.p_type == 'home_load':
            data = {
                "measurement": 'home_load',
                "fields": {
                    "current": self.current,
                    "power": self.power
                },
                "time": self.time
            }
        elif self.p_type == 'solar': 
            data = {
                "measurement": "solar",
                "fields": {
                    "current": self.current,
                    "power": self.power,
                    "pf": self.pf
                },
                "time": self.time
            }
        elif self.p_type == 'net':
            if self.power < 0:
                status = 'Producing'
            elif self.power > 0:
                status = 'Consuming'
            else:
                status = "No data"
            data = {
                "measurement": "net",
                "fields": {
                    "current": self.current,
                    "power": self.power,
                },
                "tags": {
                    "status": status,
                },
                "time": self.time
            }

        elif self.p_type == 'ct':
            data = {
                "measurement": "raw_cts",
                "fields": {
                    "current": self.current,
                    "power": self.power,
                    "pf": self.pf,
                },
                "tags": {
                    "ct": self.ct_num
                },
                "time": self.time
            }

        elif self.p_type == 'voltage':
            data = {
                "measurement": "voltages",
                "fields": {
                    "voltage": self.voltage,
                },
                "tags": {
                    "v_input": self.v_input
                },
                "time": self.time
            }
        else:
            return
        
        # Set the identifier for the point.
        if data.get('tags') is not None:
            data['tags']['id'] = self.identifier
        else:
            data['tags'] = {'id' : self.identifier}

        return data

# Main Stop Event
def _halt(*args, **kwargs) -> None:
    if not RPiPowerMonitor._halt_flag.is_set():
        logger.info("\nStopping the power monitor gracefully - please wait.")
        RPiPowerMonitor._halt_flag.set()
    else:
        logger.info("\nThe power monitor is already stopping - please wait.")

from rpi_power_monitor.plugin_handler import Plugin

if __name__ == '__main__':
    args = parser.parse_args()
    if args.verbose == True:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging output enabled.")

    if args.version:
        import rpi_power_monitor as rpim
        logger.info(f"Raspberry Pi Power Monitor, version: {rpim.__version__}")
        exit()
        

    if args.title and not args.mode == 'plot':
        logger.info("The --title flag should only be used with '--mode plot'")
    
    if args.samples and not args.mode == 'plot':
        logger.info("The --samples flag should only be used with '--mode plot'")


    rpm = RPiPowerMonitor(mode=args.mode, config=args.config)

    if args.mode == 'terminal':
        rpm.terminal_mode = True
        logger.debug("Enabled terminal mode.")
        rpm.run_main()

    if args.mode == 'main':
        rpm.run_main()
    
    if args.mode == 'plot':
        if args.samples:
            num_samples = args.samples
        else:
            num_samples = 1000
        samples = rpm._collect_data(num_samples)
        duration = samples['duration']
        # Calculate Sample Rate in Kilo-Samples Per Second.
        sample_count = sum([len(samples[x]) for x in samples.keys() if type(samples[x]) == list])
        sample_rate = round((sample_count / duration) / 1000, 2)
        per_channel_sample_rate = round(sample_rate / (2 * len(rpm.enabled_channels)), 2)

        if not args.title:
            now = datetime.now().strftime("%m-%d-%y_%H%M%S")
            title = f'Generated-Plot_{now}'
        else:
            title = args.title.replace(' ', '_')
        logger.debug("Building plot...")
        plot_data(samples, title, sample_rate, rpm.enabled_channels)

        ip = rpm.get_ip()
        if ip:
            logger.info(
                f"Plot created! Visit http://{ip}/{title}.html to view the chart. Or, "
                f"simply visit http://{ip} to view all the charts created using '--plot' mode.")
        else:
            logger.info(
                "Plot created! I could not determine the IP address of this machine."
                "Visit your device's IP address in a web browser to view the list of charts "
                "you've created using '--plot' mode.")

def _convert_duration_to_num_samples(duration, sample_rate, num_enabled_channels) -> int:
    '''This is a helper function to convert a given duration into an approximate number of samples.'''

    num_channels_samples = 2 * num_enabled_channels
    est_total_samples_to_collect = sample_rate / duration
    est_per_channel_samples_to_collect = est_total_samples_to_collect / num_channels_samples
    return round(est_per_channel_samples_to_collect)