import pytest

from . import MockGPSStream
from radicl.gps import USBGPS
from unittest.mock import patch
from types import SimpleNamespace


@pytest.fixture(scope='function')
def mock_gps_port(payload):
    yield MockGPSStream(payload)


@pytest.mark.parametrize('payload, expected', [
    # Lat long found with a retry
    ([b'$GPTXT,01,01,02,u-blox ag - www.u-blox.com*50\r\n',
      b'$GPGGA,035548.00,4400.0000,N,11600.00000,W,1,06,1.34,870.9,M,-19.4,M,,*69\r\n'], [44.0, -116.0]),

    # No lat long found
    ([b'$GPTXT,01,01,02,u-blox ag - www.u-blox.com*50'], None),
    # Lat long message found but not interpretable
    ([b'$GPRMC,201209.00,A,,N,,W,0.065,,230223,,,D*6B\r\n'], None)
])
def test_get_gps_fix(mock_gps_port, payload, expected):
    """
    Mock out the connection and gps. Ensure the managing function handles
    three scenarios.
    Args:
        payload: List of nmea strings to read
        expected: expected lat long outcome
    """
    with patch('radicl.gps.get_serial_cnx', return_value=SimpleNamespace(port='dev_fake', description='GPS/GNSS Receiver')):
        with patch('radicl.com.serial.Serial.open', return_value=None):
            with patch('radicl.gps.NMEAReader', return_value=mock_gps_port):
                gps_dev = USBGPS()
                loc = gps_dev.get_fix(max_attempts=2)
                assert loc == expected
