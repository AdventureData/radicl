from time import sleep
import pytest
from . import not_connected
from radicl.api import  RAD_API

@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_getHWID(api):
    a = api.getHWID()
    print(a)


@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_MeasGetAccRange(api):
    a = api.MeasGetAccRange()
    a = int.from_bytes(a['data'], byteorder='little')
    assert (a >= 2) and (a <= 16)


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('value', [2, 4, 6, 8, 16])
def test_MeasSetAccRange(api, value):
    # Attempt to set the value
    r1 = api.MeasSetAccRange(value)
    sleep(0.1)

    # Retrieve it
    stored_val = api.MeasGetAccRange()
    stored_val = int.from_bytes(stored_val['data'], byteorder='little')

    assert stored_val == value


class MockPort:
    def __init_(self, data, byte_length):
        self.segments = len(data)
        self.received = None
        self.sending = None
    def writePort(self, data):
        self.received = data

    def numBytesInBuffer(self):
        pass
    def readPort(self, nbytes):
        pass

class TestApi:
    @pytest.fixture()
    def port(self):
        return MockPort()
    @pytest.fixture()
    def api(self, port):
        return RAD_API(port, debug=True)

    def test_sendApiPortEnable(self, api):
        """
        Assert the api enable port command is received

        """
        api.sendApiPortEnable()
        assert api.port.received[0] == 33

    def test_getHWID(self, api):
        ret = api.getHWID()
