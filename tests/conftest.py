from unittest.mock import patch
import pytest

from radicl.serial import RAD_Serial
from radicl.api import RAD_API
from radicl.probe import RAD_Probe

@pytest.fixture()
def port():
    port = RAD_Serial(debug=True)
    port.openPort()
    yield port
    port.closePort()


@pytest.fixture()
def api(port):
    yield RAD_API(port, debug=True)

@pytest.fixture()
def probe():
    prb = RAD_Probe(debug=True)
    yield prb

@pytest.fixture()
def meas_probe():
    prb = RAD_Probe(debug=True)
    yield prb
    prb.resetMeasurement()
