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
      b'$GPGGA,044716.00,4400.0000,N,11600.00000,W,2,12,0.80,859.1,M,-19.4,M,,0000*6A\r\n'], [44.0, -116.0]),
    # No lat long found
    ([b'$GPTXT,01,01,02,u-blox ag - www.u-blox.com*50\r\n'], None),
    # Lat long message found but not interpretable
    ([b'$GPRMC,044000.00,A,,N,,W,0.045,,181000,,,D*6A\r\n'], None),
    # Valid ids to interpret
    ([b'$GPGLL,4300.00,N,11600.00,W,180000.00,A,D*74\r\n'], [43.0, -116.0]),
    # Test EW conversion
    ([b'$GPRMC,044000.00,A,4300.00,N,11600.00,E,0.045,,181000,,,D*6A\r\n'], [43.0, 116.0]),

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
