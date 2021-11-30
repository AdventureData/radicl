import unittest

from radicl.probe import RAD_Probe


class TestProbeSettings(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.probe = RAD_Probe()

    def run_fn(self, fn, **kwargs):
        try:
            d = fn(**kwargs)
            assert d != None
            return d

        except Exception as e:
            raise(e)

    def run_setting(self, setting_name, value_in):
        '''
        Run a test of a probe setting. Attempts to grab a value,
        change a value and change it back.
        '''
        # Grab the original setting
        d_o = self.run_fn(self.probe.getSetting, setting_name=setting_name)

        # Assert that its not none and its the value requested
        self.run_fn(self.probe.setSetting, setting_name=setting_name, value=value_in)

        d_n = self.run_fn(self.probe.getSetting, setting_name=setting_name)
        assert d_n == value_in

        # Change it back to avoid messing up probe settings
        self.run_fn(self.probe.setSetting, setting_name=setting_name, value=d_o)


    def test_zpfo(self):
        '''
        Tests changing the zpfo
        '''
        self.run_setting('zpfo', 100)

    def test_accthreshold(self):
        self.run_setting('accthreshold', 100)

    def test_acczpfo(self):
        self.run_setting('acczpfo', 20)

    def test_alg(self):
        # Timeseries?
        self.run_setting('alg', 0)

    def test_appp(self):
        self.run_setting('appp', 16)

    def test_calibdata(self):
        pass

    def test_ir(self):
        self.run_setting('ir', 0)

    def test_ppmm(self):
        self.run_setting('ppmm',5)

    def test_samplingrate(self):
        self.run_setting('samplingrate', 5000)

    def test_tcm(self):
        self.run_setting('tcm', 1)
        self.run_setting('tcm', 2)

    def test_usertemp(self):
        self.run_setting('usertemp', 15)


    # def test_get_calibration_data(self):
    #     """
    #     Test retrieve calibration values from the probe
    #     """
    #     # Loop through 1-4 sensors
    #     for i in range(1, 5):
    #         d = self.probe.getSetting(setting_name='calibdata', sensor=1)
    #
    #         # Confirm calibration data is always length 2
    #         assert len(d) == 2
    #
    #         # confirm its in the 12 bit range
    #         for dv in d:
    #             assert dv < 4096
    #             assert dv >= 0


if __name__ == '__main__':
    unittest.main()
