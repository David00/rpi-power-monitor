'''This file imports a legacy Raspberry Pi Power Monitor database into the Unity Monitor environment.'''

__author__ = "David Albrecht <david@dalbrecht.tech>"
__license__ = "GNU General Public License v3 https://www.gnu.org/licenses/gpl-3.0.en.html"
__copyright__ = "Copyright (C) 2022 David Albrecht - Released under terms of the GPLv3 License"

# This file is part of Unity Monitor.
#
# Unity Monitor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Unity Monitor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Unity Monitor.  If not, see <https://www.gnu.org/licenses/>.

from subprocess import run
from textwrap import dedent
import os
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError, InfluxDBClientError
from glob import glob
import time
from datetime import datetime, timedelta


LEGACY_DB_NAME = 'power_monitor'
TEMP_DB_NAME = 'temp_db'
NEW_DB_NAME = 'power_monitor'
BACKUP_TAR_NAME = 'powermon_migrate.tar.gz'
BACKUP_WORKING_DIR = '/opt/influxdb/power-monitor-influx-import'

# DB Settings
host = 'localhost'
port = 8086
username = 'root'
password = 'password'
database = LEGACY_DB_NAME


client = InfluxDBClient(
    host=host,
    port=port,
    username=username,
    password=password,
    database=database
    )


retention_policies = {
    'rp_5min' : {
        'duration' : 'INF'
    },
    'meta' : {
        'duration' : 'INF'
    }
}


########################
# - Process Overview - #
########################
'''
Given a tar containing a portable InfluxDB backup, import the backup to a temporary database named <TEMP_DB_NAME> (defined above).

Determine the date and time boundaries for the imported data. 
Then, iterate through the time range in 5 minute steps, roll up the data in the sub-interval, and insert it into the new database.

'''


def welcome():
    print_break(clear=True)
    logo = dedent('''
  _____                         __  __             _ _             
 |  __ \                       |  \/  |           (_) |            
 | |__) |____      _____ _ __  | \  / | ___  _ __  _| |_ ___  _ __ 
 |  ___/ _ \ \ /\ / / _ \ '__| | |\/| |/ _ \| '_ \| | __/ _ \| '__|
 | |  | (_) \ V  V /  __/ |    | |  | | (_) | | | | | || (_) | |   
 |_|   \___/ \_/\_/ \___|_|    |_|  |_|\___/|_| |_|_|\__\___/|_|   
''')

    print(logo)
    
    print("\n\n")
    print(dedent('''
    
    This script will help you migrate your old Raspberry Pi power monitor data from an InfluxDB Docker Container into a natively installed InfluxDB instance, to prepare you to run either version 0.2.0 or version 0.3.0 of the Power Monitor for Raspberry Pi.
    https://github.com/david00/rpi-power-monitor/

    Requirements:
        1. You must already have a backup generated from your old system.  This script only handles the import process. See the associated README for instructions on generating a backup.
        2. The backup package (powermon_migrate.tar.gz) must be placed in /home/pi/ on this host.
        3. The Power Monitor application must be stopped (this script will stop it automatically).
    '''))

    proceed = input("Proceed? [y|n]: ")
    while True:
        if proceed.lower().strip() not in ['y', 'n']:
            print("Please enter y or n!\n")
            proceed = input("Proceed? [y|n]: ")
        else:
            if proceed.lower().strip() == 'y':
                return True
            else:
                return False

def search_for_backup():
    for root, dirs, files in os.walk('/home/'):
        if BACKUP_TAR_NAME in files:
            print(f"Backup found in: {os.path.join(root, BACKUP_TAR_NAME)}")
            return os.path.join(root, BACKUP_TAR_NAME)

    print("Could not locate your InfluxDB backup. Please enter the full path to the backup location, including the filename below. Example: /home/pi/powermon_migrate.tar.gz")
    backup_location = input("Location: ")

    if not os.path.exists(backup_location):
        print("Still unable to find backup. Please verify it exists and try again.")
        quit()
    
    return backup_location


def extract_backup(backup_location):

    try:
        os.makedirs(BACKUP_WORKING_DIR)
    except FileExistsError:
        proceed = input(f"\nWorking folder at {BACKUP_WORKING_DIR} already exists. \nIf you know you've already extracted the InfluxDB backup to this folder, type n.  Otherwise, type y.\n\nDelete contents of folder and re-extract? [y|n]: ")
        while True:
            if proceed.lower().strip() not in  ['n', 'y']:
                print("Please answer y or n\n")
                proceed = input("Delete contents of folder and re-extract? [y|n]: ")



            elif proceed.lower() == 'y':
                import shutil
                shutil.rmtree(BACKUP_WORKING_DIR)
                os.makedirs(f'{BACKUP_WORKING_DIR}')
                break
            else:
                # Get backup subdirectory name and return it.
                print("Using existing data for backup.")
                subdir = os.listdir(BACKUP_WORKING_DIR)
                if len(subdir) != 1:
                    print("\nBackup format seems invalid. There should only be one folder inside the extracted tar package.  You may need to recreate the backup following the published backup instructions.")
                    quit()
                else:
                    return subdir[0]

    print()
    print(f"Extracting backup to {BACKUP_WORKING_DIR}. This can take up to 20 minutes (or more). Please wait. You will not see any output while it is extracting.")
    start = time.time()
    run(f'tar -xzf {backup_location} -C {BACKUP_WORKING_DIR}', shell=True)
    end = time.time()
    print(f"Backup extracted in {end - start} seconds.")
    subdir = os.listdir(BACKUP_WORKING_DIR)
    if len(subdir) != 1:
        print("\nBackup format seems invalid. There should only be one folder inside the extracted tar package.  You may need to recreate the backup following the published backup instructions.")
        quit()
    else:
        return subdir[0]

def import_to_influx(backup_subdir):
    '''High level interface for handling the Influx import process. Performs checks and interacts with the user (if necessary) to determine if the import is OK to run.'''

    # Check to see if the target database exists in Influx already.
    existing_databases = [db['name'] for db in client.get_list_database()]
    if TEMP_DB_NAME in existing_databases:
        retry_import = input(f"It looks like the import has previously ran (the temporary database named '{TEMP_DB_NAME}' already exists in InfluxDB. Delete this database and try running the import again? [y|n]: ")
        if retry_import.lower() == 'y':
            client.drop_database(TEMP_DB_NAME)
            print(f"Temporary database {TEMP_DB_NAME} deleted.")
            imported = run_import(backup_subdir)           
        
        else:
            print(f"Skipping the import process and proceeding with existing data in the {TEMP_DB_NAME} table.")
            imported = True # This should be true to allow the process to continue to the next step.

    else:
        imported = run_import(backup_subdir)

    return imported



def run_import(backup_subdir):
    '''Runs the actual import command.'''
    print("\nImporting data to a temporary database now. Please wait - this will take several minutes...")
    start = time.time()
    #output = run(f"docker exec -it influx influxd restore -portable -db {LEGACY_DB_NAME} -newdb {TEMP_DB_NAME} {os.path.join('/var/lib/influxdb/', 'power-monitor-influx-import', backup_subdir)} ", shell=True, capture_output=True)
    output = run(f"influxd restore -portable -db {LEGACY_DB_NAME} -newdb {TEMP_DB_NAME} {os.path.join(BACKUP_WORKING_DIR, backup_subdir)} ", shell=True, capture_output=True)
    output = output.stdout.decode('utf-8')
    end = time.time()
    if "Restoring" in output:
        print_break()
        print(f"Imported data in {round(end - start, 2)} seconds.")
        return True
    elif 'database may already exist' in output:
        print(f"Target database {TEMP_DB_NAME} already exists. No new data was imported.")
        return False
    else:
        print(output)
    

def print_break(clear=True):
    if clear:
        run('clear')
    size = os.get_terminal_size()
    print('#' * size.columns)
    print("\n")

def rollup_data(last_completed=None):
    '''
    Steps through the high resolution data from the backup and runs the queries necessary to downsample the data into 5 minute averages.
    '''

    from math import floor
    print_break(clear=True)
    print(dedent('''

    ##################
    # - IMPORTANT! - #
    ##################

    Which CT numbering scheme did you use when deploying your existing power monitor project? 
    
        A. Zero through Five (0 - 5)
        B. One through Six (1 - 6)
    
    If you deployed your power monitor prior to March 2022, it's likely option A. 
    If you deployed your power monitor during or after March 2022, it's likely option B.

    Choosing option A will renumber the CT data to make it match the new scheme in use (1-6). 
    This means the data for each CT will be moved to the next channel up, as in:
    CT 0 becomes CT 1
    CT 1 becomes CT 2
    ... etc.

    Choosing option B will keep the CT data as is (ie, CT 1 will stay as CT 1 in the database).

    If you used channel numbers 0-5 in your install, choose option A.
    If you used channel numbers 1-6 in your install, choose option B.


    '''))

    while True:
        numbering_scheme = input("Selection [A|B]: ")
        if numbering_scheme.lower().strip() not in ['a', 'b']:
            print("Please enter A or B!")
        else:
            numbering_scheme = numbering_scheme.lower().strip()
            break





    print("\n\nTHIS WILL TAKE A CONSIDERABLE AMOUNT OF TIME.\n\nIf you need to stop it, press Ctrl-C, and progress will be saved for you to resume later.")

    if not last_completed:
        # Determine the oldest timestamp.
        rs = client.query("select * from raw_cts where ct = '1' ORDER BY time LIMIT 1;", database=TEMP_DB_NAME)
        t = list(rs.get_points())[0]['time']

        # Determine which 5 minute interval this timestamp should be a part in.
        start_time = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
        start_interval_minute = floor(start_time.minute / 5) * 5

    else:
        start_time = last_completed
        start_interval_minute = floor(start_time.minute / 5) * 5
        

    # Determine the newest timestamp
    rs = client.query("select * from raw_cts where ct = '1' ORDER BY time DESC LIMIT 1", database=TEMP_DB_NAME)
    t = list(rs.get_points())[0]['time']
    end_time = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')


    # Begin rolling up data
    this_start = datetime(year=start_time.year, month=start_time.month, day=start_time.day, hour=start_time.hour, minute=start_interval_minute)
    day = this_start.day
    month = this_start.month
    print(f"\nStarting to downsample high resolution raw data, beginning from {this_start.strftime('%m-%d-%Y')}.")
    print("The output below will list the days that have been completed.")
    with open('/.migrate-import-progress', 'a') as f:
        print(f"    {datetime.strftime(this_start, '%b')}: ", end='', flush=True)
        while this_start <= end_time:
            this_end = this_start + timedelta(minutes=5)

            
            # Home power, current
            query = f'''SELECT mean(power) as power, mean(current) as current INTO {NEW_DB_NAME}.rp_5min.home_load_5m FROM home_load WHERE time > '{this_start}' and time < '{this_end}' GROUP BY TIME(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)

            # Home energy
            query = f'''SELECT integral(power) / 3600000 AS energy INTO {NEW_DB_NAME}.rp_5min.home_energy_5m FROM home_load WHERE time > '{this_start}' and time < '{this_end}' GROUP BY TIME(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)

            # Net power, current
            query = f'''SELECT mean(power) as power, mean(current) as current INTO {NEW_DB_NAME}.rp_5min.net_5m FROM net WHERE time > '{this_start}' and time < '{this_end}' GROUP BY TIME(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)
            
            # Net energy
            query = f'''SELECT integral(power) / 3600000 AS energy INTO {NEW_DB_NAME}.rp_5min.net_energy_5m FROM net WHERE time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)

            # Solar power, current
            query = f'''SELECT mean(power) AS power, mean(current) AS current INTO {NEW_DB_NAME}.rp_5min.solar_5m FROM solar WHERE time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)
            
            # Solar energy
            query = f'''SELECT integral(power) / 3600000 AS energy INTO {NEW_DB_NAME}.rp_5min.solar_energy_5m FROM solar WHERE time > '{this_start}' and time < '{this_end}' GROUP BY TIME(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)

            # Voltages
            query = f'''SELECT mean(voltage) AS voltage INTO {NEW_DB_NAME}.rp_5min.voltage_0_5m FROM voltages WHERE time > '{this_start}' and time < '{this_end}' and v_input = '0' GROUP BY time(5m)'''
            rs = client.query(query, database=TEMP_DB_NAME)

            if numbering_scheme == 'a':

                ############################
                # - Numbering Scheme 0-5 - #
                ############################

                # CT0 in the backup becomes CT1 in the new table, and so on.

                # CT0 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct1_power_5m FROM raw_cts WHERE ct = '0' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT0 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct1_energy_5m FROM raw_cts WHERE ct = '0' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT1 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct2_power_5m FROM raw_cts WHERE ct = '1' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT1 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct2_energy_5m FROM raw_cts WHERE ct = '1' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT2 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct3_power_5m FROM raw_cts WHERE ct = '2' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT2 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct3_energy_5m FROM raw_cts WHERE ct = '2' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT3 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct4_power_5m FROM raw_cts WHERE ct = '3' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT3 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct4_energy_5m FROM raw_cts WHERE ct = '3' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT4 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct5_power_5m FROM raw_cts WHERE ct = '4' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT4 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct5_energy_5m FROM raw_cts WHERE ct = '4' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT5 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct6_power_5m FROM raw_cts WHERE ct = '5' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT5 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct6_energy_5m FROM raw_cts WHERE ct = '5' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)


            elif numbering_scheme == 'b':
                ############################
                # - Numbering Scheme 1-6 - #
                ############################

                # CT0 in the backup stays as CT0 in the new table, and so on.


                # CT1 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct1_power_5m FROM raw_cts WHERE ct = '1' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT1 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct1_energy_5m FROM raw_cts WHERE ct = '1' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT2 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct2_power_5m FROM raw_cts WHERE ct = '2' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT2 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct2_energy_5m FROM raw_cts WHERE ct = '2' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT3 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct3_power_5m FROM raw_cts WHERE ct = '3' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT3 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct3_energy_5m FROM raw_cts WHERE ct = '3' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT4 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct4_power_5m FROM raw_cts WHERE ct = '4' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT4 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct4_energy_5m FROM raw_cts WHERE ct = '4' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT5 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct5_power_5m FROM raw_cts WHERE ct = '5' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT5 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct5_energy_5m FROM raw_cts WHERE ct = '5' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)

                # CT6 power, current, PF
                query = f'''SELECT mean(power) AS power, mean(current) AS current, mean(pf) AS pf INTO power_monitor.rp_5min.ct6_power_5m FROM raw_cts WHERE ct = '6' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)
                # CT6 energy
                query = f'''SELECT integral(power) / 3600000 AS energy INTO power_monitor.rp_5min.ct6_energy_5m FROM raw_cts WHERE ct = '6' and time > '{this_start}' and time < '{this_end}' GROUP BY time(5m)'''
                rs = client.query(query, database=TEMP_DB_NAME)


            # Write last completed start-time to file.
            f.write(f'{this_start}\n')

            # Increment time interval

            this_start += timedelta(minutes=5)
            if this_start.day != day:
                print(f'{day}, ', end='', flush=True)
                if this_start.month != month:
                    print(f"\n    {   datetime.strftime(this_start, '%b') }: ", end='', flush=True)
                    month = this_start.month            
                day = this_start.day

        print("\nDatabase import complete!")
        

def stop_power_monitor():
    output = run('systemctl stop power-monitor.service', shell=True, capture_output=True)
    output, errors = (output.stdout.decode('utf-8'), output.stderr.decode('utf-8') )
    if errors:
        if 'service not loaded' not in errors:
            print(f"Encountered an unexpected error. Halting script.")
            quit()


def check_migration_progress():
    # Check for previous migration progress.
    if os.path.exists('/.backup-import-progress'):
        return True
    return False



def start():
    proceed = welcome()
    if not proceed:
        print("Goodbye!")
        quit()
    stop_power_monitor()
    print_break(clear=False)

    migration_in_progress = check_migration_progress()
    if migration_in_progress:
        with open('/.backup-import-progress', 'r') as f:
            last_completed = f.readlines()[-1]

        print(dedent(f'''It looks like you've started an import already, which migrated data up until {last_completed}
        Would you like to continue from where you left off?

        Answering y will continue the data migration from where it left off.
        Answering n will give you the option to start over from the beginning.'''))
        continue_import = input("\nResume migration? [y|n]: ")

        while True:
            if continue_import.lower().strip() not in ['y', 'n']:
                print("Please enter y or n.")
                continue_import = input("\nResume migration? [y|n]: ")
                
            else:
                break
        

        if continue_import.lower().strip() == 'y':
            last_completed = datetime.strptime(last_completed.strip(), '%Y-%m-%d %H:%M:%S')
            rollup_data(last_completed=last_completed)
        else:
            migration_in_progress = False

    if not migration_in_progress:  
        backup_location = search_for_backup()

        backup_subdir = extract_backup(backup_location)
        
        # Validate and/or create retention policies if they do not exist.
        validate_rps()
        validate_cqs()

        import_successful = import_to_influx(backup_subdir) # Returns True or False

        if import_successful:
            rollup_data()
        else:
            print("\nInfluxDB import process was not successful. Please review the output from above and determine where the problem occured.")

    return


def validate_rps():
    '''Ensures that the retention policies and continuous queries exist, and creates them in the new db if not.'''

    existing_rps = client.get_list_retention_policies()
    rp_names = [rp['name'] for rp in existing_rps]

    for rp in retention_policies.keys():
        if rp not in rp_names:
            client.create_retention_policy(rp, retention_policies[rp]['duration'], 1, default = (True if rp == 'rp_raw' else False), database=NEW_DB_NAME)
            print(f"Created retention policy {rp}.")
        else:
            print(f"Retention policy {rp} already exists.")    


def validate_cqs():

    retention_policies = {
        '5m' : 'rp_5min'
        }

    cqs = client.get_list_continuous_queries()
    existing_cqs = []
    for db in cqs:
        if NEW_DB_NAME in db.keys():
            if len(db[NEW_DB_NAME]) > 0:
                existing_cqs = [cq['name'] for cq in db[NEW_DB_NAME] ]
 
    if 'cq_home_power_5m' not in existing_cqs:
        for duration, rp_name in retention_policies.items():
            client.create_continuous_query(f'cq_home_power_{duration}', f'SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."home_load_{duration}" FROM "home_load" GROUP BY time({duration})', database=NEW_DB_NAME)
            print(f"Created influxDB CQ: cq_home_power_{duration}")
    
    if 'cq_net_power_5m' not in existing_cqs:
        for duration, rp_name in retention_policies.items():
            client.create_continuous_query(f'cq_net_power_{duration}', f'SELECT mean("power") AS "power", mean("current") AS "current" INTO "{rp_name}"."net_{duration}" FROM "net" GROUP BY time({duration})', database=NEW_DB_NAME)    
            print(f"Created influxDB CQ: cq_net_power_{duration}")

    if 'cq_solar_5m' not in existing_cqs:
        for duration, rp_name in retention_policies.items():
            client.create_continuous_query(f'cq_solar_{duration}', f'SELECT mean("real_power") AS "power", mean("current") AS "current" INTO "{rp_name}"."solar_{duration}" FROM "solar" GROUP BY time({duration})', database=NEW_DB_NAME)
            print(f"Created influxDB CQ: cq_solar_{duration}")

    return

def cleanup():
    '''Deletes the temporary database and closes the connection to Influx.'''



    client.close()
    if TEMP_DB_NAME != NEW_DB_NAME:
        client.drop_database(TEMP_DB_NAME)
        print(f"Removed temporary database {TEMP_DB_NAME}")

if __name__ == '__main__':
    try:
        start()
    except KeyboardInterrupt:
        print("\n\nScript interrupted with Ctrl-C. (If you were in the middle of a migration, your progress has been saved).  Goodbye!")
    cleanup()
