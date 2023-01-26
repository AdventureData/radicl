from time import sleep
import pytest
from . import not_connected, MockRADPort
from radicl.api import RAD_API
from unittest.mock import MagicMock, patch


# @pytest.mark.skipif(not_connected, reason='probe not connected')
# def test_getHWID(api):
#     a = api.getHWID()
#     print(a)
#
#
# @pytest.mark.skipif(not_connected, reason='probe not connected')
# def test_MeasGetAccRange(api):
#     a = api.MeasGetAccRange()
#     a = int.from_bytes(a['data'], byteorder='little')
#     assert (a >= 2) and (a <= 16)
#
#
# @pytest.mark.skipif(not_connected, reason='probe not connected')
# @pytest.mark.parametrize('value', [2, 4, 6, 8, 16])
# def test_MeasSetAccRange(api, value):
#     # Attempt to set the value
#     r1 = api.MeasSetAccRange(value)
#     sleep(0.1)
#
#     # Retrieve it
#     stored_val = api.MeasGetAccRange()
#     stored_val = int.from_bytes(stored_val['data'], byteorder='little')
#
#     assert stored_val == value


class TestApi:
    @pytest.fixture()
    def mock_port(self, payload):
        yield MockRADPort(payload)

    @pytest.fixture()
    def mock_api(self, mock_port):
        return RAD_API(mock_port, debug=True)

    def test_sendApiPortEnable(self, mock_api):
        """
        Assert the api enable port command is received

        """
        mock_api.sendApiPortEnable()
        assert mock_api.port.received[0] == 33

    @pytest.mark.parametrize('payload, expected', [
        [b'\x9f\x01\x02\x00\x01\x03', 3]
    ])
    def test_getHWID(self, mock_api, payload, expected):
        ret = mock_api.getHWID()
        assert ret['data'] == expected

    @pytest.mark.parametrize('payload, expected', [
        [b'\x9f\x02\x02\x00\x01\x01', 1]
    ])
    def test_getHWREV(self, mock_api, payload, expected):
        ret = mock_api.getHWREV()
        assert ret['data'] == expected

    @pytest.mark.parametrize('payload, expected', [
        [b'\x9f\x03\x02\x00\x02\x01.', 1.46]
    ])
    def test_getFWREV(self, mock_api, payload, expected):
        ret = mock_api.getFWREV()
        assert ret['data'] == expected

    @pytest.mark.parametrize('payload, expected', [
        [b'\x9f\t\x02\x00\x04\x01.\x03\x00', '1.46.3.0']
    ])
    def test_getFullFWREV(self, mock_api, payload, expected):
        ret = mock_api.getFullFWREV()
        assert ret['data'] == expected
