import time
import unittest

import matplotlib.pyplot as plt

from radicl.probe import RAD_Probe


class TestProbeData(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.probe = RAD_Probe()
        self.probe.resetMeasurement()
        self.probe.startMeasurement()
        time.sleep(0.1)
        self.probe.stopMeasurement()

    @classmethod
    def tearDownClass(self):
        self.probe.resetMeasurement()

    def test_get_calibrated_data(self):
        """
        Test retrieve calibration data from the probe
        """
        try:
            d = self.probe.readCalibratedSensorData()
            assert d is not None

        except Exception as e:
            raise(e)
    
    def test_get_FilteredDepth_data(self):
        """
        Test retrieve filtered depth data from the probe
        """
        try:
            d = self.probe.readFilteredDepthData()
            print(d)
            assert d is not None

        except Exception as e:
            raise(e)


    # def test_get_raw_accleration_depth_data(self):
    #     """
    #     Test retrieve acceleration data from the probe
    #     """
    #     try:
    #         d = self.probe.readRawAccelerationData()
    #         print(d)
    #         assert d is not None
    #
    #     except Exception as e:
    #         raise(e)
    #
    # def test_get_sensor_combo_depth_data(self):
    #     """
    #     Test retrieve APp version of the data from the probe
    #     """
    #     try:
    #         d = self.probe.readSensorDepthComboData()
    #         assert d is not None
    #
    #     except Exception as e:
    #         raise(e)


if __name__ == '__main__':
    unittest.main()
