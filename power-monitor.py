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

# TODO
# 1. Build a dynamic Phase Correction algorithm depending on how many inputs are in use


# Tuning Variables
ct0_accuracy_factor         = 0.955
ct1_accuracy_factor         = 0.9321
ct2_accuracy_factor         = 0.9751
ct3_accuracy_factor         = 0.9734
ct4_accuracy_factor         = 1         # Not yet implemented.
AC_voltage_accuracy_factor  = 1.075

# Phase Calibration - note that these items are listed in the order they are sampled.
ct0_phasecal = 1.489     # Calculated  1.5              # TUNED - error between real power and rms power is about -0.72W with a 3.4kW load
ct4_phasecal = 1.333     # Calculated 1.3333            # Not yet implemented.
ct1_phasecal = 0.851     # Calculated 1.166667          # TUNED - error between real power and rms power is about -0.446W with a 3.4kW load
ct2_phasecal = 1.475     # Calculated 1.166667          # TUNED - error between real power and rms power is about -0.526W with a 3.4kW load
ct3_phasecal = 1.775     # Calculated 1.3333            # TUNED - error between real power and rms power is about -0.52W with a 3.4kW load

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
    sum_squared_current_ct0 = 0 
    sum_squared_current_ct1 = 0
    sum_squared_current_ct2 = 0
    sum_squared_current_ct3 = 0
    sum_raw_current_ct0 = 0
    sum_raw_current_ct1 = 0
    sum_raw_current_ct2 = 0
    sum_raw_current_ct3 = 0
    sum_squared_voltage_0 = 0
    sum_squared_voltage_1 = 0
    sum_squared_voltage_2 = 0
    sum_squared_voltage_3 = 0
    sum_raw_voltage_0 = 0
    sum_raw_voltage_1 = 0
    sum_raw_voltage_2 = 0
    sum_raw_voltage_3 = 0

    # Scaling factors
    ct0_scaling_factor = (board_voltage / 1024) * 100 * ct0_accuracy_factor
    ct1_scaling_factor = (board_voltage / 1024) * 100 * ct1_accuracy_factor
    ct2_scaling_factor = (board_voltage / 1024) * 100 * ct2_accuracy_factor
    ct3_scaling_factor = (board_voltage / 1024) * 100 * ct3_accuracy_factor
    voltage_scaling_factor = (board_voltage / 1024) * 126.5 * AC_voltage_accuracy_factor

    num_samples = len(v_samples_0)
    
    for i in range(0, num_samples):
        ct0 = (int(ct0_samples[i]))
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        voltage_0 = (int(v_samples_0[i]))      
        voltage_1 = (int(v_samples_1[i]))      
        voltage_2 = (int(v_samples_2[i]))      
        voltage_3 = (int(v_samples_3[i]))      

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct0 += ct0
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_voltage_0 += voltage_0
        sum_raw_voltage_1 += voltage_1
        sum_raw_voltage_2 += voltage_2
        sum_raw_voltage_3 += voltage_3


        # Calculate instant power for each ct sensor
        inst_power_ct0 = ct0 * voltage_0 * 2
        inst_power_ct1 = ct1 * voltage_1
        inst_power_ct2 = ct2 * voltage_2
        inst_power_ct3 = ct3 * voltage_3
        sum_inst_power_ct0 += inst_power_ct0
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3

        # Squared voltage
        squared_voltage_0 = voltage_0 * voltage_0
        squared_voltage_1 = voltage_1 * voltage_1  
        squared_voltage_2 = voltage_2 * voltage_2  
        squared_voltage_3 = voltage_3 * voltage_3  
        sum_squared_voltage_0 += squared_voltage_0
        sum_squared_voltage_1 += squared_voltage_1
        sum_squared_voltage_2 += squared_voltage_2
        sum_squared_voltage_3 += squared_voltage_3

        # Squared current
        sq_ct0 = ct0 * ct0
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        
        sum_squared_current_ct0 += sq_ct0
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3

    avg_raw_current_ct0 = sum_raw_current_ct0 / num_samples
    avg_raw_current_ct1 = sum_raw_current_ct1 / num_samples
    avg_raw_current_ct2 = sum_raw_current_ct2 / num_samples
    avg_raw_current_ct3 = sum_raw_current_ct3 / num_samples
    avg_raw_voltage_0 = sum_raw_voltage_0 / num_samples
    avg_raw_voltage_1 = sum_raw_voltage_1 / num_samples
    avg_raw_voltage_2 = sum_raw_voltage_2 / num_samples
    avg_raw_voltage_3 = sum_raw_voltage_3 / num_samples
    

    real_power_0 = ((sum_inst_power_ct0 / num_samples) - (avg_raw_current_ct0 * avg_raw_voltage_0 * 2))  * ct0_scaling_factor * voltage_scaling_factor
    real_power_1 = ((sum_inst_power_ct1 / num_samples) - (avg_raw_current_ct1 * avg_raw_voltage_1))  * ct1_scaling_factor * voltage_scaling_factor 
    real_power_2 = ((sum_inst_power_ct2 / num_samples) - (avg_raw_current_ct2 * avg_raw_voltage_2))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / num_samples) - (avg_raw_current_ct3 * avg_raw_voltage_3))  * ct3_scaling_factor * voltage_scaling_factor 

    mean_square_current_ct0 = sum_squared_current_ct0 / num_samples 
    mean_square_current_ct1 = sum_squared_current_ct1 / num_samples 
    mean_square_current_ct2 = sum_squared_current_ct2 / num_samples 
    mean_square_current_ct3 = sum_squared_current_ct3 / num_samples 
    mean_square_voltage_0 = sum_squared_voltage_0 / num_samples
    mean_square_voltage_1 = sum_squared_voltage_1 / num_samples
    mean_square_voltage_2 = sum_squared_voltage_2 / num_samples
    mean_square_voltage_3 = sum_squared_voltage_3 / num_samples

    rms_current_ct0 = sqrt(mean_square_current_ct0 - (avg_raw_current_ct0 * avg_raw_current_ct0)) * ct0_scaling_factor
    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
    rms_voltage_0     = sqrt(mean_square_voltage_0 - (avg_raw_voltage_0 * avg_raw_voltage_0)) * voltage_scaling_factor
    rms_voltage_1     = sqrt(mean_square_voltage_1 - (avg_raw_voltage_1 * avg_raw_voltage_1)) * voltage_scaling_factor
    rms_voltage_2     = sqrt(mean_square_voltage_2 - (avg_raw_voltage_2 * avg_raw_voltage_2)) * voltage_scaling_factor
    rms_voltage_3     = sqrt(mean_square_voltage_3 - (avg_raw_voltage_3 * avg_raw_voltage_3)) * voltage_scaling_factor

    # Power Factor
    apparent_power_0 = rms_voltage_0 * rms_current_ct0        
    apparent_power_1 = rms_voltage_1 * rms_current_ct1        
    apparent_power_2 = rms_voltage_2 * rms_current_ct2        
    apparent_power_3 = rms_voltage_3 * rms_current_ct3        
    power_factor_0 = real_power_0 / apparent_power_0 / 2
    power_factor_1 = real_power_1 / apparent_power_1
    power_factor_2 = real_power_2 / apparent_power_2
    power_factor_3 = real_power_3 / apparent_power_3


    
    results = {
        'ct0' : {
            'type'      : 'production',
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
            'type'      : 'consumption',
            'power'     : real_power_3,
            'current'   : rms_current_ct3,
            'voltage'   : rms_voltage_3,
            'pf'        : power_factor_3
        },
        'voltage' : rms_voltage_0,
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

def rebuild_waves(samples, PHASECAL_0, PHASECAL_1, PHASECAL_2, PHASECAL_3, PHASECAL_4):

    wave_0 = []     # This will hold the phase adjusted wave for Ct0    
    wave_1 = []     # This will hold the phase adjusted wave for Ct1
    wave_2 = []     # This will hold the phase adjusted wave for Ct2
    wave_3 = []     # This will hold the phase adjusted wave for Ct3
    wave_4 = []     # This will hold the phase adjusted wave for Ct4

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
            #starttime = timeit.default_timer()
            samples = collect_data(2000)
            poll_time = samples['time']
            #stop = timeit.default_timer() - starttime
            #print(f"Collected {len(samples['ct0']) * (len(samples)-1)} samples in {round(stop,4)} seconds at {spi.max_speed_hz} Hz.")
            
            ct0_samples = samples['ct0']
            ct1_samples = samples['ct1']
            ct2_samples = samples['ct2']
            ct3_samples = samples['ct3']
            ct4_samples = samples['ct4']
            v_samples = samples['voltage']

            rebuilt_waves = rebuild_waves(samples, ct0_phasecal, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal)
            results = calculate_power(rebuilt_waves, board_voltage) 

            # RMS calculation for phase correction only - this is not needed after everything is tuned.
            rms_power_0 = round(results['ct0']['current'] * results['ct0']['voltage'], 2)
            rms_power_1 = round(results['ct1']['current'] * results['ct1']['voltage'], 2)
            rms_power_2 = round(results['ct2']['current'] * results['ct2']['voltage'], 2)
            rms_power_3 = round(results['ct3']['current'] * results['ct3']['voltage'], 2)

            phase_corrected_power_0 = results['ct0']['power'] / 2
            phase_corrected_power_1 = results['ct1']['power']
            phase_corrected_power_2 = results['ct2']['power']
            phase_corrected_power_3 = results['ct3']['power']

            # diff is the difference between the real_power (phase corrected) compared to the simple rms power calculation.
            # This is used to calibrate for the "unknown" phase error in each CT.  The phasecal value for each CT input should be adjusted so that diff comes as close to zero as possible.
            diff_0 = phase_corrected_power_0 - rms_power_0
            diff_1 = phase_corrected_power_1 - rms_power_1
            diff_2 = phase_corrected_power_2 - rms_power_2
            diff_3 = phase_corrected_power_3 - rms_power_3

            # Phase Corrected Results
            print("\n")
            print(f"CT0 Real Power: {round(results['ct0']['power'] / 2, 2):>6} W | Amps: {round(results['ct0']['current'], 2):<6} | RMS Power: {round(results['ct0']['current'] * results['ct0']['voltage'], 2):<6} W | PF: {round(results['ct0']['pf'], 4)}")
            print(f"CT1 Real Power: {round(results['ct1']['power'], 2):>6} W | Amps: {round(results['ct1']['current'], 2):<6} | RMS Power: {round(results['ct1']['current'] * results['ct1']['voltage'], 2):<6} W | PF: {round(results['ct1']['pf'], 4)}")
            print(f"CT2 Real Power: {round(results['ct2']['power'], 2):>6} W | Amps: {round(results['ct2']['current'], 2):<6} | RMS Power: {round(results['ct2']['current'] * results['ct2']['voltage'], 2):<6} W | PF: {round(results['ct2']['pf'], 4)}")
            print(f"CT3 Real Power: {round(results['ct3']['power'], 2):>6} W | Amps: {round(results['ct3']['current'], 2):<6} | RMS Power: {round(results['ct3']['current'] * results['ct3']['voltage'], 2):<6} W | PF: {round(results['ct3']['pf'], 4)}")
            print(f"Line Voltage: {round(results['voltage'], 2)} V")
            

            #print(f"Difference between calculated real power and rms power: {diff_0} W")
            
            # solar_power      = results['ct0']['power']
            # solar_current    = results['ct0']['current']
            # subpanel_power   = results['ct1']['power']
            # subpanel_current = results['ct1']['current']
            # l_main_power     = results['ct2']['power']
            # l_main_current   = results['ct2']['current']
            # r_main_power     = results['ct3']['power']
            # r_main_current   = results['ct3']['current']
            
            # if solar_current < 0.6:
            #     solar_current = solar_current - 0.29

            # if l_main_power < 0 and r_main_power < 0:
            #     current_status = 'Producing'
            
            # else:
            #     current_status = 'Consuming'

            # power_exported = abs(l_main_power + r_main_power)
            # current_exported = abs(l_main_current + r_main_current)
            # home_consumption = abs(power_exported - solar_power) + subpanel_power
            # home_load = abs(current_exported - (2 * solar_current)) + subpanel_current        

            # if solar_power < home_consumption:
            #     current_status = 'Consuming'      
            #     verb = 'consumption'
            # else:
            #     current_status = "Producing"
            #     verb = 'production'
            
            if MODE == 'debug':
                break
            
            sleep(0.2)

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

    if not MODE:
        #infl.init_db()
        run_main()

    elif MODE == 'debug':
        # DEBUG MODE
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

    # Debug mode specifically for phase correction
    elif MODE == 'phase':

        if not title:
            title = input("Enter the title for this chart: ")

        # Read last sample set to disk to perform phase correction
        with open('data/samples/last-run.pkl', 'rb') as f:
            samples = pickle.load(f)

        #starttime = timeit.default_timer()
        rebuilt_waves = rebuild_waves(samples, ct0_phasecal, ct1_phasecal, ct2_phasecal, ct3_phasecal, ct4_phasecal)
        #stop = timeit.default_timer() - starttime
        #print(f'Took {round(stop, 3)} seconds to rebuild 5 voltage waves with {len(rebuilt_waves[0])} each.')


        samples.update({
            'vWave_ct0' : rebuilt_waves['v_ct0'],
            'vWave_ct1' : rebuilt_waves['v_ct1'],
            'vWave_ct2' : rebuilt_waves['v_ct2'],
            'vWave_ct3' : rebuilt_waves['v_ct3'],
            'vWave_ct4' : rebuilt_waves['v_ct4'],
        })

        plot_data(samples, title)        
        print("file written")


