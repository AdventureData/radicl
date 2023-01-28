from radicl.com import *
import pytest
from unittest.mock import patch


@pytest.mark.parametrize('kw, com_list, expected', [
    ('test', [('', 'TEST_com'), ('', 'com1')], [('', 'TEST_com')]),
    ('test', [('', 'com')], [])

])
def test_find_kw_port(kw, com_list, expected):
    with patch('serial.tools.list_ports.comports', return_value=com_list):
        assert find_kw_port(kw) == expected


class MockSerialPort:
    def __init__(self, **kwargs):
        self.port = kwargs['port']

    def setDTR(self, num):
        pass

    def close(self):
        pass

    def reset_output_buffer(self):
        pass

    def write(self, data):
        return len(data)

    def read(self):
        pass

    def inWaiting(self):
        pass


class TestRAD_Serial:

    @pytest.fixture(scope='function')
    def rs(self):
        with patch('serial.tools.list_ports.comports', return_value=[('mock', 'STMicroelectronics')]):
            with patch('serial.Serial', return_value=MockSerialPort(port='mock')):
                rs = RAD_Serial()
                yield rs

    def test_rad_serial_open_port(self, rs):
        rs.openPort()
        assert rs.serial_port.port == 'mock'

    def test_closePort(self, rs):
        rs.closePort()
        assert rs.serial_port is None

    def test_flushPort(self, rs):
        rs.flushPort()

    def test_writePort(self, rs):
        n = rs.writePort(10)

    def test_writePortClean(self, rs):
        rs.writePortClean(10)

    def test_readPort(self, rs):
        rs.readPort()

    def test_numBytesInBuffer(self, rs):
        rs.numBytesInBuffer()
