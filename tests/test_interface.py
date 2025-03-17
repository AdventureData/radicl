from radicl.interface import dataframe_this
import pytest
import pandas as pd


@pytest.mark.parametrize('data, name, expected', [
    ({"sensor": [1, 2, 3]}, None, pd.DataFrame.from_dict({"sensor": [1, 2, 3]})),
    ([1, 2, 3], 'sensor', pd.DataFrame.from_dict({"sensor": [1, 2, 3]}))
])
def test_dataframe_this(data, name, expected):
    df = dataframe_this(data, name=name)
    pd.testing.assert_frame_equal(df, expected)

