import unittest
from radicl.probe import RAD_Probe
import time
import matplotlib.pyplot as plt

class TestProbeData(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.probe = RAD_Probe()
        self.probe.resetMeasurement()
        self.probe.startMeasurement()
        time.sleep(1)
        self.probe.stopMeasurement()
        #self.probe.wait_for_state(4, delay=0.5)

    @classmethod
    def tearDownClass(self):
        self.probe.resetMeasurement()

    def test_get_calibrated_data(self):
        """
        Test retrieve calibration data from the probe
        """
        try:
            d = self.probe.readCalibratedSensorData()
            assert True

        except Exception as e:
            raise(e)

if __name__ == '__main__':
    unittest.main()
