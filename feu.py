#!/usr/bin/env python3
import os
import configparser
import asyncio
import aiomqtt

from pymqtt_hass.items import Device

from am2320 import AM2320
from sgp30 import SGP30


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

class NonBlockingSGP30(SGP30):
    ''' Override the start_measurement method
        to make it release the async loop every time it waits
        before init is finished (15s)
    '''
    async def start_measurement(self, run_while_waiting=None):
        """Start air quality measurement on the SGP30.

        The first 15 readings are discarded so this command will block for 15s.

        :param run_while_waiting: Function to call for every discarded reading.

        """
        self.command('init_air_quality')
        testsamples = 0
        while True:
            # Discard the initialisation readings as per page 8/15 of the datasheet
            eco2, tvoc = self.command('measure_air_quality')
            # The first 15 readings should return as 400, 0 so abort when they change
            # Break after 20 test samples to avoid a potential infinite loop
            if eco2 != 400 or tvoc != 0 or testsamples >= 20:
                break
            if callable(run_while_waiting):
                run_while_waiting()
            await asyncio.sleep(1.0)
            testsamples += 1

class MQTTDevice:

    def __init__(self):
        self.config = get_config()
        self.client = None
        self.device = None
        self.device_topic = None

        self.boost_status = 0

        # sgp30 read values
        # Initialized to None so the publish method
        # knows if sgp30 init is done
        self.sgp30 = NonBlockingSGP30()
        self.tvoc = None
        self.eco2 = None

    async def periodic(self, time_s):
        while True:
            self.event_refresh.set()
            await asyncio.sleep(time_s)

    async def refresh_sgp30(self):
        print('SGP30 start measurement')
        await self.sgp30.start_measurement()

        while True:
            print('SGP30 get air quality')
            ret = self.sgp30.get_air_quality()
            self.tvoc = ret.total_voc
            self.eco2 = ret.equivalent_co2
            await asyncio.sleep(1)

    async def publisher(self):

        temp_sensor = AM2320()
        while True:

            # Read and publish am2320 values
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

                # Push measured humidy from am2320 to the sgp30
                self.sgp30.set_humidity(humidity)

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

            # Publish sgp30 values
            if self.tvoc != None:
                print("Publish tvoc")
                topic = '/'.join([
                    device_topic,
                    'tvoc',
                ])
                await self.client.publish(topic, self.tvoc)
            if self.eco2 != None:
                print("Publish eco2")
                topic = '/'.join([
                    device_topic,
                    'eco2',
                ])
                await self.client.publish(topic, self.eco2)

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

            publish_tk = loop.create_task(
                self.publisher()
            )
            period_normal_tk = loop.create_task(
                self.periodic(60)
            )
            refresh_sgp30_tk = loop.create_task(
                self.refresh_sgp30()
            )

            await publish_tk
            await period_normal_tk
            await refresh_sgp30_tk

if __name__ == '__main__':
    asyncio.run(MQTTDevice().main())

