from radicl.interface import dataframe_this, RADICL
from study_lyte.io import (MEASUREMENT_ID_KEY, find_measurement_id,
                           new_measurement_id, read_csv)
from uuid import UUID
import pytest
import pandas as pd


@pytest.mark.parametrize('data, name, expected', [
    ({"sensor": [1, 2, 3]}, None, pd.DataFrame.from_dict({"sensor": [1, 2, 3]})),
    ([1, 2, 3], 'sensor', pd.DataFrame.from_dict({"sensor": [1, 2, 3]}))
])
def test_dataframe_this(data, name, expected):
    df = dataframe_this(data, name=name)
    pd.testing.assert_frame_equal(df, expected)



class _FakeProbe:
    """Just enough probe to build a header, so no hardware is needed."""

    def getProbeHeader(self):
        return {'RECORDED': '2026-07-20--21:44:55',
                'radicl VERSION': '0.12.2',
                'Serial Num.': 'ABCD100A0E010001'}


class _FakeCLI:
    """
    write_probe_data only ever reaches for self.probe, so borrowing the method
    exercises the real code without standing up a RADICL and a serial port.
    """

    write_probe_data = RADICL.write_probe_data

    def __init__(self):
        self.probe = _FakeProbe()


class TestMeasurementId:
    """
    Every measurement radicl writes has to come out with an id.

    It is what an upload keys on, so a retry over a bad connection resolves to
    the same file rather than storing a second copy. The pair it replaces,
    (Serial Num., RECORDED), collides when two measurements are taken inside
    the same second.
    """

    @pytest.fixture()
    def df(self):
        return pd.DataFrame({'depth': [0.0, -1.0, -2.0], 'Sensor1': [10, 20, 30]})

    def test_written_files_carry_a_uuid4(self, tmp_path, df):
        out = tmp_path / 'measurement.csv'

        _FakeCLI().write_probe_data(df, filename=str(out))

        _, meta = read_csv(str(out))
        value = find_measurement_id(meta)

        assert UUID(value).version == 4

    def test_every_measurement_gets_its_own(self, tmp_path, df):
        ids = set()

        for i in range(5):
            out = tmp_path / f'measurement_{i}.csv'
            _FakeCLI().write_probe_data(df, filename=str(out))
            _, meta = read_csv(str(out))
            ids.add(find_measurement_id(meta))

        assert len(ids) == 5

    def test_an_id_passed_in_is_kept(self, tmp_path, df):
        """
        Rewriting an existing measurement must not rename it, or the copy
        already uploaded and the one on disk stop being the same thing.
        """
        out = tmp_path / 'measurement.csv'
        existing = new_measurement_id()

        _FakeCLI().write_probe_data(df, filename=str(out),
                                    extra_meta={MEASUREMENT_ID_KEY: existing})

        _, meta = read_csv(str(out))

        assert find_measurement_id(meta) == existing

    def test_the_rest_of_the_header_survives(self, tmp_path, df):
        out = tmp_path / 'measurement.csv'

        _FakeCLI().write_probe_data(df, filename=str(out),
                                    extra_meta={'Latitude': '43.566'})

        _, meta = read_csv(str(out))

        assert meta['Serial Num.'] == 'ABCD100A0E010001'
        assert meta['Latitude'] == '43.566'
        assert find_measurement_id(meta) is not None

    def test_an_empty_frame_writes_nothing(self, tmp_path):
        out = tmp_path / 'measurement.csv'

        _FakeCLI().write_probe_data(pd.DataFrame(), filename=str(out))

        assert not out.exists()
