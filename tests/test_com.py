from radicl.com import find_kw_port, get_serial_cnx, RAD_Serial
import pytest
from unittest.mock import patch
from types import SimpleNamespace


@pytest.mark.parametrize('kw, description_list, expected', [
    # Check plain usage with capital letters
    ('test', ['TEST device', 'unknown com1'], ['TEST device']),
    # check no match found
    ('test', ['com'], []),
    # Check multiple matches found
    ('test', ['TEST device', 'tester com1'], ['TEST device', 'tester com1']),

])
def test_find_kw_port(kw, description_list, expected):
    """
    Mock devices using a list of descriptions. Check the port finder
    grabs them
    """
    coms = [SimpleNamespace(description=c) for c in description_list]
    with patch('serial.tools.list_ports.comports', return_value=coms):
        result = find_kw_port(kw)
        assert [r.description for r in result] == expected


@pytest.mark.parametrize('kw, com_list, match_index, expected', [
    # One probe
    ('ST Micro', ['St Microelectronics', 'unknown'], 0, 'dev_fake_0'),
    # Two probes but pick the index
    ('ST Micro', ['St Microelectronics', 'St Microelectronics 1'], 1, 'dev_fake_1'),
    # No probe
    ('ST Micro', ['unknown 1', 'unknown 2'], 0, None),

])
def test_get_serial_cnx(kw, com_list, match_index, expected):
    devices = [SimpleNamespace(device=f'dev_fake_{i}', description=d) for i,d in enumerate(com_list)]
    with patch('serial.tools.list_ports.comports', return_value=devices):
        with patch('serial.Serial.open', return_value=None):
            cnx = get_serial_cnx(kw, match_index=match_index)
        if hasattr(cnx, 'port'):
            assert cnx.port == expected
        else:
            assert cnx == expected


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
        with patch('serial.tools.list_ports.comports', return_value=[SimpleNamespace(device='dev_mock', description='STMicroelectronics')]):
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
