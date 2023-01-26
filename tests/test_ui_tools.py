import inspect
import unittest

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


if __name__ == '__main__':
    unittest.main()
