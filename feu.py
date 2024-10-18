#!/usr/bin/env python3
import os
import time
import traceback
import configparser
from paho.mqtt.client import Client as PahoClient

from pymqtt_hass.items import Device
from am2320 import AM2320

current_folder = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = 'config.ini'
PYMQTT_HASS_CONFIG_FILE = 'hass_config.json'

def get_config():
    ret = {}
    config = configparser.ConfigParser()
    config.read(os.path.join(current_folder, CONFIG_FILE))

    ret['MQTT_HOST'] = config.get('MQTT', 'HOST')
    ret['MQTT_PORT'] = config.getint('MQTT', 'PORT', fallback=1883)
    ret['MQTT_USERNAME'] = config.get('MQTT', 'USERNAME')
    ret['MQTT_PASSWORD'] = config.get('MQTT', 'PASSWORD')

    return ret

def run():
    config = get_config()

    # Initialize MQTT client
    client = PahoClient()
    # Set the client options
    client.enable_logger()
    client.username_pw_set(config['MQTT_USERNAME'], config['MQTT_PASSWORD'])
    # Connect the mqtt client
    client.connect(config['MQTT_HOST'], config['MQTT_PORT'])

    # Get the configured home-assistant device
    device = Device(client, os.path.join(current_folder, PYMQTT_HASS_CONFIG_FILE))
    # Send the hass's device discovery
    device.send_discovery()

    if True:
        temp_sensor = AM2320()
        go_publish = False
        for _ in range(10):
            try:
                print("Try reading AM2320")
                temperature = temp_sensor.get_temperature()
                print(temperature)
                go_publish = True
                break
            except:
                # Try again
                time.sleep(1)
                continue

        if go_publish:
            print("Publish temperature")
            device_topic = device.get_device_topic()

            # Publish the total consumed power
            topic = '/'.join([
                device_topic,
                'temperature',
            ])
            client.publish(topic, temperature)
            client.loop()
            
        time.sleep(5)


if __name__ == '__main__':
    run()
