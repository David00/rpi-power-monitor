import paho.mqtt.client as mqtt
from .. import sleep_for
import socket


def start_plugin(data, stop_flag, config, logger, *args, **kwargs):

    def on_connect(client, flags, rc):
        if rc == 0:
            logger.debug("Connected to MQTT broker")
            client.publish(prefix + "/status", "online")
        else:
            logger.error(f"Failed to connect to MQTT broker with error code: {rc}")

    def on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.warning("MQTT broker disconnected")
            while True:  # Try to reconnect
                try:
                    client.reconnect()
                    logger.debug("Successfully reconnected.")
                    break  # If the connection was successful, exit the loop
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    sleep_for(5)  # Wait before trying again



    logger.info("Starting MQTT Plugin")

    # MQTT Setup
    broker = config.get('host')
    username = config.get('username')
    password = config.get('password')
    prefix = config.get('prefix')
    client = mqtt.Client("PowerMonitor")
    #client.clean_session = False
    client.username_pw_set(username, password)

    # Set Last Will and Testament (LWT)
    will_topic = f"{prefix}/status"
    will_payload = "offline"
    will_qos = 0  # Quality of Service Level (0, 1, or 2)
    will_retain = False  # Retain message or not

    client.will_set(will_topic, payload=will_payload, qos=will_qos, retain=will_retain)

    # Set the on_connect and on_disconnect callbacks
    client.on_connect = lambda client, userdata, flags, rc: on_connect(client, flags, rc)
    client.on_disconnect = on_disconnect
    try:
        client.connect(broker, 1883, 60)
    except socket.gaierror:
        logger.warning(f"Failed to connect to MQTT broker at {broker}.")
        exit()
    client.loop_start()
    sleep_for(2)
    client.publish(prefix + "/status", "online")

    while not stop_flag.is_set():


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



        sleep_for(5)
        

    stop_plugin(client)
    return


def stop_plugin(client):
    
    client.loop_stop()
   

    return