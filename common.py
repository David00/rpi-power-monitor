# This module contains functions that are used in both the main power-monitor code and the calibration code.

from datetime import datetime
from config import ct_phase_correction, ct0_channel, ct1_channel, ct2_channel, ct3_channel, ct4_channel, board_voltage_channel, v_sensor_channel, ct5_channel, logger
import spidev
import subprocess
import docker
import sys
from time import sleep
from textwrap import dedent

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
    ct5_data = []
    v_data = []
    while len(v_data) < numSamples:
        ct0 = readadc(ct0_channel)
        ct4 = readadc(ct4_channel)
        ct1 = readadc(ct1_channel)
        v = readadc(v_sensor_channel)
        ct2 = readadc(ct2_channel)
        ct3 = readadc(ct3_channel)
        ct5 = readadc(ct5_channel)
        ct0_data.append(ct0)
        ct1_data.append(ct1)
        ct2_data.append(ct2)
        ct3_data.append(ct3)
        ct4_data.append(ct4)
        ct5_data.append(ct5)
        v_data.append(v)

    samples = {
        'ct0' : ct0_data,
        'ct1' : ct1_data,
        'ct2' : ct2_data,
        'ct3' : ct3_data,
        'ct4' : ct4_data,
        'ct5' : ct5_data,
        'voltage' : v_data,
        'time' : now,
    }
    return samples

def recover_influx_container():
    docker_client = docker.from_env()

    # Check to see if the influxdb container exists:
    containers = docker_client.containers.list(all=True)
    for container in containers:
        image = container.attrs['Config']['Image']

        if 'influx' in image.lower():
            name = container.attrs['Name'].replace('/','')
            status = container.attrs['State']['Status']

            if status.lower() != 'running':
                # Ask the user to restart the container
                answers = ['yes', 'no', 'y', 'n']
                logger.info("It appears that your InfluxDB container is not running. Would you like me to try to restart it? Please enter yes or no: ")
                try:
                    answer = input()
                except EOFError:
                    # This EOFError will be raised if the user is running this as a service (and can't enter yes or no through stdin). We'll assume that the user does want to try starting the container.
                    answer = 'yes'
                while answer.lower() not in answers:
                    answer = input("\nPlease type yes or no and press the return key: ")

                if answer.lower() == "yes" or answer.lower() == "y":
                    container.restart()
                    logger.info("... restarting your docker container. Please wait... ")
                    sleep(5)
                    logger.info("... checking to see if the container is running now...")
                    sleep(0.5)
                    try:
                        influx_container = docker_client.containers.list( filters={'name' : name} )[0]
                    except IndexError:
                        logger.info("Couldn't find the container by name! Please open a Github issue as this is an unexpected result from this experimental implementation.")
                        sys.exit()

                    if influx_container.attrs['State']['Status'] != 'running':
                        # Something must be wrong with the container - check for the exit code and grab the last few lines of logs to present to the user for further troubleshooting.
                        exit_code = influx_container.attrs['State']['ExitCode']
                        logs = influx_container.logs(tail=20)

                        logger.info(dedent(f"""Sorry, I couldn't fix your InfluxDB container. Here's some information that may help you: 
                        Container Exit Code: {exit_code}
                        Logs:"""
                        ))
                        for line in logs.splitlines():
                            logger.info(f"   {line}")
                        
                        sys.exit()

                    else:
                        logger.info("... container successfully started!")

                
                else:
                    logger.info("Please ensure that the docker container is running, then try again.")
                    sys.exit()

