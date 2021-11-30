from radicl.high_resolution import pad_with_nans, build_high_resolution_data
import pytest
import pandas as pd
from radicl.ui_tools import get_logger
import numpy as np


@pytest.fixture(scope='session')
def cli():
    class MOCKCLI():
        def grab_data(self, data_name):
            """
            Return a dataframe of the requested data
            Args:
                data_name: String of the data name to dataframe

            Returns:
                result: Dataframe
            """
            data = {}

            if data_name == 'rawsensor':
                for c in ['Sensor1', 'Sensor2', 'Sensor3']:
                    data[c] = np.linspace(1000, 4000, 4)

            elif data_name == 'filtereddepth':
                data['filtereddepth'] = np.linspace(0, 100, 2)

            elif data_name == 'rawacceleration':
                data['Y-Axis'] = np.linspace(0, 2, 3)

            result = pd.DataFrame(data)

            return result

    return MOCKCLI()


@pytest.mark.parametrize('data_name, expected_data', [
    ('depth', [-100, -50, 0, 0]),
    ('acceleration', [0, 1, 2, 2]),
    ('Sensor1', [1000, 2000, 3000, 4000]),
])
def test_build_high_resolution_data(cli, data_name, expected_data):
    log = get_logger('test_high_res')
    df = build_high_resolution_data(cli, log)
    np.testing.assert_array_equal(df[data_name].values, np.array(expected_data))
