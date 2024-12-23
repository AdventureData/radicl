import time

from radicl.gps import USBGPS
import time


def main():
    gps = USBGPS()
    while True:
        print(gps.get_fix())
        time.sleep(0.5)


if __name__ == '__main__':
    main()
