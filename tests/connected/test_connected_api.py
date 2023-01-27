import pytest
from time import sleep
from . import not_connected


@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_getHWID(real_api):
    a = real_api.getHWID()
    assert type(a['data']) == int


@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_MeasGetAccRange(real_api):
    a = real_api.MeasGetAccRange()
    a = int.from_bytes(a['data'], byteorder='little')
    assert (a >= 2) and (a <= 16)


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('value', [2, 4, 6, 8, 16])
def test_MeasSetAccRange(real_api, value):
    # Attempt to set the value
    r1 = real_api.MeasSetAccRange(value)
    sleep(0.1)

    # Retrieve it
    stored_val = real_api.MeasGetAccRange()
    stored_val = int.from_bytes(stored_val['data'], byteorder='little')

    assert stored_val == value
