import sys
from textwrap import dedent
from time import sleep

import docker

from power_monitor.config import logger


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
                logger.info(f"... It appears that your {name} container is not running. ")

                logger.info(f"... restarting your {name} container. Please wait... ")
                container.restart()

                sleep(5)
                logger.info("... checking to see if the container is running now...")
                sleep(0.5)
                for _ in range(0,2):
                    # Make two attempts to see if the container is running now.
                    try:
                        influx_container = docker_client.containers.list( filters={'name' : name} )[0]
                        container_found = True
                    except IndexError:
                        sleep(0.5)
                        continue
                if not container_found:
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
                    return True
