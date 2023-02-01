#!/usr/bin/python
import csv
import logging
import os
import subprocess
import sys
import timeit
from datetime import datetime
from math import sqrt, cos
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import socket, getaddrinfo
import ipaddress
from textwrap import dedent
from time import sleep
import tomli
import spidev
from prettytable import PrettyTable
import argparse
import pathlib
import urllib3

from rpi_power_monitor.plotting import plot_data
import rpi_power_monitor.influx_interface as infl
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError

# Logging Config
logger = logging.getLogger('power_monitor')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch_formatter = logging.Formatter('%(levelname)s : %(message)s')
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='Power Monitor CLI Interface', epilog='Please see the project documentation at https://github.com/david00/rpi-power-monitor#readme for further usage instructions.')
parser.add_argument('--mode', type=str, help="Operating Mode. Defaults to 'main' if not specified.", default='main', required=False, choices=['main', 'terminal', 'plot'])
parser.add_argument('--title', type=str, help="Optionally specify the title of the generated plot.", required=False)
parser.add_argument('--config', type=pathlib.Path, help='path to config.toml file.', default='/home/pi/rpi-power-monitor/rpi_power_monitor/config.toml', required=False)
parser.add_argument('-v', '--verbose', help='Increases verbosity of program output.', action='store_true')
parser.add_argument('-V', '--version', help='Displays the power monitor software version and exits.', action='store_true')



class RPiPowerMonitor:
    """ Class to take readings from the MCP3008 and calculate power """
    def __init__(self, mode, config, spi=None):
        # Check to see if there is already a power monitor process running.
        c = subprocess.run('sudo systemctl status power-monitor.service', shell=True, capture_output=True)
        if 'active: running' in c.stdout.decode('utf-8').lower():
            logger.warning("It appears the power monitor is already running in the background via systemd. Please stop the power monitor with the following command:\n'sudo systemctl stop power-monitor'")
            self.cleanup(-1)

        self.load_config(config)
        
        if spi:
            self.spi = spi
        else:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 1750000
        
        # Get DB Client
        self.get_db_client()
        if not self.client:
            logger.error(f"Failed to connect to InfluxDB server at {self.config['database']['host']}:{self.config['database']['port']}. Please make sure it's reachable and try again.")
            self.cleanup(-1)
        
        # Other Initializations
        self.points_buffer = [] # A buffer to hold sublists of points so that they can be written altogether (reduces DB overhead)
        self.def_cal = 0.88     # This is the default calibration factor for all CTs from my shop.
        self.terminal_mode = False

    def load_config(self, config_file=os.path.join('/home/pi/rpi-power-monitor/rpi_power_monitor', 'config.toml')):
        '''Loads the user's config.toml file and validates entries.'''

        invalid_settings = False
        logger.debug(f"Config file path: {config_file}")
        if not os.path.exists(config_file): 
            logger.error(f"Could not find your config.toml file at rpi_power_monitor/config.toml. Please ensure it exists, or, provide the config file location with the -c flag when launching the program.")

        logger.debug(f"Attempting to loading config from {config_file}")

        try:
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
        except FileNotFoundError:
            self.cleanup(-1)
        
        except tomli.TOMLDecodeError:
            logger.warning("The file config.toml appears to have a TOML syntax error. Please run the config through a TOML validator, make corrections, and try again.")
            self.cleanup(-1)

        self.config = config
        self.grid_voltage = config.get('grid_voltage').get('grid_voltage')
        self.ac_transformer_output_voltage = config.get('grid_voltage').get('ac_transformer_output_voltage')
        self.voltage_calibration = config.get('grid_voltage').get('voltage_calibration')
        self.name = config['general'].get('name')

        # Enabled Channels
        self.enabled_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['enabled'] ]
        if len(self.enabled_channels) == 0:
            invalid_settings = True
            logger.warning("Invalid config file setting: No channels have been enabled!")
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
                logger.warning(f"Invalid config file setting: 'type' for {ct_channel} should be 'consumption' or 'production', or 'mains'. It is currently set to: '{config['current_transformers'][ct_channel]['type']}'.")
                invalid_settings = True


        # Mains assignment
        self.mains_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'mains' and settings['enabled'] == True]
        if len(self.mains_channels) > 0:
            logger.debug(f"Identified mains channels: {self.mains_channels}")
        else:
            logger.debug("No mains channels configured.")

        if invalid_settings:
            logger.critical("Invalid settings detected in config.toml. Please review any warning messages above and correct the issue.")
            self.cleanup(-1)

        # Production sources assignment
        self.production_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'production' and settings['enabled'] == True]
        logger.debug(f"Identified {len(self.production_channels)} production channels: ({self.production_channels})")
    
        # Consumption sources assignment
        self.consumption_channels = [int(channel.split('_')[-1]) for channel, settings in config['current_transformers'].items() if settings['type'] == 'consumption' and settings['enabled'] == True]
        logger.debug(f"Identified {len(self.consumption_channels)} consumption channels: ({self.consumption_channels})")

        # Two-pole validation
        for channel, settings in config['current_transformers'].items():
            if 'two_pole' not in settings.keys():
                logger.critical(f"{channel.capitalize()} is missing the two_pole setting in the config file. Please make sure the config has an entry for 'two_pole' and try again.")
                self.cleanup(-1)

    def get_db_client(self):
        '''Creates an InfluxDB Client using the loaded configuration.'''

        host = self.config['database']['host']
        port = self.config['database']['port']
        logger.debug(f"Trying to connect to the Influx database at {host}:{port}...")

        # Validate DB Settings
        db_host_valid = True
        try:
            host = host
        except ipaddress.AddressValueError:
            logger.debug(f'DB host does not look like an IP address. Testing DNS resolution...')
            pass
        try:
            ip = getaddrinfo(host, None)
        except Exception as e:
            logger.debug(f'Failed to translate database host to IP. Exception msg: {e}')
            db_host_valid = False
        
        if not db_host_valid:
            logger.warning(dedent(
                f"It appears that the database host value of {host} is not a valid IP or DNS name.  Or, DNS name resolution failed. Please check this setting and your networking settings and try again."))
            self.cleanup(-1)


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
            self.cleanup(-1)

        
        # Test Client
        try:
            self.client.create_database(self.config['database']['database_name'])
        except ConnectionRefusedError:
            logger.warning("DB connection refused - is Influx running?.")
            self.cleanup(-1)
        except Exception as e:
            logger.warning(f"Failed to connect to the Influx database at {host}:{port}.")
            logger.debug(f"Error message:\n{e}")
            self.cleanup(-1)
        
        logger.debug(f"Successfully connected to Influx at {host}:{port}")
        return
        

    def dump_data(self, dump_type, samples):
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

    def get_board_voltage(self):
        """ Take 10 sample readings and return the average board voltage from the +3.3V rail. """
        samples = []
        while len(samples) <= 10:
            data = self.read_adc(4) # channel 4 is the 3.3V ref voltage
            samples.append(data)

        avg_reading = sum(samples) / len(samples)
        board_voltage = (avg_reading / 1024) * 3.31 * 2
        return board_voltage

    def read_adc(self, adc_num):
        """ Read SPI data from the MCP3008, 8 channels in total. """
        r = self.spi.xfer2([1, 8 + adc_num << 4, 0])
        data = ((r[1] & 3) << 8) + r[2]
        return data

    def collect_data(self, num_samples):
        """  Takes <num_samples> readings from the ADC for each ADC channel and returns a dictionary containing the CT channel number as the key, and a list of that channel's sample data.
        
        Arguments:
        num_samples -- int, the number of samples to collect for each channel.

        Returns a dictionary where the keys are ct1 - ct6, voltage, and time, and the value of each key is a list of that channel's samples (except for 'time', which is a UTC datetime)
        """
        now = datetime.utcnow()  # Get time of reading

        samples = dict()
        for pcb_chan in self.enabled_channels:
            samples[f'ct{pcb_chan}'] = []
            samples[f'v{pcb_chan}'] = []

        start = timeit.default_timer()
        for _ in range(num_samples):
            for pcb_chan, adc_chan in self.enabled_adc_ct_channels.items():
                samples[f'ct{pcb_chan}'].append(self.read_adc(adc_chan))
                samples[f'v{pcb_chan}'].append(self.read_adc(5))
        stop = timeit.default_timer()
        duration = stop - start
       
        samples['time'] = now
        samples['duration'] = duration
        return samples

    def calculate_power(self, samples, board_voltage):
        """ Calculates amperage, real power, power factor, and voltage
        
        Arguments:
        samples -- dict, a dictionary containing lists of each channel's sample data, and a voltage wave that's been collected for each corresponding channel.

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

        num_samples = len(v_samples_1)

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
            if self.config['current_transformers']['channel_1']['two_pole']:
                real_power_1 = real_power_1 * 2
                rms_current_ct1 = rms_current_ct1 * 2
            try:
                power_factor_1 = real_power_1 / apparent_power_1
            except ZeroDivisionError:
                power_factor_1 = 0
            results[1] = {
                'type': self.config['current_transformers']['channel_1']['type'],
                'power': real_power_1,
                'current': rms_current_ct1,
                'voltage': rms_voltage_1,
                'pf': power_factor_1
            }

        if ct2_samples:
            avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
            avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
            real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor
            mean_square_current_ct2 = sum_squared_current_ct2 / num_samples
            mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
            rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
            rms_voltage_2 = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
            apparent_power_2 = rms_voltage_2 * rms_current_ct2
            if self.config['current_transformers']['channel_2']['two_pole']:
                real_power_2 = real_power_2 * 2
                rms_current_ct2 = rms_current_ct2 * 2
            try:
                power_factor_2 = real_power_2 / apparent_power_2
            except ZeroDivisionError:
                power_factor_2 = 0
            results[2] = {
                'type': self.config['current_transformers']['channel_2']['type'],
                'power': real_power_2,
                'current': rms_current_ct2,
                'voltage': rms_voltage_2,
                'pf': power_factor_2
            }

        if ct3_samples:
            avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
            avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
            real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor
            mean_square_current_ct3 = sum_squared_current_ct3 / num_samples
            mean_square_voltage_3 = sum_squared_voltage_3 / num_samples
            rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
            rms_voltage_3 = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor
            apparent_power_3 = rms_voltage_3 * rms_current_ct3
            if self.config['current_transformers']['channel_3']['two_pole']:
                real_power_3 = real_power_3 * 2
                rms_current_ct3 = rms_current_ct3 * 2
            try:
                power_factor_3 = real_power_3 / apparent_power_3
            except ZeroDivisionError:
                power_factor_3 = 0
            results[3] = {
                'type': self.config['current_transformers']['channel_3']['type'],
                'power': real_power_3,
                'current': rms_current_ct3,
                'voltage': rms_voltage_3,
                'pf': power_factor_3
            }

        if ct4_samples:
            avg_raw_current_ct4 = sum_raw_current_ct4 / num_samples
            avg_raw_voltage_4 = sum_raw_voltage_4 / num_samples
            real_power_4 = ((sum_inst_power_ct4 / num_samples) - (avg_raw_current_ct4 * avg_raw_voltage_4))  * ct4_scaling_factor * voltage_scaling_factor
            mean_square_current_ct4 = sum_squared_current_ct4 / num_samples
            mean_square_voltage_4 = sum_squared_voltage_4 / num_samples
            rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor
            rms_voltage_4 = sqrt(mean_square_voltage_4 - (avg_raw_voltage_4 * avg_raw_voltage_4)) * voltage_scaling_factor
            apparent_power_4 = rms_voltage_4 * rms_current_ct4
            if self.config['current_transformers']['channel_4']['two_pole']:
                real_power_4 = real_power_4 * 2
                rms_current_ct4 = rms_current_ct4 * 2
            try:
                power_factor_4 = real_power_4 / apparent_power_4
            except ZeroDivisionError:
                power_factor_4 = 0
            results[4] = {
                'type': self.config['current_transformers']['channel_4']['type'],
                'power': real_power_4,
                'current': rms_current_ct4,
                'voltage': rms_voltage_4,
                'pf': power_factor_4
            }

        if ct5_samples:
            avg_raw_current_ct5 = sum_raw_current_ct5 / num_samples
            avg_raw_voltage_5 = sum_raw_voltage_5 / num_samples
            real_power_5 = ((sum_inst_power_ct5 / num_samples) - (avg_raw_current_ct5 * avg_raw_voltage_5))  * ct5_scaling_factor * voltage_scaling_factor
            mean_square_current_ct5 = sum_squared_current_ct5 / num_samples
            mean_square_voltage_5 = sum_squared_voltage_5 / num_samples
            rms_current_ct5 = sqrt(mean_square_current_ct5 - (avg_raw_current_ct5 * avg_raw_current_ct5)) * ct5_scaling_factor
            rms_voltage_5 = sqrt(mean_square_voltage_5 - (avg_raw_voltage_5 * avg_raw_voltage_5)) * voltage_scaling_factor
            apparent_power_5 = rms_voltage_5 * rms_current_ct5
            if self.config['current_transformers']['channel_5']['two_pole']:
                real_power_5 = real_power_5 * 2
                rms_current_ct5 = rms_current_ct5 * 2
            try:
                power_factor_5 = real_power_5 / apparent_power_5
            except ZeroDivisionError:
                power_factor_5 = 0
            results[5] = {
                'type': self.config['current_transformers']['channel_5']['type'],
                'power': real_power_5,
                'current': rms_current_ct5,
                'voltage': rms_voltage_5,
                'pf': power_factor_5
            }

        if ct6_samples:
            avg_raw_current_ct6 = sum_raw_current_ct6 / num_samples
            avg_raw_voltage_6 = sum_raw_voltage_6 / num_samples
            real_power_6 = ((sum_inst_power_ct6 / num_samples) - (avg_raw_current_ct6 * avg_raw_voltage_6))  * ct6_scaling_factor * voltage_scaling_factor
            mean_square_current_ct6 = sum_squared_current_ct6 / num_samples
            mean_square_voltage_6 = sum_squared_voltage_6 / num_samples
            rms_current_ct6 = sqrt(mean_square_current_ct6 - (avg_raw_current_ct6 * avg_raw_current_ct6)) * ct6_scaling_factor
            rms_voltage_6 = sqrt(mean_square_voltage_6 - (avg_raw_voltage_6 * avg_raw_voltage_6)) * voltage_scaling_factor
            apparent_power_6 = rms_voltage_6 * rms_current_ct6
            if self.config['current_transformers']['channel_6']['two_pole']:
                real_power_6 = real_power_6 * 2
                rms_current_ct6 = rms_current_ct6 * 2
            try:
                power_factor_6 = real_power_6 / apparent_power_6
            except ZeroDivisionError:
                power_factor_6 = 0        
            results[6] = {
                'type': self.config['current_transformers']['channel_6']['type'],
                'power': real_power_6,
                'current': rms_current_ct6,
                'voltage': rms_voltage_6,
                'pf': power_factor_6
            }
        
        # Grab the voltage from one of the enabled channels:
        results['voltage'] = results[self.enabled_channels[0]]['voltage']

        # Cutoff Threshold check
        for chan_num  in self.enabled_channels:
            cutoff = float(self.config['current_transformers'][f'channel_{chan_num}']['watts_cutoff_threshold'])
            if cutoff != 0:
                if abs(results[chan_num]['power']) < cutoff:
                    results[chan_num]['power'] = 0
                    results[chan_num]['current'] = 0
                    results[chan_num]['pf'] = 0
        return results

    def run_main(self):
        """ Starts the main power monitor loop. """
        logger.info("... Starting Raspberry Pi Power Monitor")
        logger.info("Press Ctrl-c to quit...")
        # The following empty dictionaries will hold the respective calculated values at the end
        # of each polling cycle, which are then averaged prior to storing the value to the DB.
        production_values = dict(power=[], pf=[], current=[])
        home_consumption_values = dict(power=[], pf=[], current=[])
        net_values = dict(power=[], current=[])
        ct_dict = {channel : {'power' : [], 'pf' : [], 'current' : []} for channel in self.enabled_channels}
        rms_voltages = []
        SMA_Values = {channel : {'power' : [], 'pf' : [], 'current' : []} for channel in self.enabled_channels}
        num_samples = 1000

        i = 0   # Counter for averaging function
        # Get the expected sample count for the current configuration.
        samples = self.collect_data(num_samples)
        sample_count = sum([len(samples[x]) for x in samples.keys() if type(samples[x]) == list])
        
        while True:
            try:
                board_voltage = self.get_board_voltage()
                samples = self.collect_data(num_samples)
                poll_time = samples['time']
                duration = samples['duration']
                sample_rate = round((sample_count / duration) / num_samples, 2)
                per_channel_sample_rate = round(sample_rate / (2 * len(rpm.enabled_channels)), 2)                
                # logger.debug(f"Sample rates. Overall: {sample_rate} | Per-channel: {per_channel_sample_rate}")


                results = self.calculate_power(samples, board_voltage)

                # RMS calculation for phase correction only - this is not needed after everything is tuned.
                # The following code is used to compare the RMS power to the calculated real power.
                # Ideally, you want the RMS power to equal the real power when measuring a purely resistive load.
                # rms_power_1 = round(results['ct1']['current'] * results['ct1']['voltage'], 2)  # AKA apparent power
                # rms_power_2 = round(results['ct2']['current'] * results['ct2']['voltage'], 2)  # AKA apparent power
                # rms_power_3 = round(results['ct3']['current'] * results['ct3']['voltage'], 2)  # AKA apparent power
                # rms_power_4 = round(results['ct4']['current'] * results['ct4']['voltage'], 2)  # AKA apparent power
                # rms_power_5 = round(results['ct5']['current'] * results['ct5']['voltage'], 2)  # AKA apparent power
                # rms_power_6 = round(results['ct6']['current'] * results['ct6']['voltage'], 2)  # AKA apparent power

                # Prepare values for database storage
                production_power = 0
                production_current = 0
                production_pf = 0   # Average power factor from all production sources

                # Set the RMS voltage using one of the calculated voltages.
                voltage = results[self.enabled_channels[0]]['voltage']

                # Determine if the system is net producing or net consuming right now by looking at the panel mains.
                # Since the current measured is always positive,
                # we need to add a negative sign to the amperage value if we're exporting power.
                for chan_num in self.mains_channels:
                    if results[chan_num]['power'] < 0:
                        results[chan_num]['current'] = results[chan_num]['current'] * -1
                    
                # Set the current for any production sources negative and find the total power and current from all production sources.
                for chan_num in self.production_channels:
                    if results[chan_num]['power'] < 0:
                        results[chan_num]['current'] = results[chan_num]['current'] * -1
                    
                    production_power += results[chan_num]['power']
                    production_current += results[chan_num]['current']

                # Home consumption power is the total power that the home is using. This is typically the mains minus the production sources. 
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
                        home_consumption_current -= results[chan_num]['current'] # Current from production sources is already "negative", so subtracting it here instead of adding it is correct.


                net_power = home_consumption_power - production_power
                net_current = home_consumption_current + production_current

                if net_power < 0:
                    current_status = "Producing"
                else:
                    current_status = "Consuming"

                # Create a simple-moving-average of 10 points
                # for chan_num in self.enabled_channels:                    
                #     SMA_Values[chan_num]


                # Average 10 readings before sending to db
                if i < 10:
                    production_values['power'].append(production_power)
                    production_values['current'].append(production_current)
                    production_values['pf'].append(production_pf)

                    home_consumption_values['power'].append(home_consumption_power)
                    home_consumption_values['current'].append(home_consumption_current)

                    net_values['power'].append(net_power)
                    net_values['current'].append(net_current)

                    for chan_num in self.enabled_channels:
                        ct_dict[chan_num]['power'].append(results[chan_num]['power'])
                        ct_dict[chan_num]['current'].append(results[chan_num]['current'])
                        ct_dict[chan_num]['pf'].append(results[chan_num]['pf'])

                    rms_voltages.append(voltage)
                    i += 1
                else:
                    # Calculate the average, buffer the result, and write to Influx 
                    # if the batch size has met the threshold.
                    self.queue_for_influx(
                        production_values,
                        home_consumption_values,
                        net_values,
                        ct_dict,
                        poll_time,
                        i,
                        rms_voltages)
                    production_values = dict(power=[], pf=[], current=[])
                    home_consumption_values = dict(power=[], pf=[], current=[])
                    net_values = dict(power=[], current=[])
                    ct_dict = {channel : {'power' : [], 'pf' : [], 'current' : []} for channel in self.enabled_channels}
                    rms_voltages = []
                    i = 0

                    if self.terminal_mode:                        
                        self.print_results(results, sample_rate)

            except KeyboardInterrupt:
                self.cleanup(0)


    def queue_for_influx(self,
                        production_values,
                        home_consumption_values,
                        net_values,
                        ct_dict,
                        poll_time,
                        length,
                        voltages):
        # Calculate Averages
        avg_production_power = sum(production_values['power']) / length
        avg_production_current = sum(production_values['current']) / length
        avg_production_pf = sum(production_values['pf']) / length
        avg_home_power = sum(home_consumption_values['power']) / length
        avg_home_current = sum(home_consumption_values['current']) / length
        avg_net_power = sum(net_values['power']) / length
        avg_net_current = sum(net_values['current']) / length

        # Create per-channel Point()
        ct_points = []
        for chan_num in self.enabled_channels:
            power = sum(ct_dict[chan_num]['power']) / length
            current = sum(ct_dict[chan_num]['current']) / length
            pf = sum(ct_dict[chan_num]['pf']) / length
            avg_voltage = sum(voltages) / length

            ct_points.append(
                Point('ct', power=power, current=current, pf=pf, time=poll_time, num=chan_num, name=self.name).to_dict()
            )

        # Create Points
        home_load = Point('home_load', power=avg_home_power, current=avg_home_current, time=poll_time, name=self.name)
        production = Point('solar', power=avg_production_power, current=avg_production_current, pf=avg_production_pf, time=poll_time, name=self.name)
        net = Point('net', power=avg_net_power, current=avg_net_current, time=poll_time, name=self.name)
        v = Point('voltage', voltage=avg_voltage, v_input=0, time=poll_time, name=self.name)

        points = [
            home_load.to_dict(),
            production.to_dict(),
            net.to_dict(),
            v.to_dict(),
        ]
        points += ct_points

        self.points_buffer += points
        batch_size = 25
        if len(self.points_buffer) >= batch_size:
            # Push buffer to DB
            try:
                self.client.write_points(self.points_buffer, time_precision='ms')
            except InfluxDBServerError as e:
                logger.critical(f"Failed to write data to Influx. Reason: {e}")
            except ConnectionError:
                logger.info("Connection to InfluxDB lost. Please investigate!")
                quit()
            
            # logger.info(f"Wrote {len(self.points_buffer)} points to the DB ({batch_size} batches)")
            self.points_buffer = []


    def cleanup(self, returncode):
        '''Performs necessary termination/shutdown procedures and exits the program.'''
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
    
        exit(returncode)
        

    @staticmethod
    def print_results(results, sample_rate):
        t = PrettyTable(['', 'ct1', 'ct2', 'ct3', 'ct4', 'ct5', 'ct6'])
        t.add_row(['Watts',
                   round(results[1]['power'] if results.get(1) else 0, 3),
                   round(results[2]['power'] if results.get(2) else 0, 3),
                   round(results[3]['power'] if results.get(3) else 0, 3),
                   round(results[4]['power'] if results.get(4) else 0, 3),
                   round(results[5]['power'] if results.get(5) else 0, 3),
                   round(results[6]['power'] if results.get(6) else 0, 3)])
        t.add_row(['Current',
                   round(results[1]['current'] if results.get(1) else 0, 3),
                   round(results[2]['current'] if results.get(2) else 0, 3),
                   round(results[3]['current'] if results.get(3) else 0, 3),
                   round(results[4]['current'] if results.get(4) else 0, 3),
                   round(results[5]['current'] if results.get(5) else 0, 3),
                   round(results[6]['current'] if results.get(6) else 0, 3)])
        t.add_row(['P.F.',
                   round(results[1]['pf'] if results.get(1) else 0, 3),
                   round(results[2]['pf'] if results.get(2) else 0, 3),
                   round(results[3]['pf'] if results.get(3) else 0, 3),
                   round(results[4]['pf'] if results.get(4) else 0, 3),
                   round(results[5]['pf'] if results.get(5) else 0, 3),
                   round(results[6]['pf'] if results.get(6) else 0, 3)])
        t.add_row(['Voltage', round(results['voltage'], 3), '', '', '', '', ''])
        t.add_row(['Sample Rate', sample_rate, 'kSPS', '', '', '', ''])
        s = t.get_string()
        logger.info(f"\n{s}")

    @staticmethod
    def get_ip():
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
    def __init__(self, p_type, *args, **kwargs):

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
            self.power   : the real power as calculated in the calculate_power() function
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

    def to_dict(self):
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

if __name__ == '__main__':

    args = parser.parse_args()
    if args.verbose == True:
        ch.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logs output enabled.")

    if args.version:
        import rpi_power_monitor as rpim
        logger.info(f"Raspberry Pi Power Monitor, version: {rpim.__version__}")
        exit()
        

    if args.title and not args.mode == 'plot':
        logger.info("The --title flag should only be used with '--mode plot'")
        exit()


    rpm = RPiPowerMonitor(args.mode, args.config)

    if args.mode == 'terminal':
        rpm.terminal_mode = True
        logger.debug("Enabled terminal mode.")
        rpm.run_main()

    if args.mode == 'main':
        rpm.run_main()
    
    if args.mode == 'plot':
        samples = rpm.collect_data(1000)
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


import rpi_power_monitor.influx_interface as infl