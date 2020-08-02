#!/usr/bin/python
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
from socket import socket, AF_INET, SOCK_DGRAM
import fcntl
from prettytable import PrettyTable
import logging
from config import logger, ct_phase_correction, ct0_channel, ct1_channel, ct2_channel, ct3_channel, ct4_channel, board_voltage_channel, v_sensor_channel, ct5_channel, GRID_VOLTAGE, AC_TRANSFORMER_OUTPUT_VOLTAGE, accuracy_calibration
from calibration import check_phasecal, rebuild_wave, find_phasecal
from textwrap import dedent
from common import collect_data, readadc
from shutil import copyfile



# Tuning Variables


# Static Variables - these should not be changed by the end user
AC_voltage_ratio            = (GRID_VOLTAGE / AC_TRANSFORMER_OUTPUT_VOLTAGE) * 11   # This is a rough approximation of the ratio
# Phase Calibration - note that these items are listed in the order they are sampled.
# Changes to these values are made in config.py, in the ct_phase_correction dictionary.
ct0_phasecal = ct_phase_correction['ct0']
ct4_phasecal = ct_phase_correction['ct4']
ct1_phasecal = ct_phase_correction['ct1']
ct2_phasecal = ct_phase_correction['ct2']
ct3_phasecal = ct_phase_correction['ct3']
ct5_phasecal = ct_phase_correction['ct5']
ct0_accuracy_factor         = accuracy_calibration['ct0']
ct1_accuracy_factor         = accuracy_calibration['ct1']
ct2_accuracy_factor         = accuracy_calibration['ct2']
ct3_accuracy_factor         = accuracy_calibration['ct3']
ct4_accuracy_factor         = accuracy_calibration['ct4']
ct5_accuracy_factor         = accuracy_calibration['ct5']
AC_voltage_accuracy_factor  = accuracy_calibration['AC']



def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    now = datetime.now().stfrtime('%m-%d-%Y-%H-%M')
    filename = f'data-dump-{now}.csv'
    with open(filename, 'w') as f:
        headers = ["Sample#", "ct0", "ct1", "ct2", "ct3", "ct4", "ct5", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        # samples contains lists for each data sample. 
        for i in range(0, len(samples[0])):
            ct0_data = samples[0]
            ct1_data = samples[1]
            ct2_data = samples[2]
            ct3_data = samples[3]
            ct4_data = samples[4]
            ct5_data = samples[5]
            v_data = samples[-1]
            writer.writerow([i, ct0_data[i], ct1_data[i], ct2_data[i], ct3_data[i], ct4_data[i], ct5_data[i], v_data[i]])
    logger.info(f"CSV written to {filename}.")

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
    ct5_samples = samples['ct5']        # current samples for CT5
    v_samples_0 = samples['v_ct0']      # phase-corrected voltage wave specifically for CT0
    v_samples_1 = samples['v_ct1']      # phase-corrected voltage wave specifically for CT1
    v_samples_2 = samples['v_ct2']      # phase-corrected voltage wave specifically for CT2
    v_samples_3 = samples['v_ct3']      # phase-corrected voltage wave specifically for CT3
    v_samples_4 = samples['v_ct4']      # phase-corrected voltage wave specifically for CT4   
    v_samples_5 = samples['v_ct5']      # phase-corrected voltage wave specifically for CT5   

    # Variable Initialization    
    sum_inst_power_ct0 = 0
    sum_inst_power_ct1 = 0
    sum_inst_power_ct2 = 0
    sum_inst_power_ct3 = 0
    sum_inst_power_ct4 = 0
    sum_inst_power_ct5 = 0
    sum_squared_current_ct0 = 0 
    sum_squared_current_ct1 = 0
    sum_squared_current_ct2 = 0
    sum_squared_current_ct3 = 0
    sum_squared_current_ct4 = 0
    sum_squared_current_ct5 = 0
    sum_raw_current_ct0 = 0
    sum_raw_current_ct1 = 0
    sum_raw_current_ct2 = 0
    sum_raw_current_ct3 = 0
    sum_raw_current_ct4 = 0
    sum_raw_current_ct5 = 0
    sum_squared_voltage_0 = 0
    sum_squared_voltage_1 = 0
    sum_squared_voltage_2 = 0
    sum_squared_voltage_3 = 0
    sum_squared_voltage_4 = 0
    sum_squared_voltage_5 = 0
    sum_raw_voltage_0 = 0
    sum_raw_voltage_1 = 0
    sum_raw_voltage_2 = 0
    sum_raw_voltage_3 = 0
    sum_raw_voltage_4 = 0
    sum_raw_voltage_5 = 0

    # Scaling factors
    vref = board_voltage / 1024
    ct0_scaling_factor = vref * 100 * ct0_accuracy_factor
    ct1_scaling_factor = vref * 100 * ct1_accuracy_factor
    ct2_scaling_factor = vref * 100 * ct2_accuracy_factor
    ct3_scaling_factor = vref * 100 * ct3_accuracy_factor
    ct4_scaling_factor = vref * 100 * ct4_accuracy_factor
    ct5_scaling_factor = vref * 100 * ct5_accuracy_factor
    voltage_scaling_factor = vref * AC_voltage_ratio * AC_voltage_accuracy_factor
    

    num_samples = len(v_samples_0)
    
    for i in range(0, num_samples):
        ct0 = (int(ct0_samples[i]))
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        ct4 = (int(ct4_samples[i]))
        ct5 = (int(ct5_samples[i]))
        voltage_0 = (int(v_samples_0[i]))
        voltage_1 = (int(v_samples_1[i]))
        voltage_2 = (int(v_samples_2[i]))
        voltage_3 = (int(v_samples_3[i]))
        voltage_4 = (int(v_samples_4[i]))
        voltage_5 = (int(v_samples_5[i]))

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct0 += ct0
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_current_ct4 += ct4
        sum_raw_current_ct5 += ct5
        sum_raw_voltage_0 += voltage_0
        sum_raw_voltage_1 += voltage_1
        sum_raw_voltage_2 += voltage_2
        sum_raw_voltage_3 += voltage_3
        sum_raw_voltage_4 += voltage_4
        sum_raw_voltage_5 += voltage_5


        # Calculate instant power for each ct sensor
        inst_power_ct0 = ct0 * voltage_0
        inst_power_ct1 = ct1 * voltage_1
        inst_power_ct2 = ct2 * voltage_2
        inst_power_ct3 = ct3 * voltage_3
        inst_power_ct4 = ct4 * voltage_4
        inst_power_ct5 = ct5 * voltage_5
        sum_inst_power_ct0 += inst_power_ct0
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3
        sum_inst_power_ct4 += inst_power_ct4
        sum_inst_power_ct5 += inst_power_ct5

        # Squared voltage
        squared_voltage_0 = voltage_0 * voltage_0
        squared_voltage_1 = voltage_1 * voltage_1
        squared_voltage_2 = voltage_2 * voltage_2
        squared_voltage_3 = voltage_3 * voltage_3
        squared_voltage_4 = voltage_4 * voltage_4
        squared_voltage_5 = voltage_5 * voltage_5
        sum_squared_voltage_0 += squared_voltage_0
        sum_squared_voltage_1 += squared_voltage_1
        sum_squared_voltage_2 += squared_voltage_2
        sum_squared_voltage_3 += squared_voltage_3
        sum_squared_voltage_4 += squared_voltage_4
        sum_squared_voltage_5 += squared_voltage_5

        # Squared current
        sq_ct0 = ct0 * ct0
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        sq_ct4 = ct4 * ct4
        sq_ct5 = ct5 * ct5
        
        sum_squared_current_ct0 += sq_ct0
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3
        sum_squared_current_ct4 += sq_ct4
        sum_squared_current_ct5 += sq_ct5

    avg_raw_current_ct0 = sum_raw_current_ct0 / num_samples
    avg_raw_current_ct1 = sum_raw_current_ct1 / num_samples
    avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
    avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
    avg_raw_current_ct4 = sum_raw_current_ct4 / num_samples
    avg_raw_current_ct5 = sum_raw_current_ct5 / num_samples
    avg_raw_voltage_0 = sum_raw_voltage_0 / num_samples
    avg_raw_voltage_1 = sum_raw_voltage_1 / num_samples
    avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
    avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
    avg_raw_voltage_4 = sum_raw_voltage_4 / num_samples
    avg_raw_voltage_5 = sum_raw_voltage_5 / num_samples
    
    real_power_0 = ((sum_inst_power_ct0 / num_samples) - (avg_raw_current_ct0 * avg_raw_voltage_0))  * ct0_scaling_factor * voltage_scaling_factor
    real_power_1 = ((sum_inst_power_ct1 / num_samples) - (avg_raw_current_ct1 * avg_raw_voltage_1))  * ct1_scaling_factor * voltage_scaling_factor 
    real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor 
    real_power_4 = ((sum_inst_power_ct4 / num_samples) - (avg_raw_current_ct4 * avg_raw_voltage_4))  * ct4_scaling_factor * voltage_scaling_factor 
    real_power_5 = ((sum_inst_power_ct5 / num_samples) - (avg_raw_current_ct5 * avg_raw_voltage_5))  * ct5_scaling_factor * voltage_scaling_factor 

    mean_square_current_ct0 = sum_squared_current_ct0 / num_samples 
    mean_square_current_ct1 = sum_squared_current_ct1 / num_samples 
    mean_square_current_ct2 = sum_squared_current_ct2 / num_samples 
    mean_square_current_ct3 = sum_squared_current_ct3 / num_samples 
    mean_square_current_ct4 = sum_squared_current_ct4 / num_samples 
    mean_square_current_ct5 = sum_squared_current_ct5 / num_samples 
    mean_square_voltage_0 = sum_squared_voltage_0 / num_samples
    mean_square_voltage_1 = sum_squared_voltage_1 / num_samples
    mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
    mean_square_voltage_3 = sum_squared_voltage_3 / num_samples
    mean_square_voltage_4 = sum_squared_voltage_4 / num_samples
    mean_square_voltage_5 = sum_squared_voltage_5 / num_samples

    rms_current_ct0 = sqrt(mean_square_current_ct0 - (avg_raw_current_ct0 * avg_raw_current_ct0)) * ct0_scaling_factor
    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
    rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor
    rms_current_ct5 = sqrt(mean_square_current_ct5 - (avg_raw_current_ct5 * avg_raw_current_ct5)) * ct5_scaling_factor
    rms_voltage_0     = sqrt(mean_square_voltage_0 - (avg_raw_voltage_0 * avg_raw_voltage_0)) * voltage_scaling_factor
    rms_voltage_1     = sqrt(mean_square_voltage_1 - (avg_raw_voltage_1 * avg_raw_voltage_1)) * voltage_scaling_factor
    rms_voltage_2     = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
    rms_voltage_3     = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor
    rms_voltage_4     = sqrt(mean_square_voltage_4 - (avg_raw_voltage_4 * avg_raw_voltage_4)) * voltage_scaling_factor
    rms_voltage_5     = sqrt(mean_square_voltage_5 - (avg_raw_voltage_5 * avg_raw_voltage_5)) * voltage_scaling_factor

    # Power Factor
    apparent_power_0 = rms_voltage_0 * rms_current_ct0
    apparent_power_1 = rms_voltage_1 * rms_current_ct1
    apparent_power_2 = rms_voltage_2 * rms_current_ct2
    apparent_power_3 = rms_voltage_3 * rms_current_ct3
    apparent_power_4 = rms_voltage_4 * rms_current_ct4
    apparent_power_5 = rms_voltage_5 * rms_current_ct5
    
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
    try:
        power_factor_5 = real_power_5 / apparent_power_5
    except ZeroDivisionError:
        power_factor_5 = 0
    

    
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
            'power'     : real_power_3,         
            'current'   : rms_current_ct3,
            'voltage'   : rms_voltage_3,            
            'pf'        : power_factor_3            
        },                                          
        'ct4' : {                                   
            'type'      : 'consumption',
            'power'     : real_power_4,
            'current'   : rms_current_ct4,
            'voltage'   : rms_voltage_4,
            'pf'        : power_factor_4
        },
        'ct5' : {                                   
            'type'      : 'consumption',
            'power'     : real_power_5,
            'current'   : rms_current_ct5,
            'voltage'   : rms_voltage_5,
            'pf'        : power_factor_5
        },
        'voltage' : rms_voltage_0,
    }

    return results

def rebuild_waves(samples, PHASECAL_0, PHASECAL_1, PHASECAL_2, PHASECAL_3, PHASECAL_4, PHASECAL_5):

    # The following empty lists will hold the phase corrected voltage wave that corresponds to each individual CT sensor.
    wave_0 = []
    wave_1 = []
    wave_2 = []
    wave_3 = []
    wave_4 = []
    wave_5 = []

    voltage_samples = samples['voltage']

    wave_0.append(voltage_samples[0])
    wave_1.append(voltage_samples[0])
    wave_2.append(voltage_samples[0])
    wave_3.append(voltage_samples[0])
    wave_4.append(voltage_samples[0])
    wave_5.append(voltage_samples[0])
    previous_point = voltage_samples[0]
    
    for current_point in voltage_samples[1:]:
        new_point_0 = previous_point + PHASECAL_0 * (current_point - previous_point)
        new_point_1 = previous_point + PHASECAL_1 * (current_point - previous_point)
        new_point_2 = previous_point + PHASECAL_2 * (current_point - previous_point)
        new_point_3 = previous_point + PHASECAL_3 * (current_point - previous_point)
        new_point_4 = previous_point + PHASECAL_4 * (current_point - previous_point)
        new_point_5 = previous_point + PHASECAL_5 * (current_point - previous_point)

        wave_0.append(new_point_0)
        wave_1.append(new_point_1)
        wave_2.append(new_point_2)
        wave_3.append(new_point_3)
        wave_4.append(new_point_4)
        wave_5.append(new_point_5)

        previous_point = current_point

    rebuilt_waves = {
        'v_ct0' : wave_0,
        'v_ct1' : wave_1,
        'v_ct2' : wave_2,
        'v_ct3' : wave_3,
        'v_ct4' : wave_4,
        'v_ct5' : wave_5,
        'voltage' : voltage_samples,
        'ct0' : samples['ct0'],
        'ct1' : samples['ct1'],
        'ct2' : samples['ct2'],
        'ct3' : samples['ct3'],
        'ct4' : samples['ct4'],
        'ct5' : samples['ct5'],
    }

    return rebuilt_waves


def run_main():
    logger.info("Press Ctrl-c to quit...")
    # The following empty dictionaries will hold the respective calculated values at the end of each polling cycle, which are then averaged prior to storing the value to the DB.
    solar_power_values = dict(power=[], pf=[], current=[])
    home_load_values = dict(power=[], pf=[], current=[])
    net_power_values = dict(power=[], current=[])
    ct0_dict = dict(power=[], pf=[], current=[])
    ct1_dict = dict(power=[], pf=[], current=[])
    ct2_dict = dict(power=[], pf=[], current=[])
    ct3_dict = dict(power=[], pf=[], current=[])
    ct4_dict = dict(power=[], pf=[], current=[])
    ct5_dict = dict(power=[], pf=[], current=[])
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
            ct5_samples = samples['ct5']
            v_samples = samples['voltage']
            rebuilt_waves = rebuild_waves(samples, ct0_phasecal, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal, ct5_phasecal)
            results = calculate_power(rebuilt_waves, board_voltage) 

            # # RMS calculation for phase correction only - this is not needed after everything is tuned. The following code is used to compare the RMS power to the calculated real power. 
            # # Ideally, you want the RMS power to equal the real power when you are measuring a purely resistive load.
            # rms_power_0 = round(results['ct0']['current'] * results['ct0']['voltage'], 2)  # AKA apparent power
            # rms_power_1 = round(results['ct1']['current'] * results['ct1']['voltage'], 2)  # AKA apparent power
            # rms_power_2 = round(results['ct2']['current'] * results['ct2']['voltage'], 2)  # AKA apparent power
            # rms_power_3 = round(results['ct3']['current'] * results['ct3']['voltage'], 2)  # AKA apparent power
            # rms_power_4 = round(results['ct4']['current'] * results['ct4']['voltage'], 2)  # AKA apparent power
            # rms_power_5 = round(results['ct5']['current'] * results['ct5']['voltage'], 2)  # AKA apparent power
            # phase_corrected_power_0 = results['ct0']['power']
            # phase_corrected_power_1 = results['ct1']['power']
            # phase_corrected_power_2 = results['ct2']['power']
            # phase_corrected_power_3 = results['ct3']['power']
            # phase_corrected_power_4 = results['ct4']['power']
            # phase_corrected_power_5 = results['ct5']['power']

            # # diff is the difference between the real_power (phase corrected) compared to the simple rms power calculation.
            # # This is used to calibrate for the "unknown" phase error in each CT.  The phasecal value for each CT input should be adjusted so that diff comes as close to zero as possible.
            # diff_0 = phase_corrected_power_0 - rms_power_0
            # diff_1 = phase_corrected_power_1 - rms_power_1
            # diff_2 = phase_corrected_power_2 - rms_power_2
            # diff_3 = phase_corrected_power_3 - rms_power_3
            # diff_4 = phase_corrected_power_4 - rms_power_4
            # diff_5 = phase_corrected_power_5 - rms_power_5

            # Phase Corrected Results
            # logger.debug("\n")
            # logger.debug(f"CT0 Real Power: {round(results['ct0']['power'], 2):>10} W | Amps: {round(results['ct0']['current'], 2):<7} | RMS Power: {round(results['ct0']['current'] * results['ct0']['voltage'], 2):<6} W | PF: {round(results['ct0']['pf'], 5)}")
            # logger.debug(f"CT1 Real Power: {round(results['ct1']['power'], 2):>10} W | Amps: {round(results['ct1']['current'], 2):<7} | RMS Power: {round(results['ct1']['current'] * results['ct1']['voltage'], 2):<6} W | PF: {round(results['ct1']['pf'], 5)}")
            # logger.debug(f"CT2 Real Power: {round(results['ct2']['power'], 2):>10} W | Amps: {round(results['ct2']['current'], 2):<7} | RMS Power: {round(results['ct2']['current'] * results['ct2']['voltage'], 2):<6} W | PF: {round(results['ct2']['pf'], 5)}")
            # logger.debug(f"CT3 Real Power: {round(results['ct3']['power'], 2):>10} W | Amps: {round(results['ct3']['current'], 2):<7} | RMS Power: {round(results['ct3']['current'] * results['ct3']['voltage'], 2):<6} W | PF: {round(results['ct3']['pf'], 5)}")
            # logger.debug(f"CT4 Real Power: {round(results['ct4']['power'], 2):>10} W | Amps: {round(results['ct4']['current'], 2):<7} | RMS Power: {round(results['ct4']['current'] * results['ct4']['voltage'], 2):<6} W | PF: {round(results['ct4']['pf'], 5)}")
            # logger.debug(f"CT5 Real Power: {round(results['ct5']['power'], 2):>10} W | Amps: {round(results['ct5']['current'], 2):<7} | RMS Power: {round(results['ct5']['current'] * results['ct5']['voltage'], 2):<6} W | PF: {round(results['ct5']['pf'], 5)}")
            # logger.debug(f"Line Voltage: {round(results['voltage'], 2)} V")

            # Prepare values for database storage 
            grid_0_power = results['ct0']['power']    # 200A Main (left)
            grid_1_power = results['ct1']['power']    # 200A Main (right)
            grid_2_power = results['ct2']['power']    # 100A Main (top)
            grid_4_power = results['ct4']['power']    # 100A Main (bottom)
            grid_5_power = results['ct5']['power']    # Unused

            grid_0_current = results['ct0']['current']
            grid_1_current = results['ct1']['current']
            grid_2_current = results['ct2']['current']
            grid_4_current = results['ct4']['current']
            grid_5_current = results['ct5']['current']

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
                ct5_dict['power'].append(results['ct5']['power'])
                ct5_dict['current'].append(results['ct5']['current'])
                ct5_dict['pf'].append(results['ct5']['pf'])
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
                    ct5_dict,
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
                ct5_dict = dict(power=[], pf=[], current=[])
                i = 0

                if logger.handlers[0].level == 10:
                    t = PrettyTable(['', 'CT0', 'CT1', 'CT2', 'CT3', 'CT4', 'CT5'])
                    t.add_row(['Watts', round(results['ct0']['power'], 3), round(results['ct1']['power'], 3), round(results['ct2']['power'], 3), round(results['ct3']['power'], 3), round(results['ct4']['power'], 3), round(results['ct5']['power'], 3)])
                    t.add_row(['Current', round(results['ct0']['current'], 3), round(results['ct1']['current'], 3), round(results['ct2']['current'], 3), round(results['ct3']['current'], 3), round(results['ct4']['current'], 3), round(results['ct5']['current'], 3)])
                    t.add_row(['P.F.', round(results['ct0']['pf'], 3), round(results['ct1']['pf'], 3), round(results['ct2']['pf'], 3), round(results['ct3']['pf'], 3), round(results['ct4']['pf'], 3), round(results['ct5']['pf'], 3)])
                    t.add_row(['Voltage', round(results['voltage'], 3), '', '', '', '', ''])
                    s = t.get_string()
                    logger.debug('\n' + s)

            #sleep(0.1)

        except KeyboardInterrupt:
            infl.close_db()
            sys.exit()

def print_results(results):
    t = PrettyTable(['', 'CT0', 'CT1', 'CT2', 'CT3', 'CT4', 'CT5'])
    t.add_row(['Watts', round(results['ct0']['power'], 3), round(results['ct1']['power'], 3), round(results['ct2']['power'], 3), round(results['ct3']['power'], 3), round(results['ct4']['power'], 3), round(results['ct5']['power'], 3)])
    t.add_row(['Current', round(results['ct0']['current'], 3), round(results['ct1']['current'], 3), round(results['ct2']['current'], 3), round(results['ct3']['current'], 3), round(results['ct4']['current'], 3), round(results['ct5']['current'], 3)])
    t.add_row(['P.F.', round(results['ct0']['pf'], 3), round(results['ct1']['pf'], 3), round(results['ct2']['pf'], 3), round(results['ct3']['pf'], 3), round(results['ct4']['pf'], 3), round(results['ct5']['pf'], 3)])
    t.add_row(['Voltage', round(results['voltage'], 3), '', '', '', '', ''])
    s = t.get_string()
    logger.debug(s)


def get_ip():
    # This function acquires your Pi's local IP address for use in providing the user with a copy-able link to view the charts.
    # It does so by trying to connect to a non-existent private IP address, but in doing so, it is able to detect the IP address associated with the default route.
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = None
    finally:
        s.close()
    return IP


if __name__ == '__main__':

    # Backup config.py file
    try:
        copyfile('config.py', 'config.py.backup')
    except FileNotFoundError:
        logger.info("Could not create a backup of config.py file.")
    
    if len(sys.argv) > 1:
        MODE = sys.argv[1]
        if MODE == 'debug' or MODE == 'phase':
            try:
                title = sys.argv[2]
            except IndexError:
                title = None
        # Create the data/samples directory:
        try:
            os.makedirs('data/samples/')
        except FileExistsError:
            pass
    else:
        MODE = None

    if not MODE:
        # Try to establish a connection to the DB for 5 seconds:
        x = 0
        connection_established = False
        while x < 5:
            try:
                infl.init_db()
                connection_established = True
                break
            except:
                sleep(1)
                x += 1

        if not connection_established:
            raise Exception("Could not connect to InfluxDB. Check that the container is running!")

        run_main()

    else:
        # Program launched in one of the non-main modes. Increase logging level.
        logger.setLevel(logging.DEBUG)
        logger.handlers[0].setLevel(logging.DEBUG)      
        if 'help' in MODE.lower() or '-h' in MODE.lower():

            logger.info("See the project Wiki for more detailed usage instructions: https://github.com/David00/rpi-power-monitor/wiki")
            logger.info(dedent("""Usage:
                Start the program:                                  python3 power-monitor.py

                Collect raw data and build an interactive plot:     python3 power-monitor.py debug "chart title here" 

                Launch interactive phase correction mode:           python3 power-monitor.py phase

                Start the program like normal, but print all        python3 power-monitor.py terminal
                readings to the terminal window
                """))

        if MODE.lower() == 'debug':
            # This mode is intended to take a look at the raw CT sensor data.  It will take 2000 samples from each CT sensor, plot them to a single chart, write the chart to an HTML file located in /var/www/html/, and then terminate.
            # It also stores the samples to a file located in ./data/samples/last-debug.pkl so that the sample data can be read when this program is started in 'phase' mode.
            samples = collect_data(2000)
            ct0_samples = samples['ct0']
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_samples = samples['ct4']
            ct5_samples = samples['ct5']
            v_samples = samples['voltage']

            # Save samples to disk
            with open('data/samples/last-debug.pkl', 'wb') as f:
                pickle.dump(samples, f)

            if not title:
                title = input("Enter the title for this chart: ")

            plot_data(samples, title)        
            ip = get_ip()
            if ip:
                logger.info(f"Chart created! Visit http://{ip}/{title}.html to view the chart. Or, simply visit http://{ip} to view all the charts created using 'debug' and/or 'phase' mode.")
            else:
                logger.info("Chart created! I could not determine the IP address of this machine. Visit your device's IP address in a webrowser to view the list of charts you've created using 'debug' and/or 'phase' mode.")

        if MODE.lower() == 'phase':
            # This mode is intended to be used for correcting the phase error in your CT sensors. Please ensure that you have a purely resistive load running through your CT sensors - that means no electric fans and no digital circuitry!

            PF_ROUNDING_DIGITS = 3      # This variable controls how many decimal places the PF will be rounded

            while True:
                try:    
                    ct_num = int(input("\nWhich CT number are you calibrating? Enter the number of the CT label [0 - 5]: "))
                    if ct_num not in range(0, 6):
                        logger.error("Please choose from CT numbers 0, 1, 2, 3, 4, or 5.")
                    else:
                        ct_selection = f'ct{ct_num}'
                        break
                except ValueError:
                    logger.error("Please enter an integer! Acceptable choices are: 0, 1, 2, 3, 4, 5.")

            
            cont = input(dedent(f"""
                #------------------------------------------------------------------------------#
                # IMPORTANT: Make sure that current transformer {ct_selection} is installed over          #
                #            a purely resistive load and that the load is turned on            #
                #            before continuing with the calibration!                           #
                #------------------------------------------------------------------------------#

                Continue? [y/yes/n/no]: """))
                

            if cont.lower() in ['n', 'no']:
                logger.info("\nCalibration Aborted.\n")
                sys.exit()

            samples = collect_data(2000)
            rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], ct_phase_correction[ct_selection])
            board_voltage = get_board_voltage()
            results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)

            # Get the current power factor and check to make sure it is not negative. If it is, the CT is installed opposite to how it should be.
            pf = results['pf']
            initial_pf = pf  
            if pf < 0:
                logger.info(dedent('''
                    Current transformer is installed backwards. Please reverse the direction that it is attached to your load. \n
                    (Unclip it from your conductor, and clip it on so that the current flows the opposite direction from the CT's perspective) \n
                    Press ENTER to continue when you've reversed your CT.'''))
                input("[ENTER]")
                # Check to make sure the CT was reversed properly by taking another batch of samples/calculations:
                samples = collect_data(2000)
                rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], 1)
                board_voltage = get_board_voltage()
                results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)
                pf = results['pf']
                if pf < 0:
                    logger.info(dedent("""It still looks like the current transformer is installed backwards.  Are you sure this is a resistive load?\n
                        Please consult the project documentation on https://github.com/david00/rpi-power-monitor/wiki and try again."""))
                    sys.exit()

            # Initialize phasecal values
            new_phasecal = ct_phase_correction[ct_selection]
            previous_pf = 0
            new_pf = pf

            samples = collect_data(2000)
            board_voltage = get_board_voltage()
            best_pfs = find_phasecal(samples, ct_selection, PF_ROUNDING_DIGITS, board_voltage)
            avg_phasecal = sum([x['cal'] for x in best_pfs]) / len([x['cal'] for x in best_pfs])
            logger.info(f"Please update the value for {ct_selection} in ct_phase_correction in config.py with the following value: {round(avg_phasecal, 8)}")

            report_title = f"{ct_selection}-phase-correction-result"
            logger.info("Please wait... building HTML plot...")
            # Get new set of samples using recommended phasecal value
            samples = collect_data(2000)
            rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], avg_phasecal)

            plot_data(rebuilt_wave, report_title, ct_selection)
            logger.info(f"file written to {report_title}.html")

        if MODE.lower() == "terminal":
            # This mode will read the sensors, perform the calculations, and print the wattage, current, power factor, and voltage to the terminal.
            # Data is stored to the database in this mode!
            logger.debug("Starting program in terminal mode")
            infl.init_db()
            run_main()

