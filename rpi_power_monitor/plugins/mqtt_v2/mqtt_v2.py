import paho.mqtt.client as mqtt
from .. import sleep_for
from time import time

def start_plugin(data, stop_flag, config, logger, *args, **kwargs):

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.debug("Connected to MQTT broker")
            client.publish(prefix + "/status", "online")
        if reason_code > 0:
            logger.error(f"Failed to connect to MQTT broker with error code: {rc}")

    logger.info("Starting MQTT_v2 Plugin")

    # MQTT Setup
    broker = config.get('host')
    username = config.get('username')
    password = config.get('password')
    prefix = config.get('prefix')
    refresh_rate = config.get('refresh_rate')
    minchangedict = {}
    minchangedict["power"] = config.get('power_change')
    minchangedict["voltage"] = config.get('voltage_change')
    minchangedict["pf"] = config.get('pf_change')
    minchangedict["current"] = config.get('current_change')
    max_publish_seconds = config.get('max_publish_seconds')
    lastpublishval = {}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, password)

    # Set Last Will and Testament (LWT)
    will_topic = f"{prefix}/status"
    will_payload = "offline"
    will_qos = 0  # Quality of Service Level (0, 1, or 2)
    will_retain = False  # Retain message or not

    client.will_set(will_topic, payload=will_payload, qos=will_qos, retain=will_retain)

    client.on_connect = on_connect

    client.connect(broker, 1883, 60)
    client.loop_start()
    sleep_for(2, stop_flag)
    client.publish(prefix + "/status", "online")

    while not stop_flag.is_set():


        for channel, channel_data in data.get('cts', {}).items():
            for key, value in channel_data.items():
                if value is not None:
                    topic = f"{prefix}/ct{channel}/{key}"
                    payload = str(round(value, 2))
                    try:
                        testvar = lastpublishval[channel]
                    except KeyError:
                        lastpublishval[channel] = {}
                    try:
                        testvar = lastpublishval[channel][key]
                    except KeyError:
                        lastpublishval[channel][key] = 0
                        lastpublishval[channel][key + "-time"] = 0
                    try:
                        testvar = minchangedict[key]
                    except KeyError:
                         minchangedict[key] = 0
                    if abs(value - lastpublishval[channel][key]) >= minchangedict[key] or time() - lastpublishval[channel][key + "-time"] >= max_publish_seconds:
                        client.publish(topic, payload)
                        lastpublishval[channel][key] = value
                        lastpublishval[channel][key + "-time"] = time()

        for key, value in data.get('production', {}).items():
            if value is not None:
                topic = f"{prefix}/production/{key}"
                payload = str(round(value, 2))
                try:
                    testvar = lastpublishval["production"]
                except KeyError:
                    lastpublishval["production"] = {}
                try:
                    testvar = lastpublishval["production"][key]
                except KeyError:
                    lastpublishval["production"][key] = 0
                    lastpublishval["production"][key + "-time"] = 0
                try:
                    testvar = minchangedict[key]
                except KeyError:
                     minchangedict[key] = 0
                if abs(value - lastpublishval["production"][key]) >= minchangedict[key] or time() - lastpublishval["production"][key + "-time"] >= max_publish_seconds:
                    client.publish(topic, payload)
                    lastpublishval["production"][key] = value
                    lastpublishval["production"][key + "-time"] = time()

        for key, value in data.get('home-consumption', {}).items():
            if value is not None:
                topic = f"{prefix}/home-consumption/{key}"
                payload = str(round(value, 2))
                try:
                    testvar = lastpublishval["home-consumption"]
                except KeyError:
                    lastpublishval["home-consumption"] = {}
                try:
                    testvar = lastpublishval["home-consumption"][key]
                except KeyError:
                    lastpublishval["home-consumption"][key] = 0
                    lastpublishval["home-consumption"][key + "-time"] = 0
                try:
                    testvar = minchangedict[key]
                except KeyError:
                     minchangedict[key] = 0
                if abs(value - lastpublishval["home-consumption"][key]) >= minchangedict[key] or time() - lastpublishval["home-consumption"][key + "-time"] >= max_publish_seconds:
                    client.publish(topic, payload)
                    lastpublishval["home-consumption"][key] = value
                    lastpublishval["home-consumption"][key + "-time"] = time()

        for key, value in data.get('net', {}).items():
            if value is not None:
                topic = f"{prefix}/net/{key}"
                payload = str(round(value, 2))
                try:
                    testvar = lastpublishval["net"]
                except KeyError:
                    lastpublishval["net"] = {}
                try:
                    testvar = lastpublishval["net"][key]
                except KeyError:
                    lastpublishval["net"][key] = 0
                    lastpublishval["net"][key + "-time"] = 0
                try:
                    testvar = minchangedict[key]
                except KeyError:
                     minchangedict[key] = 0
                if abs(value - lastpublishval["net"][key]) >= minchangedict[key] or time() - lastpublishval["net"][key + "-time"] >= max_publish_seconds:
                    client.publish(topic, payload)
                    lastpublishval["net"][key] = value
                    lastpublishval["net"][key + "-time"] = time()

        topic = f"{prefix}/voltage"
        voltage = data.get('voltage')
        if voltage is not None:
            payload = str(round(voltage, 2))
            try:
                testvar = lastpublishval["voltage"]
            except KeyError:
                lastpublishval["voltage"] = 0
                lastpublishval["voltage-time"] = 0
            try:
                testvar = minchangedict["voltage"]
            except KeyError:
                 minchangedict["voltage"] = 0
            if abs(voltage - lastpublishval["voltage"]) >= minchangedict["voltage"] or time() - lastpublishval["voltage-time"] >= max_publish_seconds:
                client.publish(topic, payload)
                lastpublishval["voltage"] = voltage
                lastpublishval["voltage-time"] = time()

        sleep_for(refresh_rate, stop_flag)


    stop_plugin(client)
    return


def stop_plugin(client):
    client.disconnect()
    client.loop_stop()


    return
