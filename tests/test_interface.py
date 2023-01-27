from radicl.interface import RADICL, dataframe_this, is_numbered, get_default_filename, add_ext, increment_fnumber
import pytest
import pandas as pd
from unittest.mock import patch
import datetime
from . import MockProbe


@pytest.mark.parametrize('data, name, expected', [
    ({"sensor": [1, 2, 3]}, None, pd.DataFrame.from_dict({"sensor": [1, 2, 3]})),
    ([1, 2, 3], 'sensor', pd.DataFrame.from_dict({"sensor": [1, 2, 3]}))
])
def test_dataframe_this(data, name, expected):
    df = dataframe_this(data, name=name)
    pd.testing.assert_frame_equal(df, expected)


@pytest.mark.parametrize('filename, expected', [
    ('test_1000.csv', True),
    ('test_1000_numbers.csv', False),
    ('test.csv', False),
])
def test_is_numbered(filename, expected):
    result = is_numbered(filename)
    assert result == expected


@pytest.mark.parametrize('filename, expected', [
    ('test.csv', 'test.csv'),
    ('test', 'test.csv'),
])
def test_add_ext(filename, expected):
    result = add_ext(filename)
    assert result == expected


def test_get_default_filename():
    dt = datetime.datetime(2023, 1, 1, 1, 2, 3)
    with patch('radicl.interface.datetime.datetime') as mock_date:
        mock_date.now.return_value = dt
        filename = get_default_filename()
    assert filename == './2023-01-01--010203.csv'


@pytest.mark.parametrize('filename, expected', [
    ('test.csv', 'test_1.csv'),
    ('test_test_10.csv', 'test_test_11.csv'),
])
def test_increment_fnumber(filename, expected):
    result = increment_fnumber(filename)
    assert result == expected
