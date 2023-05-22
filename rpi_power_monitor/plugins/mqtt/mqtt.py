# Plugin for the Power Monitor for Raspberry Pi
# Plugin Name: MQTT
# Author: Jacob Madden
# Description: This plugin will publish live power data to MQTT for use in external software like homeassistant.
#
""" 
Please update your config.toml file as below:

[plugins.mqtt]
enabled = true
host = "192.168.x.x"
username = "user"
password = "Password"
prefix = "powermon"


###  MQTT topic structure:  ###

powermon:
    status = online
    ct1
        power = 436.9398467009072
        pf = 0.6188594676154295
        current = 3.0030905091888105
        voltage = 235.0883109766441
    production
        power = 1666.4916708477683
        pf = 0.9972528630009776
        current = 7.106431483921596
    home-consumption
        power = 423.7662194448079
        current = 12.904760645319703
    net
        power = -1242.7254514029605
        current = 5.798329161398107
    voltage = 235.0883109766441

"""

import paho.mqtt.client as mqtt
from time import sleep

def on_connect(client, userdata, flags, rc, logger, prefix):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.publish(prefix + "/status", "online")
    else:
        logger.error("Failed to connect to MQTT broker, return code: {rc}")
        client.publish(prefix + "/status", "offline")

def on_disconnect(client, userdata, rc, logger, prefix):
    if rc != 0:
        logger.error("Unexpected disconnection from MQTT broker")
        client.publish(prefix + "/status", "offline")

def start_plugin(data, stop_flag, config, logger, *args, **kwargs):
  

    logger.info("Starting MQTT Plugin")


    # MQTT Setup
    broker = config.get('host')
    username = config.get('username') 
    password = config.get('password') 
    prefix = config.get('prefix')

    # Create an MQTT client instance
    client = mqtt.Client()
    client.clean_session = False

    # Set the on_connect callback function
    client.on_connect = lambda client, userdata, flags, rc: on_connect(client, userdata, flags, rc, logger, prefix)

    # Connect to the MQTT broker
    logger.info(f"Connecting to MQTT broker") 

    # Establish the initial connection
    client.username_pw_set(username, password)
    client.connect(broker, 1883, 60)
    client.loop_start()


#### MAIN ###
    while not stop_flag.is_set():


        try:
            if not client.is_connected():
                # Connect to the MQTT broker
                logger.info("Broker disconnected, reconnecting") 
                client.username_pw_set(username, password)
                client.connect(broker, 1883, 60)

            for channel, channel_data in data.get('cts', {}).items():
                for key, value in channel_data.items():
                    if value is not None:
                        topic = f"{prefix}/ct{channel}/{key}"
                        payload = str(round(value, 2))
                        client.publish(topic, payload)

            for key, value in data.get('production', {}).items():
                if value is not None:
                    topic = f"{prefix}/production/{key}"
                    payload = str(round(value, 2))
                    client.publish(topic, payload)

            for key, value in data.get('home-consumption', {}).items():
                if value is not None:
                    topic = f"{prefix}/home-consumption/{key}"
                    payload = str(round(value, 2))
                    client.publish(topic, payload)

            for key, value in data.get('net', {}).items():
                if value is not None:
                    topic = f"{prefix}/net/{key}"
                    payload = str(round(value, 2))
                    client.publish(topic, payload)

            topic = f"{prefix}/voltage"
            voltage = data.get('voltage')
            if voltage is not None:
                payload = str(round(voltage, 2))
                client.publish(topic, payload)


        except mqtt.MQTTException as e:
            logger.error(f"Error occurred while publishing MQTT message: {e}")
            client.disconnect()
            client.loop_stop()
            logger.error(f"Client loop stopped, trying to restart.. ")
            sleep(10)
            client.reconnect()  # Reconnect to the MQTT broker

        sleep(5)


    stop_plugin(client, prefix)
    return


def stop_plugin(client, prefix):

    # Publish offline status when the plugin stops
    client.publish(prefix + "/status", "offline")
    client.loop_stop()


    return