from influxdb import InfluxDBClient
from influxdb_client import InfluxDBClient as InfluxDBClient2
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb.exceptions import InfluxDBServerError
from datetime import datetime
import random
from time import sleep
from config import logger, db_settings
from requests.exceptions import ConnectionError

# For development only
import sys, traceback

is_version2 = db_settings.get('version', 1) == 2

# Changes to these settings should be made in config.py!

if is_version2:
    client = InfluxDBClient2(
        url=db_settings['url'],
        org=db_settings['org'],
        token=db_settings['token']
    )
else:
    client = InfluxDBClient(
        host=db_settings['host'],
        port=db_settings['port'],
        username=db_settings['username'],
        password=db_settings['password'],
        database=db_settings['database']
        )



class Point():
    def __init__(self, p_type, *args, **kwargs):
        if p_type == 'home_load':
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.p_type  = p_type
            self.time    = kwargs['time']
        
        elif p_type == 'solar':
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.pf      = kwargs['pf']
            self.p_type  = p_type    
            self.time    = kwargs['time']        
            
        elif p_type == 'net': 
            '''
            This type represents the current net power situation at the time of sampling. 
            self.power   : the real net power
            self.current : the rms current as measured
            self.p_type  : the type of point [home_load, solar, net, ct, voltage]
            self.time    : timestamp from when the data was sampled
            '''
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.p_type  = p_type            
            self.time    = kwargs['time']
        
        elif p_type == 'ct':
            '''
            This type represents a CT reading.
            self.power   : the real power as calculated in the calculate_power() function
            self.current : the rms current as measured
            self.p_type  : the type of point [home_load, solar, net, ct, voltage]
            self.ct_num  : the CT number [0-6]
            self.time    : timestamp from when the data was sampled
            '''
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.p_type  = p_type            
            self.pf      = kwargs['pf']
            self.ct_num  = kwargs['num']
            self.time    = kwargs['time']

        elif p_type == 'voltage':
            '''
            This type represents a voltage reading. 
            The self.voltage is self explanatory.
            The v_input represents the identifier of the voltage input. This is setting up for multiple voltage inputs in the future.
            '''
            self.voltage = kwargs['voltage']
            self.v_input = kwargs['v_input']
            self.time    = kwargs['time']
            self.p_type  = p_type
 

    def to_dict(self):
        if self.p_type == 'home_load':
            data = {
                "measurement": 'home_load',
                "fields" : {
                    "current" : self.current,
                    "power": self.power
                },
                "time" : self.time
            }
        elif self.p_type == 'solar': 
            data = {
                "measurement" : "solar",
                "fields" : {
                    "current" : self.current,
                    "power": self.power,
                    "pf": self.pf
                },
                "time" : self.time
            }
        elif self.p_type == 'net':
            if self.power < 0:
                status = 'Producing'
            elif self.power > 0:
                status = 'Consuming'
            else:
                status = "No data"
            data = {
                "measurement" : "net",
                "fields" : {
                    "current" : self.current,
                    "power" : self.power,
                },
                "tags" : {
                    "status" : status,
                },
                "time" : self.time
            }

        elif self.p_type == 'ct':
            data = {
                "measurement" : "raw_cts",
                "fields" : {
                    "current" : self.current,
                    "power" : self.power,
                    "pf" : self.pf,
                },
                "tags" : {
                    'ct' : self.ct_num
                },
                "time" : self.time
            }

        elif self.p_type == 'voltage':
            data = {
                "measurement" : "voltages",
                "fields" : {
                    "voltage" : self.voltage,
                },
                "tags" : {
                    'v_input' : self.v_input
                },
                "time" : self.time
            }
        return data



def init_db():
    try:
        if is_version2:
            # client.buckets_api().create_bucket(
            #     bucket_name=db_settings['bucket'],
            #     org_id=db_settings['org']
            #     )
            # logger.info("... Bucket Created")
            return True
        else:
            client.create_database(db_settings['database'])
            logger.info("... DB initalized.")
            return True
    except ConnectionRefusedError:
        logger.debug("Could not connect to InfluxDB")
        return False
    
    except Exception:
        logger.debug(f"Could not connect to {db_settings['host']}:{db_settings['port']}")
        return False
        
        
    
    


def close_db():
    client.close()

def client_write_points(points):
    if is_version2:
        client.write_api(write_options=ASYNCHRONOUS).write(bucket=db_settings['bucket'], org=db_settings['org'], record=points)
    else:
        client.write_points(points, time_precision='ms')

def write_to_influx(solar_power_values, home_load_values, net_power_values, ct0_dict, ct1_dict, ct2_dict, ct3_dict, ct4_dict, ct5_dict, poll_time, length, voltages):
    
    # Calculate Averages
    avg_solar_power = sum(solar_power_values['power']) / length
    avg_solar_current = sum(solar_power_values['current']) / length
    avg_solar_pf = sum(solar_power_values['pf']) / length
    avg_home_power = sum(home_load_values['power']) / length
    avg_home_current = sum(home_load_values['current']) / length
    avg_net_power = sum(net_power_values['power']) / length
    avg_net_current = sum(net_power_values['current']) / length
    ct0_avg_power = sum(ct0_dict['power']) / length
    ct0_avg_current = sum(ct0_dict['current']) / length
    ct0_avg_pf = sum(ct0_dict['pf']) / length
    ct1_avg_power = sum(ct1_dict['power']) / length
    ct1_avg_current = sum(ct1_dict['current']) / length
    ct1_avg_pf = sum(ct1_dict['pf']) / length
    ct2_avg_power = sum(ct2_dict['power']) / length
    ct2_avg_current = sum(ct2_dict['current']) / length
    ct2_avg_pf = sum(ct2_dict['pf']) / length
    ct3_avg_power = sum(ct3_dict['power']) / length
    ct3_avg_current = sum(ct3_dict['current']) / length
    ct3_avg_pf = sum(ct3_dict['pf']) / length
    ct4_avg_power = sum(ct4_dict['power']) / length
    ct4_avg_current = sum(ct4_dict['current']) / length
    ct4_avg_pf = sum(ct4_dict['pf']) / length
    ct5_avg_power = sum(ct5_dict['power']) / length
    ct5_avg_current = sum(ct5_dict['current']) / length
    ct5_avg_pf = sum(ct5_dict['pf']) / length
    avg_voltage = sum(voltages) / length

    # Create Points
    home_load = Point('home_load', power=avg_home_power, current=avg_home_current, time=poll_time)
    solar = Point('solar', power=avg_solar_power, current=avg_solar_current, pf=avg_solar_pf, time=poll_time)
    net = Point('net', power=avg_net_power, current=avg_net_current, time=poll_time)
    ct0 = Point('ct', power=ct0_avg_power, current=ct0_avg_current, pf=ct0_avg_pf, time=poll_time, num=0)
    ct1 = Point('ct', power=ct1_avg_power, current=ct1_avg_current, pf=ct1_avg_pf, time=poll_time, num=1)
    ct2 = Point('ct', power=ct2_avg_power, current=ct2_avg_current, pf=ct2_avg_pf, time=poll_time, num=2)
    ct3 = Point('ct', power=ct3_avg_power, current=ct3_avg_current, pf=ct3_avg_pf, time=poll_time, num=3)
    ct4 = Point('ct', power=ct4_avg_power, current=ct4_avg_current, pf=ct4_avg_pf, time=poll_time, num=4)
    ct5 = Point('ct', power=ct5_avg_power, current=ct5_avg_current, pf=ct5_avg_pf, time=poll_time, num=5)
    v = Point('voltage', voltage=avg_voltage, v_input=0, time=poll_time)

    points = [
        home_load.to_dict(),
        solar.to_dict(),
        net.to_dict(),
        ct0.to_dict(),
        ct1.to_dict(),
        ct2.to_dict(),
        ct3.to_dict(),
        ct4.to_dict(),
        ct5.to_dict(),
        v.to_dict(),
    ]

    try:    
        client_write_points(points)
    except InfluxDBServerError as e:
        logger.critical(f"Failed to write data to Influx. Reason: {e}")
    except ConnectionError:
        logger.info("Connection to InfluxDB lost. Please investigate!")
        sys.exit()


if __name__ == '__main__':
    client = InfluxDBClient(host='localhost', port=8086, username='root', password='password', database='example')
    test_insert_and_retrieve(client)
