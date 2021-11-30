import time
import unittest
from radicl.probe import RAD_Probe


class TestProbeData(unittest.TestCase):
    """
    Test all the probe data
    """
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

    def run_datatest(self, fn):
        """
        Pass the probe data function to run. Apply a try and except.
        Assert all data is not none.
        """
        try:
            d = fn()
            assert d is not None

        except Exception as e:
            raise e


class TestSmallProbeData(TestProbeData):
    """
    Test all the data with lower sample rates so we take a larger measurement
    """
    measure_time = 0.5

    def test_get_FilteredDepth_data(self):
        """
        Test retrieve filtered depth data from the probe
        """
        fn = self.probe.readFilteredDepthData
        self.run_datatest(fn)

    def test_get_raw_accleration_depth_data(self):
        """
        Test retrieve acceleration data from the probe
        """
        fn = self.probe.readRawAccelerationData
        self.run_datatest(fn)

    def test_get_sensor_depth_combo_data(self):
        """
        Test retrieve calibration data from the probe
        """

        fn = self.probe.readDepthCorrectedSensorData
        self.run_datatest(fn)

    @unittest.skip('Not working, needs some looking at with FW')
    def test_get_temperature(self):
        """
        Reads the temperature from the last measurement
        """
        try:
            d = self.probe.readMeasurementTemperature()
            print(d)
            assert d is not None
            assert type(d) == float

        except Exception as e:
            raise e


class TestLargeProbeData(TestProbeData):
    """
    Test all the data with larger datsets sample rates
    """
    measure_time = 0.1

    def test_get_calibrated_data(self):
        """
        Test retrieve calibration data from the probe
        """

        fn = self.probe.readCalibratedSensorData
        self.run_datatest(fn)


if __name__ == '__main__':
    unittest.main()
