#!/usr/bin/python

import spidev
import time
import timeit
import csv
from math import sqrt
import sys

#Define Variables
#board_voltage = 3.305
AC_TRANSFORMER_RATIO = 11.5
AC_TRANSFORMER_OUTPUT = 10.6
ct1_channel = 0             # YDHC CT sensor #1 input | Subpanel
ct2_channel = 1             # YDHC CT sensor #2 input | Solar Main
ct3_channel = 2             # CT sensor #3 input      | House main (leg 1) (orange pair)
ct4_channel = 3             # CT sensor #4 input      | House main (leg 2) (green pair)
board_voltage_channel = 5   # Board voltage ~3.3V
v_sensor_channel = 6        # AC Voltage channel
ref_voltage_channel = 7     # Voltage splitter channel ~1.65V

# Tuning Variables
v_read_delay                = 0.0001       # voltage read delay 
delay_factor                = 1   # Total read delay will be v_read_delay * delay_factor 
ct1_accuracy_factor         = -0.0515   # DONE
ct2_accuracy_factor         = -0.050    # DONE
ct3_accuracy_factor         = -0.050    # DONE
ct4_accuracy_factor         = -0.0503   # 
AC_voltage_accuracy_factor  = 0.00585   # Negative if output voltage reads higher than meter


#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 650000


def readadc(adcnum):
    # read SPI data from the MCP3008, 8 channels in total
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

def collect_data(numSamples):
    
    samples = []
    ct1_data = []
    ct2_data = []
    ct3_data = []
    ct4_data = []
    v_data = []
    while len(v_data) < numSamples:
        ct1 = readadc(ct1_channel)
        ct2 = readadc(ct2_channel)
        v = readadc(v_sensor_channel)
        ct3 = readadc(ct3_channel)
        ct4 = readadc(ct4_channel)        
        ct1_data.append(ct1)
        ct2_data.append(ct2)
        ct3_data.append(ct3)
        ct4_data.append(ct4)
        v_data.append(v)

    samples = (ct1_data, ct2_data, ct3_data, ct4_data, v_data)
    return samples


def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    filename = f'data-dump-{speed_kHz}kHz-delay-{delay_factor}.csv'
    with open(filename, 'w') as f:
        headers = ["Sample#", "ct1", "ct2", "ct3", "ct4", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        # samples contains lists for each data sample. 
        for i in range(0, len(samples[0])):
            ct1_data = samples[0]
            ct2_data = samples[1]
            ct3_data = samples[2]
            ct4_data = samples[3]
            v_data = samples[-1]
            writer.writerow([i, ct1_data[i], ct2_data[i], ct3_data[i], ct4_data[i], v_data[i]])
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
    ct1_samples = samples[0]
    ct2_samples = samples[1]
    ct3_samples = samples[2]
    ct4_samples = samples[3]
    v_samples   = samples[-1]

    # Variable Initialization    
    sum_inst_power_ct1 = sum_inst_power_ct2 = sum_inst_power_ct3 = sum_inst_power_ct4 = 0
    sum_squared_current_ct1 = sum_squared_current_ct2 = sum_squared_current_ct3 = sum_squared_current_ct4 = 0
    sum_raw_current_ct1 = sum_raw_current_ct2 = sum_raw_current_ct3 = sum_raw_current_ct4 = 0
    sum_squared_voltage = 0
    sum_raw_voltage = 0

    # Scaling factors
    ct1_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct1_accuracy_factor)
    ct2_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct2_accuracy_factor)
    ct3_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct3_accuracy_factor)
    ct4_scaling_factor = (board_voltage / 1024) * 100 * (1 + ct4_accuracy_factor)
    voltage_scaling_factor = (board_voltage / 1024) * 126.5 * (1 + AC_voltage_accuracy_factor)

    
    for i in range(0, len(v_samples)):
        ct1 = (int(ct1_samples[i]))
        ct2 = (int(ct2_samples[i]))
        ct3 = (int(ct3_samples[i]))
        ct4 = (int(ct4_samples[i]))
        voltage = (int(v_samples[i]))      

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current_ct1 += ct1
        sum_raw_current_ct2 += ct2
        sum_raw_current_ct3 += ct3
        sum_raw_current_ct4 += ct4
        sum_raw_voltage += voltage

        # Calculate instant power for each ct sensor
        inst_power_ct1 = ct1 * voltage
        inst_power_ct2 = ct2 * voltage
        inst_power_ct3 = ct3 * voltage
        inst_power_ct4 = ct4 * voltage
        sum_inst_power_ct1 += inst_power_ct1
        sum_inst_power_ct2 += inst_power_ct2
        sum_inst_power_ct3 += inst_power_ct3
        sum_inst_power_ct4 += inst_power_ct4

        # Squared voltage
        squared_voltage = voltage * voltage  
        sum_squared_voltage += squared_voltage

        # Squared current
        sq_ct1 = ct1 * ct1
        sq_ct2 = ct2 * ct2
        sq_ct3 = ct3 * ct3
        sq_ct4 = ct4 * ct4
        
        sum_squared_current_ct1 += sq_ct1
        sum_squared_current_ct2 += sq_ct2
        sum_squared_current_ct3 += sq_ct3
        sum_squared_current_ct4 += sq_ct4

    avg_raw_current_ct1 = sum_raw_current_ct1 / len(v_samples)
    avg_raw_current_ct2 = sum_raw_current_ct2 / len(v_samples)
    avg_raw_current_ct3 = sum_raw_current_ct3 / len(v_samples)
    avg_raw_current_ct4 = sum_raw_current_ct4 / len(v_samples)
    avg_raw_voltage = sum_raw_voltage / len(v_samples)

    real_power_1 = ((sum_inst_power_ct1 / len(v_samples)) - (avg_raw_current_ct1 * avg_raw_voltage))  * ct1_scaling_factor * voltage_scaling_factor 
    real_power_2 = ((sum_inst_power_ct2 / len(v_samples)) - (avg_raw_current_ct2 * avg_raw_voltage))  * ct2_scaling_factor * voltage_scaling_factor 
    real_power_3 = ((sum_inst_power_ct3 / len(v_samples)) - (avg_raw_current_ct3 * avg_raw_voltage))  * ct3_scaling_factor * voltage_scaling_factor 
    real_power_4 = ((sum_inst_power_ct4 / len(v_samples)) - (avg_raw_current_ct4 * avg_raw_voltage))  * ct4_scaling_factor * voltage_scaling_factor 
    mean_square_voltage = sum_squared_voltage / len(v_samples)    

    rms_voltage = sqrt(mean_square_voltage - (avg_raw_voltage * avg_raw_voltage)) * voltage_scaling_factor

    mean_square_current_ct1 = sum_squared_current_ct1 / len(v_samples) 
    mean_square_current_ct2 = sum_squared_current_ct2 / len(v_samples) 
    mean_square_current_ct3 = sum_squared_current_ct3 / len(v_samples) 
    mean_square_current_ct4 = sum_squared_current_ct4 / len(v_samples) 

    rms_current_ct1 = sqrt(mean_square_current_ct1 - (avg_raw_current_ct1 * avg_raw_current_ct1)) * ct1_scaling_factor
    rms_current_ct2 = sqrt(mean_square_current_ct2 - (avg_raw_current_ct2 * avg_raw_current_ct2)) * ct2_scaling_factor
    rms_current_ct3 = sqrt(mean_square_current_ct3 - (avg_raw_current_ct3 * avg_raw_current_ct3)) * ct3_scaling_factor
    rms_current_ct4 = sqrt(mean_square_current_ct4 - (avg_raw_current_ct4 * avg_raw_current_ct4)) * ct4_scaling_factor

    if rms_current_ct1 != 0:
        apparent_power = rms_voltage * rms_current_ct1        
        power_factor = real_power_1 / apparent_power

    else:
        apparent_power = 0
        power_factor = 0
    
    results = (
        real_power_1,
        real_power_2,
        real_power_3,
        real_power_4,
        rms_voltage,
        rms_current_ct1,
        rms_current_ct2,
        rms_current_ct3,
        rms_current_ct4,
        power_factor
        )

    return results

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
    
    
    while True:        
        try:
            board_voltage = get_board_voltage()
            #print(f"Board voltage is: {board_voltage}") 
            #ref_voltage = get_ref_voltage(board_voltage)
            #print(f"Ref voltage {ref_voltage}V | Board voltage: {board_voltage}V")
            starttime = timeit.default_timer()
            samples = collect_data(2000)
            stop = timeit.default_timer() - starttime
            # print(f"Collected {len(samples[2]) * len(samples)} samples in {round(stop,4)} seconds at {spi.max_speed_hz} Hz.")
            
            ct0_samples = samples[0]
            ct1_samples = samples[1]
            ct2_samples = samples[2]
            ct3_samples = samples[3]
            v_samples = samples[-1]

            # EXPERIMENTAL: Phase correction 
            # ct1_samples = ct1_samples[:-1]    # remove the last sample from ct1
            # ct2_samples = ct2_samples[1:]   # remove the first sample from ct2
            # v_samples = v_samples[1:]     # remove the first sample from voltage samples
            # Repackage the individual samples after phase correction
            # samples = (ct1_samples, ct2_samples, v_samples)

            # dump_data('tuple', samples)

            results = calculate_power(samples, board_voltage)
            # Unpack results
            real_power_0, real_power_1, real_power_2, real_power_3, rms_voltage, rms_current_ct0, rms_current_ct1, rms_current_ct2, rms_current_ct3, power_factor = results         
           
            avg_ct_0.append(rms_current_ct0)
            avg_ct_1.append(rms_current_ct1)
            avg_ct_2.append(rms_current_ct2)
            avg_ct_3.append(rms_current_ct3)
            avg_rms_voltage.append(rms_voltage)

            avg_ct_0_value = sum(avg_ct_0) / len(avg_ct_0)
            avg_ct_1_value = sum(avg_ct_1) / len(avg_ct_1)
            avg_ct_2_value = sum(avg_ct_2) / len(avg_ct_2)
            avg_ct_3_value = sum(avg_ct_3) / len(avg_ct_3)
            avg_rms_voltage_value = sum(avg_rms_voltage) / len(avg_rms_voltage)
      
            
            #print(f"CT0 Average: {round(avg_ct_0_value, 3)} | CT1: {round(avg_ct_1_value, 3)} | CT2: {round(avg_ct_2_value, 3)} | CT3: {round(avg_ct_3_value, 3)} | Voltage: {round(avg_rms_voltage_value, 3)}") 
            #print(f"CT3: {round(avg_ct_3_value, 3)}    |    Voltage: {round(avg_rms_voltage_value, 3)}")
            print("\n")
            print(f"Sensor 0: Real Power {round(real_power_0, 3)} | RMS Current: {round(rms_current_ct0, 3)} | RMS Voltage: {round(rms_voltage, 3)} | Power Factor: {round(power_factor, 3)}")
            print(f"Sensor 1: Real Power {round(real_power_1, 3)} | RMS Current: {round(rms_current_ct1, 3)} | RMS Voltage: {round(rms_voltage, 3)}")
            print(f"Sensor 2: Real Power {round(real_power_2, 3)} | RMS Current: {round(rms_current_ct2, 3)} | RMS Voltage: {round(rms_voltage, 3)}")
            print(f"Sensor 3: Real Power {round(real_power_3, 3)} | RMS Current: {round(rms_current_ct3, 3)} | RMS Voltage: {round(rms_voltage, 3)}")
            # print("\n\n")

            avg_rms_0.append(rms_current_ct0)
            avg_rms_1.append(rms_current_ct1)
            avg_rms_2.append(rms_current_ct2)
            avg_rms_3.append(rms_current_ct3)

            print(f"Averages: Ct0: {round(sum(avg_rms_0) / len(avg_rms_0),2)} | Ct1: {round(sum(avg_rms_1) / len(avg_rms_1), 2)} | Ct2: {round(sum(avg_rms_2) / len(avg_rms_2), 2)} | Ct3: {round(sum(avg_rms_3) / len(avg_rms_3), 2)}")    
     
        except KeyboardInterrupt:
            sys.exit()

if __name__ == '__main__':
    run_main()