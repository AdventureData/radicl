from radicl.info import AccelerometerRange, ProbeErrors, ProbeState
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

