# This file is a part of the Power Monitor for Raspberry Pi project at https://github.com/david00/rpi-power-monitor
# Please see the README for more details.

from math import sqrt, sin, cos, acos, degrees, radians, floor

def measure_phase_angle(samples, enabled_channels, grid_frequency):
    '''Measures the phase angle between the current and voltage samples that are provided in the samples dictionary.'''
    # Get the number of samples per channel
    num_samples_per_channel = len(samples[f'ct{enabled_channels[0]}'])
    total_samples = num_samples_per_channel * len(enabled_channels) * 2
    overall_sample_rate = total_samples / samples['duration']
    per_channel_sample_rate = round(overall_sample_rate / (len(enabled_channels) * 2), 3)
    
    #print(f"Sample Rate: {sample_rate} | per channel sample rate: {per_channel_sample_rate}")
    
    phase_shifts_dict = dict()

    # Determine the number of samples needed to capture a full cycle at the grid_frequency
    step_size = int((per_channel_sample_rate / grid_frequency) * 0.85)  # Step size is a bit too large

    # Determine how many times we can look at a single oscillation based on the per-channel sample size
    num_oscillations = floor(num_samples_per_channel / step_size)

    # Analyze each channel
    for chan in enabled_channels:

        phase_shifts_dict[chan] = {
            'deg' : 0,
            'rad' : 0,
        }

        current_samples = samples[f'ct{chan}']
        voltage_samples = samples[f'v{chan}']

        current_peaks = []  # Holds the indices for each oscillation where the current wave peaks.
        actual_current_centers = [] 
        voltage_peaks = []  # Holds the indices for each oscillation where the voltage wave peaks

        for starting_position in range(0, step_size * num_oscillations, step_size):
            # Break up large sample batches into smaller batches
            current_max = 0
            current_max_idx = 0
            v_max = 0
            v_max_idx = 0
            current_max_found = False
            v_max_found = False

            # Find max current value first
            current_max = max(current_samples[starting_position : starting_position + step_size])
            current_max_idx = current_samples[starting_position : starting_position + step_size].index(current_max) + starting_position

            idx_center_current = find_center(current_max_idx, current_samples, len(current_samples))
            # actual_current_centers.append(idx_center_current)
            current_peaks.append(idx_center_current)
            
            # Old Way
            # current_peaks.append(current_max_idx) 
            
            # This represents the number of samples we'll start looking for the peak of the voltage wave BEFORE the current wave. 
            # For example, if the current wave peaks at index position 10, we'll start looking for the voltage wave peak at index position 5.
            # This handles the scenario where the current and voltage waves are in the same phase.
            voltage_wave_padding = 5

            # Make sure that current_max_idx is larger than the value to be subtracted in the first analysis
            if current_max_idx < voltage_wave_padding:
                voltage_wave_padding = current_max_idx                

            v_max = max(voltage_samples[current_max_idx - voltage_wave_padding : current_max_idx + step_size - voltage_wave_padding])
            
            # If the current and voltage wave are in the same phase, it is necessary to start looking at least a few samples before the current sample.
                    
            v_max_idx = voltage_samples[ current_max_idx - voltage_wave_padding: current_max_idx + step_size - voltage_wave_padding].index(v_max) + current_max_idx - voltage_wave_padding + 1
            idx_center_voltage = find_center(v_max_idx, voltage_samples, len(current_samples))
            voltage_peaks.append(idx_center_voltage)

            # Old Way
            # voltage_peaks.append(v_max_idx)

        # Measure the difference between the voltage wave and the current wave indices.
        delta_peaks = [voltage_peaks[i] - current_peaks[i] for i in range(0, len(current_peaks))]   # A list containing the difference in index positions between the peaks of the current and voltage waves.
        avg_delta_peak = sum(delta_peaks) / len(delta_peaks)    # The average difference in positions that the current and voltage waves peak.
        min_delta_peak = min(delta_peaks)
        max_delta_peak = max(delta_peaks)
        if max_delta_peak > 0:
            variance = min_delta_peak / max_delta_peak  # Closer to 1 implies samples were taken at a more consistent rate
        
        sample_duration = 1 / per_channel_sample_rate
        phase_shifts = [ (td * sample_duration * 360) * grid_frequency for td in delta_peaks]
        avg_phase_shift = round(sum(phase_shifts) / len(phase_shifts), 2)
        avg_phase_shift_rad = radians(avg_phase_shift)
        phase_shifts_dict[chan] = {
            'deg' : avg_phase_shift,
            'rad' : avg_phase_shift_rad,
            'v_peak_idxs' : voltage_peaks,
            'c_peak_idxs' : current_peaks,
            # 'actual_current_centers': current_peaks,
        }

    return phase_shifts_dict


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
        'v_ct1' : wave_0,
        'v_ct2' : wave_1,
        'v_ct3' : wave_2,
        'v_ct4' : wave_3,
        'v_ct5' : wave_4,
        'v_ct6' : wave_5,
        'voltage' : voltage_samples,
        'ct1' : samples['ct1'],
        'ct2' : samples['ct2'],
        'ct3' : samples['ct3'],
        'ct4' : samples['ct4'],
        'ct5' : samples['ct5'],
        'ct6' : samples['ct6'],
    }

    return rebuilt_waves


def find_center(max_idx, wave, buffer_size):
    '''Finds the center of a sinusoidal waveform'''

    slopes = []
    window_size = 10    # This is how many samples before/after the given max_idx point to look at.

    if max_idx <= window_size:
        start= 0
    else:
        start = max_idx - window_size
    
    if max_idx + window_size >= buffer_size:
        stop = buffer_size - 1
    else:
        stop = max_idx + window_size
    
    for i in range(start, stop):
        slopes.append( round(wave[i + 1] - wave[i]) )
    
    
    num_slopes = len(slopes)
    smallest_slope_values = [-1] * 11
    largest_slope_values = [-1] * 11
    actual_center = -1

    target_slopes = [1, 2, 3]
    s = 1

    for s in range(1, 11):  # s is the target slope that we're looking for.
        for i in range(0, num_slopes):  # slope is the measured slope from the wave data.
            if s == abs(slopes[i]):     # If the target slope s equals the absolute value of the slope at this position
                if smallest_slope_values[s] == -1:
                    smallest_slope_values[s] = i
                    # print(f"Found first occurence of slope {s} at position {i}")
                    break

        # Checks the slopes from the back side of the slope array moving forward
        if smallest_slope_values[s] > -1:
            for i in range(num_slopes - 1, -1, -1):
                if (s == abs(slopes[i])):
                    if largest_slope_values[s] == -1:
                        largest_slope_values[s] = i
                        break
        
        # Check to see if there is a smallest and largest position found for this slope that are different from each other.
        if (smallest_slope_values[s] != -1 and largest_slope_values[s] != -1):

            # There are slopes found in the same relative position. Check to see if the slopes are not identical
            if (smallest_slope_values[s] != largest_slope_values[s]):
                delta_slope = largest_slope_values[s] - smallest_slope_values[s]            
                if delta_slope > 1:
                    actual_center = max_idx + smallest_slope_values[s] + (delta_slope / 2) - 9
                else:
                    actual_center = max_idx + smallest_slope_values[s] + 1 - 9
                break
        
            # The slopes are identical, so the actual center should be at the index position directly between the two slopes.
            else:
                abs_slopes = [abs(x) for x in slopes]
                min_slope = min(abs_slopes)
                min_slope_idx = abs_slopes.index(min_slope)
                actual_center = max_idx - window_size + min_slope_idx + 1
                break

        else:
            return max_idx
    return int(actual_center)