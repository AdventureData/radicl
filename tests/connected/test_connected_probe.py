import time

import pytest
from time import sleep

from . import not_connected
import numpy as np
from radicl.probe import RAD_Probe
from radicl.info import ProbeState

from study_lyte.adjustments import merge_on_to_time

@pytest.mark.skipif(not_connected, reason='probe not connected')
class TestProbeMeasurementData:
    @pytest.fixture(scope='class')
    def meas_probe(self):
        prb = RAD_Probe(debug=True)
        prb.connect()
        prb.setSetting(setting_name='samplingrate', value=16000)
        prb.startMeasurement()
        time.sleep(1)
        prb.stopMeasurement()
        prb.wait_for_state(ProbeState.DATA_STAGED, retry=1000, delay=0.3)

        yield prb
        prb.resetMeasurement()

    @pytest.mark.skipif(not_connected, reason='probe not connected')
    def test_merging(self, meas_probe):
        baro = meas_probe.readFilteredDepthData()
        acc = meas_probe.readRawAccelerationData()
        final = merge_on_to_time([acc, baro], final_time=acc.index)

        # Check timing of adjusted dataset
        assert final['filtereddepth'].idxmax() == pytest.approx(baro['filtereddepth'].idxmax(), 1e-2)
        assert final['filtereddepth'].idxmin() == pytest.approx(baro['filtereddepth'].idxmin(), 1e-2)


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


@pytest.mark.skipif(not_connected, reason='probe not connected')
@pytest.mark.parametrize('scale', [2, 16])
def test_rawacceleration_scaling(real_probe, scale):
    """
    If a real probe is connected, the magnitude of the sensor should
    always be very close to 1 unless the scaling is off.
    """
    a = real_probe.setSetting(setting_name='accrange', value=scale)
    time.sleep(0.1)
    real_probe.startMeasurement()
    time.sleep(1)
    real_probe.stopMeasurement()

    data = real_probe.readRawAccelerationData()

    data['magnitude'] = np.sqrt(np.power(data['X-Axis'], 2) +
                                np.power(data['Y-Axis'], 2) +
                                np.power(data['Z-Axis'], 2))
    result = np.mean(data['magnitude'])
    real_probe.resetMeasurement()
    time.sleep(0.2)
    assert pytest.approx(result, abs=5e-2) == 1

@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_initial_state_set(real_probe):
    real_probe.getProbeMeasState()
    assert real_probe.state != ProbeState.NOT_SET

@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_meas_temp(real_probe):
    temp = real_probe.readMeasurementTemperature()
    assert type(temp) == int

@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_probe_serial(real_probe):
    result = real_probe.serial_number
    # Ensure the probe returns something real
    assert result is not None
    # Its a string
    assert type(result) == str
    # Its number and uppers
    assert all([c.isupper() or c.isnumeric() for c in result])

@pytest.mark.skipif(not_connected, reason='probe not connected')
def test_probe_header(real_probe):
    result = real_probe.getProbeHeader()
    assert result is not None
    assert type(result) == dict
    assert all([v is not None for k,v in result.items()])

