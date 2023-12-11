from radicl.info import AccelerometerRange, ProbeErrors, ProbeState, Firmware, PCA_Name
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

@pytest.mark.parametrize('idx, expected', [
    (1, PCA_Name.PB1),
    (3, PCA_Name.PB3),
    (100, PCA_Name.UNKNOWN),
    (None, PCA_Name.UNKNOWN)
])
def test_PCA_NAME(idx, expected):
    assert PCA_Name.from_index(idx) == expected
