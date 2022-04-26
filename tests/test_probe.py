import pytest
from time import sleep
import numpy as np
from . import not_connected


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name", [
    'accrange'
])
def test_get_setting(probe, setting_name):
    """
    Functionality test ensuring a setting runs
    """
    a = probe.getSetting(setting_name=setting_name)
    assert True


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name, value", [
    ('accrange', 2),
    ('samplingrate', 5000),
    ('zpfo', 80)
])
def test_set_setting(probe, setting_name, value):
    """
    Test setting a parameter in the probes settings
    """
    a = probe.setSetting(setting_name=setting_name, value=value)
    a = probe.getSetting(setting_name=setting_name)
    assert (a == value)


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('scale', [2, 16])
def test_rawacceleration_scaling(meas_probe, scale):
    """
    If a real probe is connected, the magnitude of the sensor should
    always be very close to 1 unless the scaling is off.
    """

    a = meas_probe.setSetting(setting_name='accrange', value=scale)

    meas_probe.startMeasurement()
    sleep(1)
    meas_probe.stopMeasurement()
    data = meas_probe.readRawAccelerationData()

    data['magnitude'] = np.sqrt(np.power(data['X-Axis'], 2) +
                                np.power(data['Y-Axis'], 2) +
                                np.power(data['Z-Axis'], 2))
    result = np.mean(data['magnitude'])
    assert pytest.approx(result, abs=2e-2) == 1
