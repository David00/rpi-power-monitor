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
ct_sensor_channel = 0       # YDHC CT sensor #1 input
board_voltage_channel = 5   # Board voltage ~3.3V
v_sensor_channel = 6        # AC Voltage channel
ref_voltage_channel = 7     # Voltage splitter channel ~1.65V

# Tuning Variables
v_read_delay                = 0.0001       # voltage read delay 
delay_factor                = 1   # Total read delay will be v_read_delay * delay_factor 
reference_level             = 511       # This is the digital equivalent to the reference voltage of 1.65V (half of 1024) 
CT_accuracy_factor          = 0.01
AC_voltage_accuracy_factor  =  -0.0035   # Negative if output voltage reads higher than meter


#Create SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 200000

def readadc(adcnum):
    # read SPI data from the MCP3008, 8 channels in total
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data

def collect_data(numSamples):
    
    samples = []
    while len(samples) < numSamples:
        ct_data = readadc(ct_sensor_channel)
        v_data = readadc(v_sensor_channel)
        samples.append((ct_data, v_data))
        #time.sleep(v_read_delay * delay_factor)
    return samples


def dump_data(dump_type, samples):
    speed_kHz = spi.max_speed_hz / 1000
    filename = f'laptop-plugin-{speed_kHz}kHz-delay-{delay_factor}.csv'
    with open(filename, 'a') as f:
        headers = ["Sample#", "current", "voltage"]
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, sample in enumerate(samples):
            writer.writerow([i, sample[0], sample[1]])
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
    while len(samples) < 10:
        data = readadc(board_voltage_channel)
        samples.append(data)

    avg_reading = sum(samples) / len(samples)
    board_voltage = (avg_reading / 1024) * 3.31
    return board_voltage



def calculate_power(samples, board_voltage):
    # Samples contains a list of 2-tuples. Inside each 2-tuple is a raw ADC current and voltage reading.
    # The reference value should be subtracted from each of the values prior to calculating.

    sum_inst_power = 0
    sum_squared_voltage = 0
    sum_squared_current = 0

    current_scaling_factor = (board_voltage / 1024) * 100 * (1 + CT_accuracy_factor)
    voltage_scaling_factor = (board_voltage / 1024) * 126.5 * (1 + AC_voltage_accuracy_factor)

    total_scaling_factor = current_scaling_factor * voltage_scaling_factor

    for sample in samples:
        current = (int(sample[0]) - 512)
        voltage = (int(sample[1]) - 512)

        inst_power = current * voltage 
        sum_inst_power += inst_power

        squared_voltage = voltage * voltage 
        sum_squared_voltage += squared_voltage

        squared_current = current * current
        sum_squared_current += squared_current

    real_power = sum_inst_power / len(samples)  * total_scaling_factor # 1 is subtracted to account for the header row in the CSV data
    mean_square_voltage = sum_squared_voltage / len(samples)
    rms_voltage = sqrt(mean_square_voltage) * voltage_scaling_factor

    mean_square_current = sum_squared_current / len(samples) 
    rms_current = sqrt(mean_square_current) * current_scaling_factor

    apparent_power = rms_voltage * rms_current
    power_factor = real_power / apparent_power
    
    return real_power, rms_voltage, rms_current, apparent_power, power_factor

def run_main():
    while True:
        try:
            board_voltage = get_board_voltage()
            ref_voltage = get_ref_voltage(board_voltage)
            #print(f"Ref voltage {ref_voltage}V | Board voltage: {board_voltage}V")
            starttime = timeit.default_timer()
            chan0_samples = collect_data(2000)
            stop = timeit.default_timer() - starttime
            #print(f"Collected {len(samples)} samples in {round(stop,4)} seconds at {spi.max_speed_hz} Hz.")
            #dump_data('tuple', samples)

            real_power, rms_voltage, rms_current, apparent_power, power_factor = calculate_power(chan0_samples, board_voltage)

            if real_power < 1 and real_power > -1:
                real_power = 0

            print(f"Real Power: {round(real_power, 3)} W | RMS Voltage: {round(rms_voltage, 3)}V | RMS Current: {round(rms_current, 3)}A | Apparent Power: {round(apparent_power, 3)} W | Power Factor: {round(power_factor, 3)}")
     
    
     
        except KeyboardInterrupt:
            sys.exit()

if __name__ == '__main__':
    run_main()