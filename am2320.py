#!/usr/bin/env python
import time
from smbus2 import SMBus, i2c_msg


class AM2320:
    DEVICE_ADDRESS = 0x5C
    def __init__(self):
        self.bus = SMBus(1)

    def wake_up(self):
        for _ in range(3):
            msg = i2c_msg.write(self.DEVICE_ADDRESS, [])
            try:
                self.bus.i2c_rdwr(msg)
                time.sleep(0.01)
                break
            except:
                # try again...
                continue

    def _check_crc(self, data):
        read_crc = data[-1] * 256 + data[-2]
        crc = 0xffff

        for item in data[:-2]:
            crc ^= item
            for _ in range(8):
                if crc & 0x01:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        
        if crc != read_crc:
            raise Exception(f'Bad CRC ({hex(crc)} != {hex(read_crc)})')

    def get_temperature(self):
        write_request = i2c_msg.write(self.DEVICE_ADDRESS, [0x03, 0x02, 0x02])
        read_request = i2c_msg.read(self.DEVICE_ADDRESS, 6)
        self.wake_up()
        for _ in range(1):
            try:
                self.bus.i2c_rdwr(write_request)
                break
            except:
                # try again...
                continue

        time.sleep(0.02)

        self.bus.i2c_rdwr(read_request)
        data = list(read_request)
        self._check_crc(data)

        ret = (data[2]*255 + data[3]) / 10

        return ret

    def get_humidity(self):
        pass

