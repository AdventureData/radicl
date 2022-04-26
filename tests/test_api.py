from time import sleep
import pytest

from . import not_connected


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
    stored_val = api.MeasGetAccRange()

    stored_val = int.from_bytes(stored_val['data'], byteorder='little')

    assert stored_val == value
