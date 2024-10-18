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

    def _get_shorts(self, index, size):
        ''' Read bytes at specified index and shape short integers
            
            index: start address
            size: number of bytes to read (twice the numer of shorts to expect)
        '''
        write_request = i2c_msg.write(self.DEVICE_ADDRESS, [0x03, index, size])
        read_request = i2c_msg.read(self.DEVICE_ADDRESS, 4+size)
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

        if data[0] != 0x03:
            raise Exception("Read issue")

        self._check_crc(data)

        # Split result to 2 sized chunks and compute shorts
        chunks = [data[i:i + 2] for i in range(2, len(data)-2, 2)]
        shorts = [data[0]*255 + data[1] for data in chunks]

        return shorts
    
    def get_both(self):
        both = self._get_shorts(0, 4)
        return both[0]/10, both[1]/10

    def get_temperature(self):
        return self._get_shorts(2, 2)[0] / 10

    def get_humidity(self):
        return self._get_shorts(0, 2)[0] / 10

if __name__ == '__main__':
    dev = AM2320()
    # temp = dev.get_temperature()
    # print(temp)
    while True:
        try:
            hum, temp = dev.get_both()
            break
        except:
            continue
    print(temp, hum)
