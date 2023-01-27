import time

import pytest
from time import sleep
from . import not_connected
import numpy as np
from radicl.probe import RAD_Probe
from radicl.interface import dataframe_this

@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name, expected_type", [
    ('accrange', int)
])
def test_get_setting(real_probe, setting_name, expected_type):
    """
    Functionality test ensuring a setting runs
    """
    a = real_probe.getSetting(setting_name=setting_name)
    assert type(a) is expected_type


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize("setting_name, value", [
    ('accrange', 2),
    ('samplingrate', 5000),
    ('zpfo', 80)
])
def test_set_setting(real_probe, setting_name, value):
    """
    Test setting a parameter in the probes settings
    """
    a = real_probe.setSetting(setting_name=setting_name, value=value)
    sleep(0.1)
    a = real_probe.getSetting(setting_name=setting_name)
    assert (a == value)
    sleep(0.1)


@pytest.mark.skipif(not_connected, reason='probe not connected')
class TestProbeMeasurementData:
    @pytest.fixture(scope='class')
    def meas_probe(self):
        prb = RAD_Probe(debug=True)
        prb.setSetting(setting_name='samplingrate', value=16000)
        prb.startMeasurement()
        time.sleep(1)
        prb.stopMeasurement()
        prb.wait_for_state(3, retry=1000, delay=0.3)

        yield prb
        prb.resetMeasurement()

    # @pytest.mark.parametrize('fn, expected_n_datasets, expected_samples, ', [
    #     ('readFilteredDepthData', None, 50),
    #     ('readRawAccelerationData', 3, 75)
    #     ('readRawSensor', 3, 16000)
    #
    # ])
    # def test_dataset_len(self, meas_probe, fn, expected_samples, expected_n_datasets):
    #     """
    #     Pulls data and checks the length is as expected
    #     Args:
    #         fn: probe function attribute
    #         expected_n_datasets: number of data sets expected
    #         expected_samples: number of samples taken
    #     """
    #     data = getattr(meas_probe, fn)()
    #
    #     if expected_n_datasets is not None:
    #         keys = list(data.keys())
    #         assert len(keys) == expected_n_datasets
    #         data = data[keys[0]]
    #
    #     assert pytest.approx(len(data), abs=0.05*expected_samples) == expected_samples


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('scale', [2, 16])
def test_rawacceleration_scaling(real_probe, scale):
    """
    If a real probe is connected, the magnitude of the sensor should
    always be very close to 1 unless the scaling is off.
    """
    a = real_probe.setSetting(setting_name='accrange', value=scale)

    real_probe.startMeasurement()
    time.sleep(0.5)
    real_probe.stopMeasurement()

    data = real_probe.readRawAccelerationData()

    data['magnitude'] = np.sqrt(np.power(data['X-Axis'], 2) +
                                np.power(data['Y-Axis'], 2) +
                                np.power(data['Z-Axis'], 2))
    result = np.mean(data['magnitude'])
    real_probe.resetMeasurement()
    assert pytest.approx(result, abs=2e-2) == 1


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('scale', [2, 16])
def test_rawacceleration_scaling(real_probe, scale):
    """
    If a real probe is connected, the magnitude of the sensor should
    always be very close to 1 unless the scaling is off.
    """
    a = real_probe.setSetting(setting_name='accrange', value=scale)

    real_probe.startMeasurement()
    time.sleep(0.5)
    real_probe.stopMeasurement()

    data = real_probe.readRawAccelerationData()

    data['magnitude'] = np.sqrt(np.power(data['X-Axis'], 2) +
                                np.power(data['Y-Axis'], 2) +
                                np.power(data['Z-Axis'], 2))
    result = np.mean(data['magnitude'])
    real_probe.resetMeasurement()
    assert pytest.approx(result, abs=2e-2) == 1
