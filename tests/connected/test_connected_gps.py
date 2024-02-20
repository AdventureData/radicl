import time
from radicl.gps import USBGPS
import pytest
from . import gps_not_connected


@pytest.mark.skipif(gps_not_connected, reason='gps not connected')
class TestUSBGPS:
    @pytest.fixture(scope='class')
    def gps_dev(self):
        return USBGPS()

    def test_get_fix(self, gps_dev):
        location = gps_dev.get_fix(max_attempts=30)

        assert len(location) == 2

    def test_get_fix_not_identical(self, gps_dev):
        """ Even a static GPS should be slightly different."""
        location = gps_dev.get_fix(max_attempts=30)
        time.sleep(0.5)
        location2 = gps_dev.get_fix(max_attempts=30)

        assert location != location2
