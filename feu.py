#!/usr/bin/env python3
import os
import configparser
import asyncio
import aiomqtt

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

class MQTTDevice:

    def __init__(self):
        self.config = get_config()
        self.client = None
        self.device = None
        self.device_topic = None

        self.boost_status = 0

    async def periodic(self, time_s):
        while True:
            self.event_refresh.set()
            await asyncio.sleep(time_s)

    async def publisher(self):
        temp_sensor = AM2320()
        while True:
            go_publish = False
            for _ in range(10):
                try:
                    print("Try reading AM2320")
                    humidity, temperature = temp_sensor.get_both()
                    print(temperature, humidity)
                    go_publish = True
                    break
                except:
                    # Try again
                    await asyncio.sleep(1)
                    continue

            if go_publish:
                device_topic = self.device.get_device_topic()

                print("Publish temperature")
                topic = '/'.join([
                    device_topic,
                    'temperature',
                ])
                await self.client.publish(topic, temperature)

                print("Publish humidity")
                topic = '/'.join([
                    device_topic,
                    'humidity',
                ])
                await self.client.publish(topic, humidity)

            # Block until event_refresh in fired
            await self.event_refresh.wait()
            self.event_refresh.clear()

    async def send_discovery(self):
         for topic, payload in self.device.discovery_items():
             await self.client.publish(topic, payload)

    async def main(self):
        ''' main method
            Launches tasks

            publisher : collect and publish on MQTT, then wait for an event
            period: triggers the publish signal
        '''
        client_config = {
            'hostname': self.config['MQTT_HOST'],
            'port': self.config['MQTT_PORT'],
            'username': self.config['MQTT_USERNAME'],
            'password': self.config['MQTT_PASSWORD'],
        }

        loop = asyncio.get_running_loop() 

        async with aiomqtt.Client(**client_config) as client:
            self.client = client

            self.device = Device(self.client, os.path.join(current_folder, PYMQTT_HASS_CONFIG_FILE))

            await self.send_discovery()

            self.event_refresh = asyncio.Event(loop=loop) 

            publish_tk = loop.create_task(self.publisher())
            period_normal_tk = loop.create_task(
                self.periodic(60)
            )

            await publish_tk
            await period_normal_tk

if __name__ == '__main__':
    asyncio.run(MQTTDevice().main())

