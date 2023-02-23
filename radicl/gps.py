import time
from pynmeagps import NMEAReader

from .com import get_serial_cnx
from .ui_tools import get_logger


class USBGPS:
    def __init__(self, debug=False):
        self.log = get_logger("GPS", debug=debug)
        self.cnx = get_serial_cnx('gps')
        if self.cnx is None:
            self.log.warning('No GPS found. No location data will be recorded.')

    def get_fix(self, max_attempts=20):
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
            gps = NMEAReader(self.cnx)

            for i in range(max_attempts):
                msg = gps.read()[1]
                if msg.msgID in ['GGA', 'RMC']:
                    location = msg.lat, msg.lon
                    self.log.info(f'GPS fix acquired, {location[0]:0.4f} {location[1]:0.4f}')
                    break
                time.sleep(0.1)
            if location is None:
                self.log.warning('Unable to get a fix on GPS! No location data will be recorded!')

        return location
