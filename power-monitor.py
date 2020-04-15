#!/usr/bin/python

import spidev
from time import sleep
import timeit
import csv
from math import sqrt
import sys
import influx_interface as infl
from datetime import datetime
from plotting import plot_data
import pickle
import os

#Define Variables
ct0_channel = 0             # Orange Pair           | House main (leg 1 - left)  (orange pair)
ct1_channel = 1             # Green Pair            | House main (leg 2 - right) (green pair)
ct2_channel = 2             # Blue Pair             | Subpanel main (leg 1 - top)
ct3_channel = 3             # Brown Pair            | Solar Power 
ct4_channel = 6             # CT sensor #4          | Subpanel main (leg 2 - bottom)
board_voltage_channel =  4  # Board voltage ~3.3V
v_sensor_channel = 5        # AC Voltage channel
ct5_channel = 7             # Available for use


# Tuning Variables
ct0_accuracy_factor         = 1.0151
ct1_accuracy_factor         = 1.054
ct2_accuracy_factor         = 0.9751
ct3_accuracy_factor         = 0.985
ct4_accuracy_factor         = 1
ct5_accuracy_factor         = 1
AC_voltage_accuracy_factor  = 1.075

# Phase Calibration - note that these items are listed in the order they are sampled.
ct0_phasecal = 1.3025    # Calculated  1.5              # TUNED 
ct4_phasecal = 1.3       # Calculated 1.3333            # TUNED
ct1_phasecal = 2.1995    # Calculated 1.166667          # TUNED 
ct2_phasecal = 1.475     # Calculated 1.166667          # TUNED 
ct3_phasecal = 1.775     # Calculated 1.3333            # TUNED 

#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1750000          # Changing this value will require you to adjust the phasecal values above.


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
        ct0 = readadc(ct0_channel)
        ct4 = readadc(ct4_channel)
        ct1 = readadc(ct1_channel)
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
    return samples


def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    filename = f'upstairs-no-conductors-breadboard.csv'
    with open(filename, 'w') as f:
        headers = ["Sample#", "ct0", "ct1", "ct2", "ct3", "ct4", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        # samples contains lists for each data sample. 
        for i in range(0, len(samples[0])):
            ct0_data = samples[0]
            ct1_data = samples[1]
            ct2_data = samples[2]
            ct3_data = samples[3]
            ct4_data = samples[4]
            v_data = samples[-1]
            writer.writerow([i, ct0_data[i], ct1_data[i], ct2_data[i], ct3_data[i], ct4_data[i], v_data[i]])
    print("data dumped")

def get_board_voltage():
    # Take 10 sample readings and return the average board voltage from the +3.3V rail. 
    samples = []
    while len(samples) <= 10:
        data = readadc(board_voltage_channel)
        samples.append(data)

    avg_reading = sum(samples) / len(samples)
    board_voltage = (avg_reading / 1024) * 3.31 * 2    
    return board_voltage

# Phase corrected power calculation
def calculate_power(samples, board_voltage):
    ct0_samples = samples['ct0']        # current samples for CT0
    ct1_samples = samples['ct1']        # current samples for CT1
    ct2_samples = samples['ct2']        # current samples for CT2
    ct3_samples = samples['ct3']        # current samples for CT3
    ct4_samples = samples['ct4']        # current samples for CT4
    v_samples_0 = samples['v_ct0']      # phase-corrected voltage wave specifically for CT0
    v_samples_1 = samples['v_ct1']      # phase-corrected voltage wave specifically for CT1
    v_samples_2 = samples['v_ct2']      # phase-corrected voltage wave specifically for CT2
    v_samples_3 = samples['v_ct3']      # phase-corrected voltage wave specifically for CT3
    v_samples_4 = samples['v_ct4']      # phase-corrected voltage wave specifically for CT4   

    # Variable Initialization    
    sum_inst_power_ct0 = 0
    sum_inst_power_ct1 = 0
    sum_inst_power_ct2 = 0
    sum_inst_power_ct3 = 0
    sum_inst_power_ct4 = 0
    sum_squared_current_ct0 = 0 
    sum_squared_current_ct1 = 0
    sum_squared_current_ct2 = 0
    sum_squared_current_ct3 = 0
    sum_squared_current_ct4 = 0
    sum_raw_current_ct0 = 0
    sum_raw_current_ct1 = 0
    sum_raw_current_ct2 = 0
    sum_raw_current_ct3 = 0
    sum_raw_current_ct4 = 0
    sum_squared_voltage_0 = 0
    sum_squared_voltage_1 = 0
    sum_squared_voltage_2 = 0
    sum_squared_voltage_3 = 0
    sum_squared_voltage_4 = 0
    sum_raw_voltage_0 = 0
    sum_raw_voltage_1 = 0
    sum_raw_voltage_2 = 0
    sum_raw_voltage_3 = 0
    sum_raw_voltage_4 = 0

    # Scaling factors
    vref = board_voltage / 1024
    ct0_scaling_factor = vref * 100 * ct0_accuracy_factor
    ct1_scaling_factor = vref * 100 * ct1_accuracy_factor
    ct2_scaling_factor = vref * 100 * ct2_accuracy_factor
    ct3_scaling_factor = vref * 100 * ct3_accuracy_factor
    ct4_scaling_factor = vref * 100 * ct4_accuracy_factor
    voltage_scaling_factor = vref * 126.5 * AC_voltage_accuracy_factor

    num_samples = len(v_samples_0)
    
    for i in range(0, num_samples):
        ct0 = (int(ct0_samples[i]))
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        ct4 = (int(ct4_samples[i]))        
        voltage_0 = (int(v_samples_0[i]))      
        voltage_1 = (int(v_samples_1[i]))      
        voltage_2 = (int(v_samples_2[i]))      
        voltage_3 = (int(v_samples_3[i]))      
        voltage_4 = (int(v_samples_4[i]))      

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct0 += ct0
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_current_ct4 += ct4
        sum_raw_voltage_0 += voltage_0
        sum_raw_voltage_1 += voltage_1
        sum_raw_voltage_2 += voltage_2
        sum_raw_voltage_3 += voltage_3
        sum_raw_voltage_4 += voltage_4


        # Calculate instant power for each ct sensor
        inst_power_ct0 = ct0 * voltage_0
        inst_power_ct1 = ct1 * voltage_1
        inst_power_ct2 = ct2 * voltage_2
        inst_power_ct3 = ct3 * voltage_3
        inst_power_ct4 = ct4 * voltage_4
        sum_inst_power_ct0 += inst_power_ct0
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3
        sum_inst_power_ct4 += inst_power_ct4

        # Squared voltage
        squared_voltage_0 = voltage_0 * voltage_0
        squared_voltage_1 = voltage_1 * voltage_1
        squared_voltage_2 = voltage_2 * voltage_2
        squared_voltage_3 = voltage_3 * voltage_3
        squared_voltage_4 = voltage_4 * voltage_4
        sum_squared_voltage_0 += squared_voltage_0
        sum_squared_voltage_1 += squared_voltage_1
        sum_squared_voltage_2 += squared_voltage_2
        sum_squared_voltage_3 += squared_voltage_3
        sum_squared_voltage_4 += squared_voltage_4

        # Squared current
        sq_ct0 = ct0 * ct0
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        sq_ct4 = ct4 * ct4
        
        sum_squared_current_ct0 += sq_ct0
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3
        sum_squared_current_ct4 += sq_ct4

    avg_raw_current_ct0 = sum_raw_current_ct0 / num_samples
    avg_raw_current_ct1 = sum_raw_current_ct1 / num_samples
    avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
    avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
    avg_raw_current_ct4 = sum_raw_current_ct4 / num_samples
    avg_raw_voltage_0 = sum_raw_voltage_0 / num_samples
    avg_raw_voltage_1 = sum_raw_voltage_1 / num_samples
    avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
    avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
    avg_raw_voltage_4 = sum_raw_voltage_4 / num_samples
    
    real_power_0 = ((sum_inst_power_ct0 / num_samples) - (avg_raw_current_ct0 * avg_raw_voltage_0))  * ct0_scaling_factor * voltage_scaling_factor
    real_power_1 = ((sum_inst_power_ct1 / num_samples) - (avg_raw_current_ct1 * avg_raw_voltage_1))  * ct1_scaling_factor * voltage_scaling_factor 
    real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor 
    real_power_4 = ((sum_inst_power_ct4 / num_samples) - (avg_raw_current_ct4 * avg_raw_voltage_4))  * ct4_scaling_factor * voltage_scaling_factor 

    mean_square_current_ct0 = sum_squared_current_ct0 / num_samples 
    mean_square_current_ct1 = sum_squared_current_ct1 / num_samples 
    mean_square_current_ct2 = sum_squared_current_ct2 / num_samples 
    mean_square_current_ct3 = sum_squared_current_ct3 / num_samples 
    mean_square_current_ct4 = sum_squared_current_ct4 / num_samples 
    mean_square_voltage_0 = sum_squared_voltage_0 / num_samples
    mean_square_voltage_1 = sum_squared_voltage_1 / num_samples
    mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
    mean_square_voltage_3 = sum_squared_voltage_3 / num_samples
    mean_square_voltage_4 = sum_squared_voltage_4 / num_samples

    rms_current_ct0 = sqrt(mean_square_current_ct0 - (avg_raw_current_ct0 * avg_raw_current_ct0)) * ct0_scaling_factor
    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
    rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor
    rms_voltage_0     = sqrt(mean_square_voltage_0 - (avg_raw_voltage_0 * avg_raw_voltage_0)) * voltage_scaling_factor
    rms_voltage_1     = sqrt(mean_square_voltage_1 - (avg_raw_voltage_1 * avg_raw_voltage_1)) * voltage_scaling_factor
    rms_voltage_2     = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
    rms_voltage_3     = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor
    rms_voltage_4     = sqrt(mean_square_voltage_4 - (avg_raw_voltage_4 * avg_raw_voltage_4)) * voltage_scaling_factor

    # Power Factor
    apparent_power_0 = rms_voltage_0 * rms_current_ct0        
    apparent_power_1 = rms_voltage_1 * rms_current_ct1        
    apparent_power_2 = rms_voltage_2 * rms_current_ct2        
    apparent_power_3 = rms_voltage_3 * rms_current_ct3        
    apparent_power_4 = rms_voltage_4 * rms_current_ct4        
    
    try:
        power_factor_0 = real_power_0 / apparent_power_0
    except ZeroDivisionError:
        power_factor_0 = 0
    try:
        power_factor_1 = real_power_1 / apparent_power_1
    except ZeroDivisionError:
        power_factor_1 = 0
    try:
        power_factor_2 = real_power_2 / apparent_power_2
    except ZeroDivisionError:
        power_factor_2 = 0
    try:
        power_factor_3 = real_power_3 / apparent_power_3
    except ZeroDivisionError:
        power_factor_3 = 0
    try:
        power_factor_4 = real_power_4 / apparent_power_4
    except ZeroDivisionError:
        power_factor_4 = 0

    

    
    results = {
        'ct0' : {
            'type'      : 'consumption',
            'power'     : real_power_0,
            'current'   : rms_current_ct0,
            'voltage'   : rms_voltage_0,
            'pf'        : power_factor_0
        },
        'ct1' : {
            'type'      : 'consumption',
            'power'     : real_power_1,
            'current'   : rms_current_ct1,
            'voltage'   : rms_voltage_1,
            'pf'        : power_factor_1 
        },
        'ct2' : {
            'type'      : 'consumption', 
            'power'     : real_power_2,
            'current'   : rms_current_ct2,
            'voltage'   : rms_voltage_2,
            'pf'        : power_factor_2
        },
        'ct3' : {
            'type'      : 'production',
            'power'     : real_power_3 * 2,         # NOTE: The 'power' and 'current' readings are multiplied by 2 for CT3 because
            'current'   : rms_current_ct3 * 2,      # CT3 is measuring my solar input, and I'm only measuring a 120V single leg when the
            'voltage'   : rms_voltage_3,            # solar input consists of two legs.  I trust that my inverter is equally distributing the
            'pf'        : power_factor_3            # load evenly over both legs, hence why I've chosen to simply double this measurement instead of
        },                                          # adding another CT sensor.  Check my implementation diagram for a visual depiction:
        'ct4' : {                                   # https://raw.githubusercontent.com/David00/rpi-power-monitor/master/docs/Sample%20Electrical%20Panel%20with%20Solar%20PV%20Input.png
            'type'      : 'consumption',
            'power'     : real_power_4,
            'current'   : rms_current_ct4,
            'voltage'   : rms_voltage_4,
            'pf'        : power_factor_4
        },
        'voltage' : rms_voltage_0,
    }

    return results

def rebuild_waves(samples, PHASECAL_0, PHASECAL_1, PHASECAL_2, PHASECAL_3, PHASECAL_4):

    # The following empty lists will hold the phase corrected voltage wave that corresponds to each individual CT sensor.
    wave_0 = []
    wave_1 = []
    wave_2 = []
    wave_3 = []
    wave_4 = []

    voltage_samples = samples['voltage']

    wave_0.append(voltage_samples[0])
    wave_1.append(voltage_samples[0])
    wave_2.append(voltage_samples[0])
    wave_3.append(voltage_samples[0])
    wave_4.append(voltage_samples[0])
    previous_point = voltage_samples[0]
    
    for current_point in voltage_samples[1:]:
        new_point_0 = previous_point + PHASECAL_0 * (current_point - previous_point)
        new_point_1 = previous_point + PHASECAL_1 * (current_point - previous_point)
        new_point_2 = previous_point + PHASECAL_2 * (current_point - previous_point)
        new_point_3 = previous_point + PHASECAL_3 * (current_point - previous_point)
        new_point_4 = previous_point + PHASECAL_4 * (current_point - previous_point)

        wave_0.append(new_point_0)
        wave_1.append(new_point_1)
        wave_2.append(new_point_2)
        wave_3.append(new_point_3)
        wave_4.append(new_point_4)

        previous_point = current_point

    rebuilt_waves = {
        'v_ct0' : wave_0,
        'v_ct1' : wave_1,
        'v_ct2' : wave_2,
        'v_ct3' : wave_3,
        'v_ct4' : wave_4,
        'voltage' : voltage_samples,
        'ct0' : samples['ct0'],
        'ct1' : samples['ct1'],
        'ct2' : samples['ct2'],
        'ct3' : samples['ct3'],
        'ct4' : samples['ct4'],
    }

    return rebuilt_waves  


def run_main():
    print("Press Ctrl-c to quit...")
    # The following empty dictionaries will hold the respective calculated values at the end of each polling cycle, which are then averaged prior to storing the value to the DB.
    solar_power_values = dict(power=[], pf=[], current=[])
    home_load_values = dict(power=[], pf=[], current=[])
    net_power_values = dict(power=[], current=[])
    ct0_dict = dict(power=[], pf=[], current=[])
    ct1_dict = dict(power=[], pf=[], current=[])
    ct2_dict = dict(power=[], pf=[], current=[])
    ct3_dict = dict(power=[], pf=[], current=[])
    ct4_dict = dict(power=[], pf=[], current=[])
    rms_voltage_values = []
    i = 0   # Counter for aggregate function
    
    while True:        
        try:
            board_voltage = get_board_voltage()    
            samples = collect_data(2000)
            poll_time = samples['time']            
            ct0_samples = samples['ct0']
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_samples = samples['ct4']
            v_samples = samples['voltage']
            rebuilt_waves = rebuild_waves(samples, ct0_phasecal, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal)
            results = calculate_power(rebuilt_waves, board_voltage) 

            # # RMS calculation for phase correction only - this is not needed after everything is tuned. The following code is used to compare the RMS power to the calculated real power. 
            # # Ideally, you want the RMS power to equal the real power when you are measuring a purely resistive load.
            # rms_power_0 = round(results['ct0']['current'] * results['ct0']['voltage'], 2)
            # rms_power_1 = round(results['ct1']['current'] * results['ct1']['voltage'], 2)
            # rms_power_2 = round(results['ct2']['current'] * results['ct2']['voltage'], 2)
            # rms_power_3 = round(results['ct3']['current'] * results['ct3']['voltage'], 2)
            # phase_corrected_power_0 = results['ct0']['power']
            # phase_corrected_power_1 = results['ct1']['power']
            # phase_corrected_power_2 = results['ct2']['power']
            # phase_corrected_power_3 = results['ct3']['power']

            # # diff is the difference between the real_power (phase corrected) compared to the simple rms power calculation.
            # # This is used to calibrate for the "unknown" phase error in each CT.  The phasecal value for each CT input should be adjusted so that diff comes as close to zero as possible.
            # diff_0 = phase_corrected_power_0 - rms_power_0
            # diff_1 = phase_corrected_power_1 - rms_power_1
            # diff_2 = phase_corrected_power_2 - rms_power_2
            # diff_3 = phase_corrected_power_3 - rms_power_3

            # Phase Corrected Results
            # print("\n")
            # print(f"CT0 Real Power: {round(results['ct0']['power'], 2):>10} W | Amps: {round(results['ct0']['current'], 2):<7} | RMS Power: {round(results['ct0']['current'] * results['ct0']['voltage'], 2):<6} W | PF: {round(results['ct0']['pf'], 5)}")
            # print(f"CT1 Real Power: {round(results['ct1']['power'], 2):>10} W | Amps: {round(results['ct1']['current'], 2):<7} | RMS Power: {round(results['ct1']['current'] * results['ct1']['voltage'], 2):<6} W | PF: {round(results['ct1']['pf'], 5)}")
            # print(f"CT2 Real Power: {round(results['ct2']['power'], 2):>10} W | Amps: {round(results['ct2']['current'], 2):<7} | RMS Power: {round(results['ct2']['current'] * results['ct2']['voltage'], 2):<6} W | PF: {round(results['ct2']['pf'], 5)}")
            # print(f"CT3 Real Power: {round(results['ct3']['power'], 2):>10} W | Amps: {round(results['ct3']['current'], 2):<7} | RMS Power: {round(results['ct3']['current'] * results['ct3']['voltage'], 2):<6} W | PF: {round(results['ct3']['pf'], 5)}")
            # print(f"CT4 Real Power: {round(results['ct4']['power'], 2):>10} W | Amps: {round(results['ct4']['current'], 2):<7} | RMS Power: {round(results['ct4']['current'] * results['ct4']['voltage'], 2):<6} W | PF: {round(results['ct4']['pf'], 5)}")
            # print(f"Line Voltage: {round(results['voltage'], 2)} V")

            # Prepare values for database storage 
            grid_0_power = results['ct0']['power']    # 200A Main (left)
            grid_1_power = results['ct1']['power']    # 200A Main (right)
            grid_2_power = results['ct2']['power']    # 100A Main (top)
            grid_4_power = results['ct4']['power']    # 100A Main (bottom)

            grid_0_current = results['ct0']['current']
            grid_1_current = results['ct1']['current']
            grid_2_current = results['ct2']['current']
            grid_4_current = results['ct4']['current']

            solar_power = results['ct3']['power']
            solar_current = results['ct3']['current']
            solar_pf = results['ct3']['pf']

            # Set solar power and current to zero if the solar power is under 20W.
            if solar_power < 20:
                solar_power = 0
                solar_current = 0
                solar_pf = 0
            
            # Determine if the system is net producing or net consuming right now by looking at the two panel mains.
            # Since the current measured is always positive, we need to add a negative sign to the amperage value if we're exporting power.
            if grid_0_power < 0:
                grid_0_current = grid_0_current * -1
            if grid_1_power < 0:
                grid_1_current = grid_1_current * -1
            if solar_power > 0:
                solar_current = solar_current * -1

            # Unless your specific panel setup matches mine exactly, the following four lines will likely need to be re-written:
            home_consumption_power = grid_2_power + grid_4_power + grid_0_power + grid_1_power + solar_power
            net_power = home_consumption_power - solar_power
            home_consumption_current = grid_2_current + grid_4_current + grid_0_current + grid_1_current - solar_current
            net_current = grid_0_current + grid_1_current + grid_2_current + grid_4_current + solar_current

            if net_power < 0:
                current_status = "Producing"                                
            else:
                current_status = "Consuming"                

            # print(f'{"Solar Output:":<20} {round(solar_power, 2):>10} W | {round(solar_current, 2):>10} A')
            # print(f'{"Home Consumption:":<20} {round(home_consumption_power, 2):>10} W | {round(home_consumption_current, 2):>10} A')
            # print(f'{"Current Status:":<20} {current_status:>10} {abs(round(net_power, 2))} W | {round(net_current, 2):>10} A')


            # Average 2 readings before sending to db
            if i < 2:
                solar_power_values['power'].append(solar_power)
                solar_power_values['current'].append(solar_current)
                solar_power_values['pf'].append(solar_pf)

                home_load_values['power'].append(home_consumption_power)
                home_load_values['current'].append(home_consumption_current)
                net_power_values['power'].append(net_power)
                net_power_values['current'].append(net_current)
                
                ct0_dict['power'].append(results['ct0']['power'])
                ct0_dict['current'].append(results['ct0']['current'])
                ct0_dict['pf'].append(results['ct0']['pf'])
                ct1_dict['power'].append(results['ct1']['power'])
                ct1_dict['current'].append(results['ct1']['current'])
                ct1_dict['pf'].append(results['ct1']['pf'])
                ct2_dict['power'].append(results['ct2']['power'])
                ct2_dict['current'].append(results['ct2']['current'])
                ct2_dict['pf'].append(results['ct2']['pf'])
                ct3_dict['power'].append(results['ct3']['power'])
                ct3_dict['current'].append(results['ct3']['current'])
                ct3_dict['pf'].append(results['ct3']['pf'])
                ct4_dict['power'].append(results['ct4']['power'])
                ct4_dict['current'].append(results['ct4']['current'])
                ct4_dict['pf'].append(results['ct4']['pf'])
                i += 1
            
            
            else:   # Calculate the average, send the result to InfluxDB, and reset the dictionaries for the next 2 sets of data.
                infl.write_to_influx(
                    solar_power_values,
                    home_load_values,
                    net_power_values, 
                    ct0_dict,
                    ct1_dict,
                    ct2_dict,
                    ct3_dict,
                    ct4_dict,
                    poll_time,
                    i)
                solar_power_values = dict(power=[], pf=[], current=[])
                home_load_values = dict(power=[], pf=[], current=[])
                net_power_values = dict(power=[], current=[])
                ct0_dict = dict(power=[], pf=[], current=[])
                ct1_dict = dict(power=[], pf=[], current=[])
                ct2_dict = dict(power=[], pf=[], current=[])
                ct3_dict = dict(power=[], pf=[], current=[])
                ct4_dict = dict(power=[], pf=[], current=[])
                i = 0
            
            sleep(0.1)

        except KeyboardInterrupt:
            infl.close_db()
            sys.exit()

if __name__ == '__main__':
    
    if len(sys.argv) > 1:
        MODE = sys.argv[1]
        if MODE == 'debug' or MODE == 'phase':
            try:
                title = sys.argv[2]
            except IndexError:
                title = None
        # Create the data/samples directory:
        os.makedirs('data/samples/')
    else:
        MODE = None

    if not MODE:
        infl.init_db()
        run_main()

    elif 'help' in MODE.lower() or '-h' in MODE.lower():
        print("\nSee the project Wiki for more detailed usage instructions: https://github.com/David00/rpi-power-monitor/wiki")
        print("""\nUsage:
            Start the program:                                  python3 power-monitor.py

            Collect raw data and build an interactive plot:     python3 power-monitor.py debug "chart title here" 

            Use the previously collected data to tune phase
            correction:                                         python3 power-monitor.py phase "chart title here"
            """)

    elif MODE == 'debug':
        # This mode is intended to take a look at the raw CT sensor data.  It will take 2000 samples from each CT sensor, plot them to a single chart, write the chart to an HTML file located in /var/www/html/, and then terminate.
        # It also stores the samples to a file located in ./data/samples/last-run.pkl so that the sample data can be read when this program is started in 'phase' mode.
        samples = collect_data(2000)
        ct0_samples = samples['ct0']
        ct1_samples = samples['ct1']
        ct2_samples = samples['ct2']
        ct3_samples = samples['ct3']
        ct4_samples = samples['ct4']
        v_samples = samples['voltage']

        # Save samples to disk
        with open('data/samples/last-run.pkl', 'wb') as f:
            pickle.dump(samples, f)

        if not title:
            title = input("Enter the title for this chart: ")

        plot_data(samples, title)        
        print("file written")

    elif MODE == 'phase':
        # This mode is intended to be used for correcting the phase error in your CT sensors. Instead of reading the CT sensors, it will open the 'last-run.pkl' file and read the contents, which
        # contain the samples from the last time the program was ran in "debug" mode. This is to save electricity so you don't need to keep your resistive load device running while you calibrate.
        # The function then continues to build 5 different variations of the raw AC voltage wave based on the ct#_phasecal variable.
        # Finally, a single chart is constructed that shows all of the raw CT data points, the "as measured" voltage wave, and the phase corrected voltage wave. The chart is written to an HTML file
        # in the webroot /var/www/html/.

        if not title:
            title = input("Enter the title for this chart: ")

        # Read last sample set to disk to perform phase correction
        try:
            with open('data/samples/last-run.pkl', 'rb') as f:
                samples = pickle.load(f)
        
        except FileNotFoundError:
            print("Please start the program in debug mode first so it can read from the CT sensors and save the data to disk.  Example:")
            print('python3.7 power-monitor.py debug "Initialize debug mode"')
            sys.exit()

        rebuilt_waves = rebuild_waves(samples, ct0_phasecal, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal)
        board_voltage = get_board_voltage()
        results = calculate_power(rebuilt_waves, board_voltage) 

        samples.update({
            'vWave_ct0' : rebuilt_waves['v_ct0'],
            'vWave_ct1' : rebuilt_waves['v_ct1'],
            'vWave_ct2' : rebuilt_waves['v_ct2'],
            'vWave_ct3' : rebuilt_waves['v_ct3'],
            'vWave_ct4' : rebuilt_waves['v_ct4'],
        })


        print(f"CT0 Real Power: {round(results['ct0']['power'] / 2, 2):>6} W | Amps: {round(results['ct0']['current'], 2):<6} | RMS Power: {round(results['ct0']['current'] * results['ct0']['voltage'], 2):<6} W | PF: {round(results['ct0']['pf'], 6)}")
        print(f"CT1 Real Power: {round(results['ct1']['power'], 2):>6} W | Amps: {round(results['ct1']['current'], 2):<6} | RMS Power: {round(results['ct1']['current'] * results['ct1']['voltage'], 2):<6} W | PF: {round(results['ct1']['pf'], 6)}")
        print(f"CT2 Real Power: {round(results['ct2']['power'], 2):>6} W | Amps: {round(results['ct2']['current'], 2):<6} | RMS Power: {round(results['ct2']['current'] * results['ct2']['voltage'], 2):<6} W | PF: {round(results['ct2']['pf'], 6)}")
        print(f"CT3 Real Power: {round(results['ct3']['power'], 2):>6} W | Amps: {round(results['ct3']['current'], 2):<6} | RMS Power: {round(results['ct3']['current'] * results['ct3']['voltage'], 2):<6} W | PF: {round(results['ct3']['pf'], 6)}")
        print(f"CT4 Real Power: {round(results['ct4']['power'], 2):>6} W | Amps: {round(results['ct4']['current'], 2):<6} | RMS Power: {round(results['ct4']['current'] * results['ct4']['voltage'], 2):<6} W | PF: {round(results['ct4']['pf'], 6)}")
        print(f"Line Voltage: {round(results['voltage'], 2)} V")

        plot_data(samples, title)        
        print("file written")


