#!/usr/bin/env python
import time

from am2320 import AM2320

if __name__ == '__main__':
    dev = AM2320()
    for _ in range(10):
        try:
            print('Try reading')
            temperature = dev.get_temperature()
            break
        except:
            # Try again
            time.sleep(0.5)
            pass
    print(temperature)

