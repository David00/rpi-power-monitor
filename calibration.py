from math import sqrt
from config import logger
from common import collect_data

def rebuild_wave(samples, v_wave, PHASECAL):
    # This function will rebuild a single voltage wave according to a single phasecal value.
    ''' samples: a list containing raw ADC readings from a single CT input 
        v_wave: a list contianing raw ADC readings from the original voltage waveform
        PHASECAL: a float represnting the current phase correction value.
    ''' 

    # The following empty lists will hold the phase corrected voltage wave that corresponds to each individual CT sensor.
    wave = []
    

    wave.append(v_wave[0])
    previous_point = v_wave[0]
    
    for current_point in v_wave[1:]:
        new_point = previous_point + PHASECAL * (current_point - previous_point)
        wave.append(new_point)
        previous_point = current_point

    rebuilt_wave = {        
        'new_v' : wave,                     # Rebuilt voltage wave
        'ct' : samples,                     # Raw ADC output for a single CT
        'original_v' : v_wave,              # Original voltage wave samples
    }
    return rebuilt_wave

def check_phasecal(samples, rebuilt_wave, board_voltage):
    # This function is a trimmed down version of the calculate_power().
    # Instead of calculating the power for all CTs at once, it will calculate the data for one CT at a time.
    # samples is a list of raw CT samples
    '''
    samples         : list, raw ADC output values for a single CT

    rebuilt_wave    : list, phase-corrected voltage wave for the single CT

    board_voltage   : float, current reading of the reference voltage from the +3.3V rail

    '''

    # Variable Initialization    
    sum_inst_power = 0    
    sum_squared_current = 0     
    sum_raw_current = 0    
    sum_squared_voltage = 0
    sum_raw_voltage = 0    

    # Scaling factors
    vref = board_voltage / 1024
    #ct_scaling_factor = vref * 100 * ct_accuracy_factor
    ct_scaling_factor = vref * 100
    #voltage_scaling_factor = vref * 126.5 * AC_voltage_accuracy_factor
    voltage_scaling_factor = vref * 126.5

    num_samples = len(rebuilt_wave)
    
    for i in range(0, num_samples):
        ct = (int(samples[i]))
        voltage = (int(rebuilt_wave[i]))

        # Process all data in a single function to reduce runtime complexity
        # Get the sum of all current samples individually
        sum_raw_current += ct
        sum_raw_voltage += voltage

        # Calculate instant power for each ct sensor
        inst_power = ct * voltage
        sum_inst_power += inst_power

        # Squared voltage
        squared_voltage = voltage * voltage
        sum_squared_voltage += squared_voltage

        # Squared current
        sq_ct = ct * ct
        sum_squared_current += sq_ct

    avg_raw_current = sum_raw_current / num_samples
    avg_raw_voltage = sum_raw_voltage / num_samples
    
    real_power = ((sum_inst_power / num_samples) - (avg_raw_current * avg_raw_voltage))  * ct_scaling_factor * voltage_scaling_factor

    mean_square_current = sum_squared_current / num_samples 
    mean_square_voltage = sum_squared_voltage / num_samples

    rms_current = sqrt(mean_square_current - (avg_raw_current * avg_raw_current)) * ct_scaling_factor
    rms_voltage     = sqrt(mean_square_voltage - (avg_raw_voltage * avg_raw_voltage)) * voltage_scaling_factor

    # Power Factor
    apparent_power = rms_voltage * rms_current
    
    try:
        power_factor = real_power / apparent_power
    except ZeroDivisionError:
        power_factor = 0

    
    results = {
        'power'     : real_power,
        'current'   : rms_current,
        'voltage'   : rms_voltage,
        'pf'        : power_factor
    }

    return results


def find_phasecal(samples, ct_selection, accuracy_digits, board_voltage):
    # This controls how many times the calibration process is repeated for this particular CT.
    num_calibration_attempts = 20   

    # Get Initial PF
    rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], 1.0)
    results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)
    pf = results['pf']
    logger.debug(f"Please wait while I read {ct_selection} and calculate the best PHASECAL value. This can take a few minutes, so please be patient.")
    
    best_pfs = []
    previous_phasecal = 1.0
    previous_pf = pf
    trends = []

    # Base Increment settings for changing phasecal
    increment = 1.005
    decrement = 0.995
    big_increment = 1.01
    big_decrement = 0.98

    for i, _ in enumerate(range(3), start=1):
        best_pf = {
        'pf' : 0,
        'cal' : 0,
    }
        for _ in range(75):

            if round(pf, 4) == 1.0:
                best_pf.update({
                    'pf': pf,
                    'cal': new_phasecal,
                })
                break

            if pf < 1.0:
                # If the PF isn't better than 0.995, we can increment the phasecal by an amount twice as large, referred to as big_increment, to help speed up the process.
                if round(pf, 2) != 1.0:
                    new_phasecal = previous_phasecal * big_increment
                else:
                    new_phasecal = previous_phasecal * increment
                action = 'incremented'
            else:
                if round(pf, 2) != 1.0:
                    new_phasecal = previous_phasecal * big_decrement
                else:
                    new_phasecal = previous_phasecal * decrement
                action = 'decremented'

            # Collect a live sample and calculate PF using new_phasecal
            samples = collect_data(2000)
            rebuilt_wave = rebuild_wave(samples[ct_selection], samples['voltage'], new_phasecal)
            results = check_phasecal(rebuilt_wave['ct'], rebuilt_wave['new_v'], board_voltage)
            pf = results['pf']
            if pf > best_pf['pf']:
                best_pf.update({
                    'pf' : pf,
                    'cal' : new_phasecal
                })

            #logger.debug(f"  PF: {pf} | Phasecal: {new_phasecal}")
           
            # Determine whether or not trend is moving away from 1.0 or towards 1.0.
            # Trend should be a moving average over two values.

            trends.append(pf - previous_pf)
            previous_phasecal = new_phasecal

            if len(trends) == 2:
                # Check to see if both values have the same sign to determine the actual trend, then empty the list
                if trends[0] < 0:
                    if trends[1] < 0:
                        trend = 'worse'
                        # If the trend is getting worse, reject the previous phasecal, and reduce cut increment/decrement by half.
                        increment = 1 + (abs(1 - increment) / 2)
                        decrement = decrement + ((1 - decrement) / 2)
                
                        # Apply the opposite action to the previous phasecal value to attempt to reverse the trend. If the previous phasecal
                        # was incremented, then we will decrement using the newly adjusted decrement value.
                        if action == 'increment':
                            # Decrement instead
                            new_phasecal = previous_phasecal * decrement
                        else:
                            # Increment instead
                            new_phasecal = previous_phasecal * increment


                if trends[1] > 0:
                    trend = 'better'

                trends = []
                continue    # Skip updating the previous phasecal and previous_pf since we want to attempt to reverse the trend.

            else:
                if action == 'increment':
                    # Repeat same action
                    new_phasecal = previous_phasecal * increment                
                else:
                    new_phasecal = previous_phasecal * decrement


            
            previous_pf = pf

        logger.debug(f"Wave {i}/3 results: ")
        logger.debug(f" Best PF: {best_pf['pf']} using phasecal: {best_pf['cal']}")
        best_pfs.append(best_pf)
        
    return best_pfs