from radicl.info import AccelerometerRange, ProbeErrors, ProbeState, Firmware, PCA_Name, SensorReadInfo
import pytest


class TestAccelerometerRange:
    @pytest.mark.parametrize('sensing_range, expected', [
        (2, AccelerometerRange.RANGE_2G),
        (3, None)
    ])
    def test_from_range(self, sensing_range, expected):
        assert AccelerometerRange.from_range(sensing_range) == expected


class TestProbeErrors:
    @pytest.mark.parametrize('error_code, expected', [
        (2049, ProbeErrors.MEASUREMENT_NOT_RUNNING),
        (10, ProbeErrors.UNKNOWN_ERROR)
    ])
    def test_from_code(self, error_code, expected):
        assert ProbeErrors.from_code(error_code) == expected


class TestFirmware:

    @pytest.fixture(scope='function')
    def fw1(self, fw1_str):
        return Firmware(fw1_str)

    @pytest.fixture(scope='function')
    def fw2(self, fw2_str):
        return Firmware(fw2_str)

    @pytest.mark.parametrize('fw1_str, fw2_str, expected', [
        ('1.2.3.0', '1.2.3.0', True),
        # Check auto assume subsequent zero values
        ('1.0.0.0', '1', True)

    ])
    def test_firmware_eq(self, fw1, fw2, expected):
        comparison = (fw1 == fw2)
        assert comparison == expected

    @pytest.mark.parametrize('fw1_str, fw2_str, expected', [
        # Test greater at both ends of the scales
        ('2.0', '1.1', True),
        ('0.0.0.2', '0.0.0.1', True),
        # Test equal
        ('1.2.3', '1.2.3', True),
        # Test greater value in a different position
        ('0.2', '1.1', False),
    ])
    def test_firmware_ge(self, fw1, fw2, expected):
        comparison = (fw1 >= fw2)
        assert comparison == expected

    @pytest.mark.parametrize('fw1_str, fw2_str, expected', [
        ('1.2', '1.1', True),
        ('0.2', '0.2', False),
        ('0.0.0.2', '0.0.0.1', True),
        ('0.0.0.1', '0.0.0.2', False),

    ])
    def test_firmware_gt(self, fw1, fw2, expected):
        comparison = (fw1 > fw2)
        assert comparison == expected

    @pytest.mark.parametrize('fw1_str, expected', [
        ('1.2', 'v1.2.0.0')
    ])
    def test_repr(self, fw1, expected):
        assert str(fw1) == expected

    def test_null_fw(self):
        assert Firmware(None) == Firmware('-1.-1.-1.-1')


@pytest.mark.parametrize('idx, expected', [
    (1, PCA_Name.PB1),
    (3, PCA_Name.PB3),
    (100, PCA_Name.UNKNOWN),
    (None, PCA_Name.UNKNOWN)
])
def test_PCA_NAME(idx, expected):
    assert PCA_Name.from_index(idx) == expected


class TestProbeState():
    @pytest.mark.parametrize("state, expected", [
        (1, ProbeState.MEASURING),
        (100, ProbeState.UNKOWN_STATE),

    ])
    def test_from_state(self, state, expected: ProbeState):
        assert ProbeState.from_state(state) == expected

    @pytest.mark.parametrize("state1, state2, expected", [
        (ProbeState.IDLE, ProbeState.MEASURING, True),
        (ProbeState.IDLE, ProbeState.IDLE, True),
        (ProbeState.DATA_STAGED, ProbeState.IDLE, False),

    ])
    def test_le(self, state1, state2, expected):
        assert (state1 <= state2) == expected

    @pytest.mark.parametrize("state1, state2, expected", [
        (ProbeState.MEASURING, ProbeState.MEASURING, True),
        (ProbeState.SENDING_DATA, ProbeState.IDLE, True),
        (ProbeState.PROCESSING, ProbeState.DATA_STAGED, False),

    ])
    def test_ge(self, state1, state2, expected):
        assert (state1 >= state2) == expected

    @pytest.mark.parametrize("state, expected", [
        (ProbeState.MEASURING, False),
        (ProbeState.IDLE, True),
        (ProbeState.RESET, True),
    ])
    def test_ready(self, state, expected):
        assert ProbeState.ready(state) == expected

class TestReadSensorInfo:
    @pytest.mark.parametrize("sensor_info, att, expected", [
        (SensorReadInfo.RAWSENSOR, 'buffer_id', 0),
        # Bytes per segment
        (SensorReadInfo.ACCELEROMETER, 'bytes_per_segment', None),
        (SensorReadInfo.RAWSENSOR, 'bytes_per_segment', 256),
        # nbytes_per_value
        (SensorReadInfo.RAW_BAROMETER_PRESSURE, 'nbytes_per_value', 3),
        # expected values
        (SensorReadInfo.FILTERED_BAROMETER_DEPTH, 'expected_values', 1),
        (SensorReadInfo.ACCELEROMETER, 'expected_values', 3),
        # spi usage
        (SensorReadInfo.RAWSENSOR, 'uses_spi', True),
        (SensorReadInfo.ACCELEROMETER, 'uses_spi', False),
        # Readable name
        (SensorReadInfo.ACCELEROMETER, 'readable_name', 'Acceleration'),
        # data_names
        (SensorReadInfo.RAW_BAROMETER_PRESSURE, 'data_names', ['raw_pressure']),
        # unpack type
        (SensorReadInfo.ACCELEROMETER, 'unpack_type', '<h'),
        # conversion
        (SensorReadInfo.ACCELEROMETER, 'conversion_factor', 0.001),
        # Max sample
        (SensorReadInfo.RAWSENSOR, 'max_sample_rate', 16000),
    ])
    def test_properties(self, sensor_info:SensorReadInfo, att, expected):
        result = getattr(sensor_info, att)
        assert result == expected

    @pytest.mark.skip("Unsure why this wont evaluate")
    def test_bytes_per_sample(self):
        result = SensorReadInfo.bytes_per_sample
        assert result == 8

    @pytest.mark.parametrize("data_request, expected", [
        ('rawsensor', SensorReadInfo.RAWSENSOR),
        ('calibratedsensor', SensorReadInfo.RAWSENSOR),
        ('rawacceleration', SensorReadInfo.ACCELEROMETER),
        ('rawpressure', SensorReadInfo.RAW_BAROMETER_PRESSURE),
        ('garbage', None),
    ])
    def test_from_data_request(self, data_request, expected):
        result = SensorReadInfo.from_data_request(data_request)
        assert result == expected
