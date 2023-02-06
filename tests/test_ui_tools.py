import inspect
import unittest

import pytest

from radicl.probe import RAD_Probe
from radicl.ui_tools import *


@unittest.skip('Incomplete test. Needs work')
class TestUITools(unittest.TestCase):
    def test_parse_func_list(self):
        """
        Test we can parse the functions in the API for user interaction
        """
        api_funcs = inspect.getmembers(
            RAD_Probe, )  # predicate=inspect.ismethod)
        # print(api_funcs)
        result = parse_func_list(
            api_funcs, [
                'read', 'Data'], ignore_keywords=['correlation'])

        for v in ['depth', 'filtereddepth', 'rawpressure']:
            assert v in result.keys()

@pytest.mark.parametrize("idx, ratio, n_samples, expected", [
    (10, 1.1, 10, 9),
    (1, 0.9, 10, 0)
])
def test_get_index_from_ratio(idx, ratio, n_samples, expected):
    result = get_index_from_ratio(idx, ratio, n_samples)
    assert result == expected


if __name__ == '__main__':
    unittest.main()
