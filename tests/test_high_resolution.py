from radicl.high_resolution import build_high_resolution_data
import pytest
from radicl.ui_tools import get_logger
import numpy as np
from . import MOCKCLI

class TestBuildingHighResolution:
    """
    This function is quite critical, so we test it in great detail here
    """
    @pytest.fixture(scope='class')
    def df(self):
        cli = MOCKCLI()
        log = get_logger('test_high_res')
        df = build_high_resolution_data(cli, log)
        return df

    def test_no_nans(self, df):
        """ Ensure we have interpolated all nans"""
        assert ~np.any(np.isnan(df))

    @pytest.mark.parametrize('column, index, expected', [
        ('depth', 0, 0),
        ('depth', 19, -100),
        ('Y-Axis', 19, 2),
        ('Sensor1', 0, 1000),
        ('Sensor1', 19, 4000),
    ])
    def test_specific_value(self, df, column, index, expected):
        assert df[column].iloc[index] == expected

