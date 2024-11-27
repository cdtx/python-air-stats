# python-air-stats

Read air quality sensors with python and push to MQTT for home assistant (with discovery)

## AM2320

For temperature and humidity

## SGP30

For TVOC and eCO2

Uses library at : https://github.com/pimoroni/sgp30-python

Make it a systsmd service
``` bash
# See https://stackoverflow.com/a/62643730
sudo ln -s airstats.service /etc/systemd/system/rpict3t1_mqtt.service
systemctl enable airstats
systemctl daemon-reload
systemctl start airstats
```

## Configure

``` text
[System]
AM2320 = True|False
SGP30 = True|False

[MQTT]
HOST =
PORT = 
USERNAME = 
PASSWORD = 
```
