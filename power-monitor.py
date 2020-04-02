#!/usr/bin/python

import spidev
import time
import timeit
import csv
from math import sqrt
import sys
import influx_interface as infl
from datetime import datetime
from plotting import plot_data

#Define Variables
#board_voltage = 3.305
AC_TRANSFORMER_RATIO = 11.5
AC_TRANSFORMER_OUTPUT = 10.6
ct0_channel = 0             # YDHC CT sensor #0 input | Solar Main
ct1_channel = 1             # YDHC CT sensor #1 input | Subpanel main (leg 1 - top)
ct2_channel = 2             # CT sensor #2 input      | House main (leg 1 - left)  (orange pair)
ct3_channel = 3             # CT sensor #3 input      | House main (leg 2 - right) (green pair)
ct4_channel = 4             # CT sensor #4            | Subpanel main (leg 2 - bottom)
board_voltage_channel = 5   # Board voltage ~3.3V
v_sensor_channel = 6        # AC Voltage channel
ref_voltage_channel = 7     # Voltage splitter channel ~1.65V

# DEBUGGING
#MODE = ''
#MODE = 'debug'      # 'debug' mode will disable database storing and enable writing the data to a CSV file.


# Tuning Variables
v_read_delay                = 0.0001       # voltage read delay 
delay_factor                = 1   # Total read delay will be v_read_delay * delay_factor 
ct0_accuracy_factor         = 0   # DONE
ct1_accuracy_factor         = 0    # DONE
ct2_accuracy_factor         = 0    # DONE
ct3_accuracy_factor         = 0   # 
AC_voltage_accuracy_factor  = 0   # Negative if output voltage reads higher than meter


#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1750000


def readadc(adcnum):
    # read SPI data from the MCP3008, 8 channels in total
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

def collect_data(numSamples):
    # Get time of reading
    now = datetime.utcnow()
    
    samples = []
    ct0_data = []
    ct1_data = []
    ct2_data = []
    ct3_data = []
    ct4_data = []
    v_data = []
    while len(v_data) < numSamples:
        ct0 = readadc(ct0_channel)  # Read subpanel leg #1
        ct4 = readadc(ct4_channel)  # Read subpanel leg #2
        ct1 = readadc(ct1_channel)  # Read 
        v = readadc(v_sensor_channel)
        ct2 = readadc(ct2_channel)
        ct3 = readadc(ct3_channel)        
        ct0_data.append(ct0)
        ct1_data.append(ct1)
        ct2_data.append(ct2)
        ct3_data.append(ct3)
        ct4_data.append(ct4)
        v_data.append(v)

    samples = {
        'ct0' : ct0_data,
        'ct1' : ct1_data,
        'ct2' : ct2_data,
        'ct3' : ct3_data,
        'ct4' : ct4_data,
        'voltage' : v_data,
        'time' : now,
    }
    #samples = (ct0_data, ct1_data, ct2_data, ct3_data, v_data, now)
    return samples


def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    filename = f'upstairs-no-conductors-breadboard.csv'
    with open(filename, 'w') as f:
        headers = ["Sample#", "ct0", "ct1", "ct2", "ct3", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        # samples contains lists for each data sample. 
        for i in range(0, len(samples[0])):
            ct0_data = samples[0]
            ct1_data = samples[1]
            ct2_data = samples[2]
            ct3_data = samples[3]
            v_data = samples[-1]
            writer.writerow([i, ct0_data[i], ct1_data[i], ct2_data[i], ct3_data[i], v_data[i]])
    print("data dumped")


def get_ref_voltage(board_voltage):
    # take 10 samples readings and return the average reference voltage from the voltage splitter. Should be equal to about 1.65
    # The reference voltage is fed to input 7 on the MCP3008.

    samples = []
    while len(samples) < 10:
        data = readadc(ref_voltage_channel)
        samples.append(data)
    
    avg_reading = sum(samples) / len(samples)
    ref_voltage = (avg_reading / 1024) * board_voltage
    return ref_voltage

def get_board_voltage():
    # Take 10 sample readings and return the average board voltage from the +3.3V rail. 
    samples = []
    while len(samples) <= 10:
        data = readadc(board_voltage_channel)
        samples.append(data)

    avg_reading = sum(samples) / len(samples)
    board_voltage = (avg_reading / 1024) * 3.31
    return board_voltage



def calculate_power(samples, board_voltage):
    # Samples contains several lists.
    ct0_samples = samples['ct0']
    ct1_samples = samples['ct1']
    ct2_samples = samples['ct2']
    ct3_samples = samples['ct3']
    ct4_samples = samples['ct4']
    v_samples   = samples['voltage']

    # Variable Initialization    
    sum_inst_power_ct0 = 0
    sum_inst_power_ct1 = 0
    sum_inst_power_ct2 = 0
    sum_inst_power_ct3 = 0
    sum_squared_current_ct0 = 0 
    sum_squared_current_ct1 = 0
    sum_squared_current_ct2 = 0
    sum_squared_current_ct3 = 0
    sum_raw_current_ct0 = 0
    sum_raw_current_ct1 = 0
    sum_raw_current_ct2 = 0
    sum_raw_current_ct3 = 0
    sum_squared_voltage = 0
    sum_raw_voltage = 0

    # Scaling factors
    ct0_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct0_accuracy_factor)
    ct1_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct1_accuracy_factor)
    ct2_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct2_accuracy_factor)
    ct3_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct3_accuracy_factor)
    voltage_scaling_factor = (board_voltage / 1024) * 126.5 * (1 + AC_voltage_accuracy_factor)

    
    for i in range(0, len(v_samples)):
        ct0 = (int(ct0_samples[i]))
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        voltage = (int(v_samples[i]))      

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct0 += ct0
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_voltage += voltage

        # Calculate instant power for each ct sensor
        inst_power_ct0 = ct0 * voltage * 2
        inst_power_ct1 = ct1 * voltage
        inst_power_ct2 = ct2 * voltage
        inst_power_ct3 = ct3 * voltage
        sum_inst_power_ct0 += inst_power_ct0
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3

        # Squared voltage
        squared_voltage = voltage * voltage  
        sum_squared_voltage += squared_voltage

        # Squared current
        sq_ct0 = ct0 * ct0
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        
        sum_squared_current_ct0 += sq_ct0
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3

    avg_raw_current_ct0 = sum_raw_current_ct0 / len(v_samples)
    avg_raw_current_ct1 = sum_raw_current_ct1 / len(v_samples)
    avg_raw_current_ct2 = sum_raw_current_ct2 / len(v_samples)
    avg_raw_current_ct3 = sum_raw_current_ct3 / len(v_samples)
    avg_raw_voltage = sum_raw_voltage / len(v_samples)

    real_power_0 = ((sum_inst_power_ct0 / len(v_samples)) - (avg_raw_current_ct0 * avg_raw_voltage * 2))  * ct0_scaling_factor * voltage_scaling_factor
    real_power_1 = ((sum_inst_power_ct1 / len(v_samples)) - (avg_raw_current_ct1 * avg_raw_voltage))  * ct1_scaling_factor * voltage_scaling_factor 
    real_power_2 = ((sum_inst_power_ct2 / len(v_samples)) - (avg_raw_current_ct2 * avg_raw_voltage))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / len(v_samples)) - (avg_raw_current_ct3 * avg_raw_voltage))  * ct3_scaling_factor * voltage_scaling_factor 
    mean_square_voltage = sum_squared_voltage / len(v_samples)    

    rms_voltage = sqrt(mean_square_voltage - (avg_raw_voltage * avg_raw_voltage)) * voltage_scaling_factor

    mean_square_current_ct0 = sum_squared_current_ct0 / len(v_samples) 
    mean_square_current_ct1 = sum_squared_current_ct1 / len(v_samples) 
    mean_square_current_ct2 = sum_squared_current_ct2 / len(v_samples) 
    mean_square_current_ct3 = sum_squared_current_ct3 / len(v_samples) 

    rms_current_ct0 = sqrt(mean_square_current_ct0 - (avg_raw_current_ct0 * avg_raw_current_ct0)) * ct0_scaling_factor
    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor

    if rms_current_ct0 != 0:
        apparent_power = rms_voltage * rms_current_ct0        
        power_factor = real_power_1 / apparent_power

    else:
        apparent_power = 0
        power_factor = 0
    
    results = {
        'ct0' : {
            'type'      : 'production',
            'power'     : real_power_0,
            'current'   : rms_current_ct0
        },
        'ct1' : {
            'type'      : 'consumption',
            'power'     : real_power_1,
            'current'   : rms_current_ct1 
        },
        'ct2' : {
            'type'      : 'consumption', 
            'power'     : real_power_2,
            'current'   : rms_current_ct2
        },
        'ct3' : {
            'type'      : 'consumption',
            'power'     : real_power_3,
            'current'   : rms_current_ct3
        },
        'voltage' : rms_voltage

    }

    return results

def aggregate_results(results):
    total_solar_power = 0
    total_solar_current = 0
    total_subpanel_power = 0
    total_subpanel_current = 0
    total_l_main_power = 0
    total_l_main_current = 0
    total_r_main_power = 0
    total_r_main_current = 0
    total_voltage = 0
    

    for result in results:
        total_solar_power += result['ct0']['power']
        total_solar_current += result['ct0']['current']
        total_subpanel_power += result['ct1']['power']
        total_subpanel_current += result['ct1']['current']
        total_l_main_power += result['ct2']['power']
        total_l_main_current += result['ct2']['current']
        total_r_main_power += result['ct3']['power']
        total_r_main_current += result['ct3']['current']
        total_voltage += result['voltage']
    
    len_results = len(results)
    avg_solar_power = total_solar_power / len_results
    avg_solar_current = total_solar_current / len_results
    avg_subpanel_power = total_subpanel_power / len_results
    avg_subpanel_current = total_subpanel_current / len_results
    avg_l_main_power = total_l_main_power / len_results
    avg_l_main_current = total_l_main_current / len_results
    avg_r_main_power = total_r_main_power / len_results
    avg_r_main_current = total_r_main_current / len_results
    avg_voltage = total_voltage / len_results


    avg_results = {
        'solar_power' : avg_solar_power,
        'solar_current' : avg_solar_current,
        'subpanel_power' : avg_subpanel_power,
        'subpanel_current' : avg_subpanel_current,
        'l_main_power' : avg_l_main_power,
        'l_main_current' : avg_l_main_current,
        'r_main_power' : avg_r_main_power,
        'r_main_current': avg_r_main_current,
        'voltage' : avg_voltage
    }
    
    return avg_results


def run_main():
    avg_rms_voltage = []
    avg_ct_0 = []
    avg_ct_1 = []
    avg_ct_2 = []
    avg_ct_3 = []

    avg_rms_0 = []
    avg_rms_1 = []
    avg_rms_2 = []
    avg_rms_3 = []
    
    all_results = []
    
    while True:        
        try:
            board_voltage = get_board_voltage()
            #print(f"Board voltage is: {board_voltage}") 
            #ref_voltage = get_ref_voltage(board_voltage)
            #print(f"Ref voltage {ref_voltage}V | Board voltage: {board_voltage}V")
            starttime = timeit.default_timer()
            samples = collect_data(2000)
            poll_time = samples['time']
            stop = timeit.default_timer() - starttime
            print(f"Collected {len(samples['ct0']) * (len(samples)-1)} samples in {round(stop,4)} seconds at {spi.max_speed_hz} Hz.")
            
            ct0_samples = samples['ct0']
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_sampels = samples['ct4']
            v_samples = samples['voltage']

  

            results = calculate_power(samples, board_voltage)
    

            print("\n")
            print(f"CT0    : {round(results['ct0']['power'],2):>8} W | {round(results['ct0']['current'],2):>6} A")
            print(f"CT1 : {round(results['ct1']['power'],2):>8} W | {round(results['ct1']['current'],2):>6} A")
            print(f"CT2   : {round(results['ct2']['power'],2):>8} W | {round(results['ct2']['current'],2):>6} A")
            print(f"CT3   : {round(results['ct3']['power'],2):>8} W | {round(results['ct3']['current'],2):>6} A")
            print(f"Voltage   : {round(results['voltage'],2):>8} V")
            
            solar_power      = results['ct0']['power']
            solar_current    = results['ct0']['current']
            subpanel_power   = results['ct1']['power']
            subpanel_current = results['ct1']['current']
            l_main_power     = results['ct2']['power']
            l_main_current   = results['ct2']['current']
            r_main_power     = results['ct3']['power']
            r_main_current   = results['ct3']['current']
            
            # if solar_current < 0.6:
            #     solar_current = solar_current - 0.29

            # if l_main_power < 0 and r_main_power < 0:
            #     current_status = 'Producing'
            
            # else:
            #     current_status = 'Consuming'

            power_exported = abs(l_main_power + r_main_power)
            current_exported = abs(l_main_current + r_main_current)
            home_consumption = abs(power_exported - solar_power) + subpanel_power
            home_load = abs(current_exported - (2 * solar_current)) + subpanel_current        

            if solar_power < home_consumption:
                current_status = 'Consuming'      
                verb = 'consumption'
            else:
                current_status = "Producing"
                verb = 'production'

            # print()
            # print(f"{'Current Status:':<20s} {current_status:>2}")
            # print(f"{f'Net {verb}:':<20s} {round(home_consumption - solar_power, 2)} W")
            # print(f"{'Solar Output:':<20s} {round(solar_power, 2):>8} W | {round(solar_current, 2)} A")
            # print(f"{'Home Consumption:':<20s} {round(home_consumption,2):>8} W | {round(home_load, 2)} A")
            # print(f"{'Line Voltage:':<20s} {round(results['voltage'], 2)} V")
            
            # Aggregate and average results before writing to database
            num_results = 5
            if len(all_results) < num_results:
                all_results.append(results)
            
            else:
                avg_results = aggregate_results(all_results)
                # if MODE != 'debug':
                #     infl.write_to_db(avg_results, poll_time)     
                all_results = []
            
            if MODE == 'debug':
                break

        except KeyboardInterrupt:
            sys.exit()

if __name__ == '__main__':
    
    if len(sys.argv) > 1:
        MODE = sys.argv[1]
        try:
            title = sys.argv[2]
        except IndexError:
            title = None
    else:
        MODE = None

    if MODE != 'debug':
        #infl.init_db()
        run_main()

    else:
        # DEBUG MODE
        samples = collect_data(2000)
        ct0_samples = samples['ct0']
        ct1_samples = samples['ct1']
        ct2_samples = samples['ct2']
        ct3_samples = samples['ct3']
        ct4_samples = samples['ct4']
        v_samples = samples['voltage']

        if not title:
            title = input("Enter the title for this chart: ")

        plot_data(samples, title)
        
        print("file written")