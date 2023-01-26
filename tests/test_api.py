import pytest
from . import MockRADPort
from radicl.api import RAD_API


class TestApi:
    @pytest.fixture()
    def mock_port(self, payload):
        yield MockRADPort(payload)

    @pytest.fixture()
    def mock_api(self, mock_port):
        return RAD_API(mock_port, debug=True)

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
