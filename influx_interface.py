from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBServerError
from datetime import datetime
import random

# InfluxDB connection settings
client = InfluxDBClient(host='localhost', port=8086, username='root', password='password', database='power_monitor')



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
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.p_type  = p_type            
            self.time    = kwargs['time']
        
        elif p_type == 'ct':
            self.power   = kwargs['power']
            self.current = kwargs['current']
            self.p_type  = p_type            
            self.pf      = kwargs['pf']
            self.ct_num  = kwargs['num']
            self.time    = kwargs['time']


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
                },
                "tags" : {
                    'ct' : self.ct_num
                },
                "time" : self.time
            }
        return data



def init_db():
    client.create_database('power_monitor')
    print("DB created")  

def close_db():
    client.close()

def write_to_influx(solar_power_values, home_load_values, net_power_values, ct0_dict, ct1_dict, ct2_dict, ct3_dict, ct4_dict, poll_time, length):
    
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

    # Create Points
    home_load = Point('home_load', power=avg_home_power, current=avg_home_current, time=poll_time)
    solar = Point('solar', power=avg_solar_power, current=avg_solar_current, pf=avg_solar_pf, time=poll_time)
    net = Point('net', power=avg_net_power, current=avg_net_current, time=poll_time)
    ct0 = Point('ct', power=ct0_avg_power, current=ct0_avg_current, pf=ct0_avg_pf, time=poll_time, num=0)
    ct1 = Point('ct', power=ct1_avg_power, current=ct1_avg_current, pf=ct1_avg_pf, time=poll_time, num=1)
    ct2 = Point('ct', power=ct2_avg_power, current=ct2_avg_current, pf=ct2_avg_pf, time=poll_time, num=2)
    ct3 = Point('ct', power=ct3_avg_power, current=ct3_avg_current, pf=ct3_avg_pf, time=poll_time, num=3)
    ct4 = Point('ct', power=ct4_avg_power, current=ct4_avg_current, pf=ct4_avg_pf, time=poll_time, num=4)

    points = [
        home_load.to_dict(),
        solar.to_dict(),
        net.to_dict(),
        ct0.to_dict(),
        ct1.to_dict(),
        ct2.to_dict(),
        ct3.to_dict(),
        ct4.to_dict(),
    ]

    try:    
        client.write_points(points, time_precision='ms')
    except influxdb.exceptions.InfluxDBServerError as e:
        print(f"Failed to write data to Influx. Reason: {e}")


if __name__ == '__main__':
    client = InfluxDBClient(host='localhost', port=8086, username='root', password='password', database='example')
    test_insert_and_retrieve(client)