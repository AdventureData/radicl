import time
from pynmeagps import NMEAReader

from .com import get_serial_cnx
from .ui_tools import get_logger


class USBGPS:
    def __init__(self, debug=False):
        self.log = get_logger(__name__, debug=debug)
        try:
            self.cnx = get_serial_cnx('blox')
        except Exception as e:
            self.cnx = None
            self.log.error('Unable to open GPS port.')
            self.log.error(e)

        if self.cnx is None:
            self.log.warning('No GPS found. No location data will be recorded.')
        else:
            self.log.info(f'GPS found ({self.cnx.port})!')

    def get_fix(self, max_attempts=100):
        """
        Attempts to get a location fix given a serial port
        connection to a usb gps.

        Args:
            max_attempts: Number of attempts to get lat long

        Returns:
            location: tuple of latitude and longitude
        """

        location = None
        if self.cnx is not None:
            self.log.info('Attempting to get a fix on location...')

            gps = NMEAReader(self.cnx)
            for i in range(max_attempts):
                rx, msg = gps.read()
                if msg.msgID in ['GGA', 'GLL', 'RMC']:
                    info = msg.lat, msg.lon
                    if all(info):
                        location = [float(p) for p in info]
                        break
                time.sleep(0.1)

            if location is None:
                self.log.warning('Unable to get a fix on GPS! No location data will be recorded!')
            else:
                self.log.info(f'GPS fix acquired, {location[0]:0.6f} {location[1]:0.6f}')

        return location

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cnx is not None:
            self.cnx.close()
