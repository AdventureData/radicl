import pytest

from radicl.com import RAD_Serial
from radicl.api import RAD_API
from radicl.probe import RAD_Probe
from . import MOCKCLI


@pytest.fixture(scope='session')
def real_port():
    port = RAD_Serial(debug=True)
    port.openPort()
    yield port
    port.closePort()


@pytest.fixture(scope='session')
def real_api(real_port):
    yield RAD_API(real_port, debug=True)


@pytest.fixture(scope='session')
def real_probe():
    """
    Probe object with a reset at the end
    """
    prb = RAD_Probe(debug=True)
    yield prb
    prb.resetMeasurement()


@pytest.fixture()
def mock_cli():
    yield MOCKCLI()
