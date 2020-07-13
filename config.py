import logging
import sys

# Create basic logger
logger = logging.getLogger('power_monitor')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


# Enter the voltage of your grid "as measured at the time of calibration".
GRID_VOLTAGE = 124.2


# Define Variables
ct0_channel = 0             # Orange Pair           | House main (leg 1 - left)  (orange pair)
ct1_channel = 1             # Green Pair            | House main (leg 2 - right) (green pair)
ct2_channel = 2             # Blue Pair             | Subpanel main (leg 1 - top)
ct3_channel = 3             # Brown Pair            | Solar Power 
ct4_channel = 6             # 3.5mm Input #1        | Subpanel main (leg 2 - bottom)
board_voltage_channel =  4  # Board voltage ~3.3V
v_sensor_channel = 5        # 9V AC Voltage channel
ct5_channel = 7             # 3.5mm Input #2        | Unused

# The values from running the software in "phase" mode should go below!
ct_phase_calibration = {
    'ct0' : 1.069606140,
    'ct1' : 1.3,
    'ct2' : 1.475,
    'ct3' : 1.775,
    'ct4' : 1.0600186657237292,
    'ct5' : 1.220857186171267,
}
