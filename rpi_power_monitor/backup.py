# This script will backup your power monitor database from InfluxDB. 
# If you are using a remote InfluxDB server (as in, not on your Raspberry Pi), you should not run this script, because
# it stops the power monitor in order to generate the backup.

# Backup settings are configured in rpi-power-monitor/rpi_power_monitor/config.toml

import os
import subprocess
from glob import glob
from datetime import datetime
import tomli
import argparse
import logging
import logging.handlers
import pathlib
import shutil
from time import sleep
import timeit

# Logging Setup. Logs to file named backups.log and also to the console.
formatter = logging.Formatter(fmt='{asctime} - {levelname}: {message}', datefmt='%m-%d-%Y %H:%M:%S', style='{')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

module_root = pathlib.Path(__file__).parent
b_log = logging.getLogger(os.path.join(module_root, 'backup_logger'))
b_log.setLevel(logging.DEBUG)

rfh = logging.handlers.RotatingFileHandler('backups.log', backupCount=1)
rfh.setLevel(logging.DEBUG)
rfh.setFormatter(formatter)
b_log.addHandler(ch)
b_log.addHandler(rfh)

# Shell Colors
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
ORANGE = '\033[38;5;214m'
GREEN = '\033[0;32m'
CYAN = '\033[0;36m'
NC = '\033[0m'

class Backup():
    '''Backup handler for Raspberry Pi Power Monitor.'''

    def __init__(self, settings):
        self.settings = settings
        b_log.info(f"\n{YELLOW}------------- Starting new backup -------------{NC}")

    def run(self, settings):
        '''Starts the Power Monitor backup process. 
        
        This function only handles the backup setup and config file backup; it determines if the host is using Docker or a native 
        installation of InfluxDB and calls either run_docker_backup() or run_native_backup() to execute the backup.
        '''

        start = timeit.default_timer()

        # Initialize backup constants.
        now = datetime.now().strftime('%Y-%m-%d_%H%M')
        create_and_mount_path(settings['device'], settings['mount_path'])
        backup_root = os.path.join(settings['mount_path'], self.settings['folder']) # like /media/backups/power_monitor_backups/
        this_backup_dir = os.path.join(backup_root, f'backup_{now}')    # like /media/backups/power_monitor_backups/backup_01-31-2023_0933)
        if not os.path.exists(this_backup_dir):
            os.makedirs(this_backup_dir)
            b_log.debug(f"Created directory {this_backup_dir}.")
        else:
            b_log.debug("Backup directory already exists.")

        # Backup config.toml
        shutil.copy2(settings['config_path'], this_backup_dir)
        # Stop Power Monitor service and backup InfluxDB
        r = subprocess.run('systemctl stop power-monitor.service', shell=True)
        b_log.info("Stopped power monitor service... Starting InfluxDB Backup. ")
        b_log.info("Please wait. This can take several minutes if you have a lot of data, and you won't see any output until it's done.")

        # Determine if this host is using Docker or a native InfluxDB installation.
        output = subprocess.run('docker ps | grep influxdb', shell=True, capture_output=True)
        if 'influxdb' in output.stdout.decode():
            # Docker container mode
            container_name = output.stdout.decode().split('   ')[-1].strip()
            print("Container name: ", container_name)
            print(f"Executing: docker exec {container_name} mkdir -p /backups/{this_backup_dir}'")
            subprocess.run(f'docker exec {container_name} mkdir -p /backups/{this_backup_dir}', shell=True)
            subprocess.run(f'docker exec {container_name} influxd backup -portable -database {settings["db_name"]} /backups/{this_backup_dir} > /dev/null', shell=True)
            b_log.info("Done backing up InfluxDB. Creating an archive...")
            r = subprocess.run(f'docker exec {container_name} tar -czf /backups/backup_{now}.tar.gz /backups/{this_backup_dir} > /dev/null 2>&1', shell=True)
            r = subprocess.run(f'docker cp {container_name}:/backups/backup_{now}.tar.gz {backup_root}', shell=True)
            b_log.debug("Done creating the archive. Cleaning up...")

            r = subprocess.run(f'docker exec {container_name} rm -r /backups/{this_backup_dir}', shell=True)
            r = subprocess.run(f'docker exec {container_name} rm -r /backups/backup_{now}.tar.gz', shell=True)

        else:
            # Natively installed InfluxDB mode - check to see if the configured database is localhost in order to continue.
            if settings['host'] not in ['localhost', '127.0.0.1', '127.0.1.1']:
                b_log.error(f"This script can only be used when InfluxDB is running locally on this Pi. Your configured database host is {settings['host']} which does not appear to be local to this Pi.")
                exit()

            r = subprocess.run(f'influxd backup -portable -database {settings["db_name"]} {this_backup_dir}/ > /dev/null', shell=True)
            b_log.info("Done backing up InfluxDB. Creating an archive...")
            # Create compressed archive
            r = subprocess.run(f'tar -czf {os.path.join(backup_root, f"backup_{now}.tar.gz")} {os.path.join(backup_root, f"backup_{now}")} > /dev/null 2>&1', shell=True)
            b_log.debug("Done creating the archive. Cleaning up...")
            # Cleanup
            subprocess.run(f'rm -r {this_backup_dir}', shell=True)

        # Check for backup_count limit
        existing_backups = glob(os.path.join(backup_root, 'backup_*.tar*'))
        existing_backups.sort(key=os.path.getmtime)

        if len(existing_backups) > settings['count']:
            b_log.info(f"There are currently {len(existing_backups)} backups. Removing {len(existing_backups) - settings['count']} old backups.")
            while len(existing_backups) > settings['count']:
                existing_backups.pop(0)
                subprocess.run(f'rm {existing_backups[0]}', shell=True)

        # Get filesize
        size = os.path.getsize(os.path.join(backup_root, f'backup_{now}.tar.gz'))
        size = size / 1E6   # Convert to MB
        
        # Unmount the drive
        r = subprocess.run(f"umount {settings['mount_path']}", shell=True, capture_output=True)
        if r.returncode == 0:
            b_log.debug("USB Drive unmounted.")
        else:
            b_log.debug(f"There was a problem unmounting your USB drive. Error message:\n{r.stderr.decode()}")


        stop = timeit.default_timer()
        duration = round(stop - start, 2)

        # Start the power monitor
        r = subprocess.run('systemctl start power-monitor.service', shell=True, capture_output=True)
        if r.returncode != 0:
            b_log.warning(f"\n\n{RED}WARNING!{NC} Failed to start power monitor service after the backup. {RED}YOUR POWER MONITOR IS NOT RUNNING!{NC} The response from systemd was:\n\n    {r.stderr.decode()}")
        else:
            b_log.info(f"{GREEN}Backup completed successfully in {duration} seconds.{NC} Backup filesize: {size} MB")
        exit()




def create_and_mount_path(device, mount_path):
    '''Mounts your USB drive to the provided path (creating the path if necessary)'''

    if not os.path.exists(mount_path):
        try:
            os.mkdir(mount_path)
        except Exception as e:
            b_log.debug(f"Failed to create the path at {mount_path}. Message: {e}")
            exit()
    
    mounts = subprocess.run(f'mount | grep "{device}"', capture_output=True, shell=True)
    output = mounts.stdout.decode()
    if device in output:
        if f'{device} on {mount_path}' in output:
            b_log.debug(f"Device {device} is already mounted.")
            return
        else:
            try:
                current_mount_path = output.split('type')[0].split('on')[-1].strip()
            except:
                b_log.debug(f"{YELLOW}Your device is already mounted, but I was unable to determine current mount path. Please unmount your device with 'sudo umount /PATH/TO/MOUNTPOINT' and try again.{NC}")
                exit()
            
            b_log.debug(f"{YELLOW}Device {device} is mounted, but not to the intended target. Please unmount your backup drive with 'sudo umount {current_mount_point}' and run the script again.{NC}")
            exit()
    # Mount the drive if it's not mounted (script returns above if it's already properly mounted)
    try:
        p = subprocess.run(f'mount {device} {mount_path} > /dev/null', shell=True)
        sleep(1)
        if p.returncode == 0:
            b_log.info(f"Mounted {device} to {mount_path}")
            return True
        else:
            b_log.info(f"  {ORANGE}Failed to mount {device} to {mount_path}.{NC} stderr:\n{p.stderr}")
            return False
    
    except Exception as e:
        b_log.info(f"  {ORANGE}There was a problem mounting {device}.{NC} Error:\n{e}")
        return False




def parse_config(config):
    '''Parses the configuration file to ensure all the required values are there.'''

     # Check if the database is a remote or local host. This script is intended only for locally ran databases.
    try:
        db_host = config.get('database').get('host')
    except Exception as e:
        b_log.debug(f"The host field seems to be missing from the config.toml field in the database section. Please check this out and rerun the script. Error message:\n{e}")
        exit()
    
    if '127.0.0' not in db_host and db_host.lower() != 'localhost':
        b_log.debug("It seems you are trying to run this backup script for a remote InfluxDB instance. This script aims to backup the data on a local Raspberry Pi instance.")
        exit()
    
    # Config loading
    try:
        backup_settings = config.get('backups')
        if not backup_settings:
            b_log.error("It appears your config file is missing the [backups] section. Please see the docs at https://github.com/david00/rpi-power-monitor for the latest version of config.toml.")
            exit()
        
        database_settings = config.get('database')
        
        host = 'localhost' if not database_settings.get('host') else database_settings.get('host')
        port = 8088 if not database_settings.get('port') else database_settings.get('port')
        backup_device = backup_settings.get('backup_device')
        mount_path = backup_settings.get('mount_path')
        folder_name = 'power_monitor_backups' if not backup_settings.get('folder_name') else backup_settings.get('folder_name')
        backup_count = int(backup_settings.get('backup_count'))
        db_name = database_settings.get('database_name')
    except Exception as e:
        b_log.debug(f"There was a problem loading the requred values from your config file. Please see the error below and fix the config.toml file:\n{e}")
        exit()

    # Optional values    
    username = database_settings.get('username')
    password = database_settings.get('password')
    

    settings = {
        'device' : backup_device,
        'mount_path' : mount_path,
        'count' : backup_count,
        'db_name' : db_name,
        'host' : host,
        'port' : port,
        'username' : username,
        'password' : password,
        'folder' : folder_name,
    }

    return settings


if __name__ == '__main__':

    # Check for root access
    uid = os.geteuid()
    if uid != 0:
        b_log.info("You must be root to run this script (it needs to mount your USB drive)")
        exit()

    # TODO: Update documentation with usage instructions.
    parser = argparse.ArgumentParser(description='Power Monitor CLI Backup Interface', epilog='Documentation for the backup interface coming soon.')
    parser.add_argument('--config', type=pathlib.Path, help='path to config.toml file.', default=os.path.join(module_root, 'config.toml'), required=False)
    args = parser.parse_args()    

    config_path = os.path.join(module_root, 'config.toml')
    if args.config:
        config_path = args.config
        if not os.path.exists(config_path):
            b_log.error(f"Did not find a config file at {config_path}. (Note: You can use the --config flag to specify the path to config.toml). Exiting.")
            exit()    

    try:
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
    except tomli.TOMLDecodeError:
        b_log.debug("The file config.toml appears to have a TOML syntax error. Please run the config through a TOML validator, make corrections, and try again.")
        exit()
        
    settings = parse_config(config)
    settings['config_path'] = config_path
    backup = Backup(settings)
    backup.run(settings)