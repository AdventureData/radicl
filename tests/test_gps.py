import pytest

from . import MockRADPort
from radicl.gps import USBGPS
from unittest.mock import patch, MagicMock

@pytest.fixture(scope='function')
def mock_gps(payload):
    yield MockGPS(payload)

@pytest.mark.parametrize('payload', [
    ([b'$GPTXT,01,01,02,u-blox ag - www.u-blox.com*50'])
])
def test_get_gps_fix(mock_gps, payload):
    with patch('serial.tools.list_ports.comports', return_value=com_list):
