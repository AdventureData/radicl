import time
import unittest

import matplotlib.pyplot as plt

from radicl.probe import RAD_Probe

class TestProbeData(unittest.TestCase):
    '''
    Test all the probe data
    '''
    measure_time = 0.5

    @classmethod
    def setUpClass(self):
        self.probe = RAD_Probe(debug=True)
        self.probe.resetMeasurement()
        self.probe.startMeasurement()
        time.sleep(self.measure_time)
        self.probe.stopMeasurement()

    @classmethod
    def tearDownClass(self):
        self.probe.resetMeasurement()

class TestSmallProbeData(TestProbeData):
    '''
    Test all the data with lower sample rates so we take a larger measurement
    '''
    measure_time = 0.5

    def test_get_FilteredDepth_data(self):
        """
        Test retrieve filtered depth data from the probe
        """
        try:
            d = self.probe.readFilteredDepthData()
            assert d is not None

        except Exception as e:
            raise(e)

    def test_get_raw_accleration_depth_data(self):
        """
        Test retrieve acceleration data from the probe
        """
        try:
            d = self.probe.readRawAccelerationData()
            assert d is not None

            # Make sure each sensor is not none also
            for sensor, data in d.items():
                assert data != None

        except Exception as e:
            raise(e)

    def test_get_sensor_depth_combo_data(self):
        """
        Test retrieve calibration data from the probe
        """
        try:
            d = self.probe.readDepthCorrectedSensorData()
            assert d is not None

            # Make sure each sensor is not none also
            for sensor, data in d.items():
                assert data != None

        except Exception as e:
            raise(e)

class TestLargeProbeData(TestProbeData):
    '''
    Test all the data with larger datsets sample rates
    '''
    measure_time = 0.1

    def test_get_calibrated_data(self):
        """
        Test retrieve calibration data from the probe
        """
        try:
            d = self.probe.readCalibratedSensorData()
            assert d is not None

            # Make sure each sensor is not none also
            for sensor, data in d.items():
                assert data != None
        except Exception as e:
            raise(e)



if __name__ == '__main__':
    unittest.main()
