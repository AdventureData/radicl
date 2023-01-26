import pytest
from time import sleep
from . import not_connected
import numpy as np


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name, expected_type", [
    ('accrange', int)
])
def test_get_setting(meas_probe, setting_name, expected_type):
    """
    Functionality test ensuring a setting runs
    """
    a = meas_probe.getSetting(setting_name=setting_name)
    assert type(a) is expected_type


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name, value", [
    ('accrange', 2),
    ('samplingrate', 5000),
    ('zpfo', 80)
])
def test_set_setting(meas_probe, setting_name, value):
    """
    Test setting a parameter in the probes settings
    """
    a = meas_probe.setSetting(setting_name=setting_name, value=value)
    sleep(0.1)
    a = meas_probe.getSetting(setting_name=setting_name)
    assert (a == value)
    sleep(0.1)


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('scale', [2, 16])
def test_rawacceleration_scaling(meas_probe, scale):
    """
    If a real probe is connected, the magnitude of the sensor should
    always be very close to 1 unless the scaling is off.
    """

    a = meas_probe.setSetting(setting_name='accrange', value=scale)

    meas_probe.startMeasurement()
    sleep(0.5)
    meas_probe.stopMeasurement()
    data = meas_probe.readRawAccelerationData()

    data['magnitude'] = np.sqrt(np.power(data['X-Axis'], 2) +
                                np.power(data['Y-Axis'], 2) +
                                np.power(data['Z-Axis'], 2))
    result = np.mean(data['magnitude'])
    meas_probe.resetMeasurement()
    assert pytest.approx(result, abs=2e-2) == 1
