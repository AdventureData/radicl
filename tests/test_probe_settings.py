import unittest
from radicl.probe import RAD_Probe


class TestProbeSettings(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.probe = RAD_Probe()

    def test_get_calibration_data(self):
        """
        Test retrieve calibration values from the probe
        """
        # Loop through 1-4 sensors
        for i in range(1,5):
            d = self.probe.getSetting(setting_name='calibdata', sensor=1)

            # Confirm calibration data is always length 2
            assert len(d) == 2

            # confirm its in the 12 bit range
            for dv in d:
                assert dv < 4096
                assert dv >= 0


if __name__ == '__main__':
    unittest.main()
