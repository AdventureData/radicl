from radicl.high_resolution import build_high_resolution_data
import pytest
from radicl.ui_tools import get_logger
import numpy as np


@pytest.mark.parametrize('data_name, expected_data', [
    ('depth', [-100, -75, -50, -25, 0]),
    ('Y-Axis', [0, 0.5, 1, 1.5, 2.0]),
    ('Sensor1', [1000, 2000, 2500, 3000, 4000]),
])
def test_build_high_resolution_data(mock_cli, data_name, expected_data):
    log = get_logger('test_high_res')
    df = build_high_resolution_data(mock_cli, log)
    np.testing.assert_array_equal(df[data_name].values, np.array(expected_data))
