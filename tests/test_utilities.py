import pytest
from radicl.utilities import is_numbered, add_ext, increment_fnumber


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

@pytest.mark.parametrize('filename, expected', [
    ('test.csv', 'test_1.csv'),
    ('test_test_10.csv', 'test_test_11.csv'),
])
def test_increment_fnumber(filename, expected):
    result = increment_fnumber(filename)
    assert result == expected
