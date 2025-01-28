from time import sleep
import logging

from power_monitor import RPiPowerMonitor, logger, ch


config =  {
    'general' : {
        'name' : 'Power-Monitor'
        },
    'database' : {
        'enabled' : False,
        'host' : 'localhost',
        'port' : 8086,
        'username' : 'root',
        'password' : 'password',
        'database_name' : 'power_monitor',
        'influx_version' : 1,
        # The Influx V2 configuration is only required if influx_version (above) is set to 1.
        # Set influx_version = 2, and fill in your InfluxDB v2 parameters below, to use InfluxDB v2.
        'influx_v2' : {
            'bucket' : 'power_monitor',
            'org' : '<your Influx Cloud email or custom defined org>',
            'token' : '<an API token with at least r/w permissions for all buckets and all tasks>',
            'url' : '<your unique Influx Cloud or self-hosted InfluxDB v2 server URL>',
        }
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
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
            'phase_angle' : 0
        },
        'channel_2' : {
            'name' : 'Channel 2',
            'rating' : 100,
            'type' : 'consumption',
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
            'phase_angle' : 0
        },
        'channel_3' : {
            'name' : 'Channel 3',
            'rating' : 100,
            'type' : 'consumption',
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
            'phase_angle' : 0
        },
        'channel_4' : {
            'name' : 'Channel 4',
            'rating' : 100,
            'type' : 'consumption',
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
            'phase_angle' : 0
        },
        'channel_5' : {
            'name' : 'Channel 5',
            'rating' : 100,
            'type' : 'consumption',
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
            'phase_angle' : 0
        },
        'channel_6' : {
            'name' : 'Channel 6',
            'rating' : 100,
            'type' : 'consumption',
            'two_pole' : False,
            'enabled' : True,
            'calibration' : 1.0,
            'amps_cutoff_threshold' : 0.01,
            'reversed' : False,
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
            'enabled' : False,
            'host' : '192.168.0.10'
        }
    }
}


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)
    
    # Instantiate the class using the dictionary config.
    rpm = RPiPowerMonitor(config=config)

    # This is an example call to calculate the power on demand for channel 1. The `duration` key is simply how long to sample for before those samples are then used in the power calculation.
    print(rpm.get_single_channel_measurements(channel=1, duration=0.5))
    
    # Sample Response (from a PCB with no sensors attached)
    '''
    {1: {'type': 'consumption', 'power': 0.0, 'current': 0.0, 'voltage': 0.166376704922229, 'pf': 0}}
    '''
    
    # You can also use the rpm.get_power_measurements to sample all channels for a given duration.
    print(rpm.get_power_measurements(duration=0.5))
    
    # Sample Response (from a PCB with no sensors attached)
    '''
    
    {1: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.1875829860604289, 'pf': 0},
     2: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.18721555470986087, 'pf': 0},
     3: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.1885725671567515, 'pf': 0},
     4: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.1886439495894453, 'pf': 0},
     5: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.18652368116784318, 'pf': 0},
     6: {'type': 'consumption', 'power': 0, 'current': 0, 'voltage': 0.18768352047679315, 'pf': 0}
    }
    '''

    # Alternatively, you can run the standard Power Monitor deployment (including plugins), which sends data to your configured InfluxDB instance.
    rpm.run_main()