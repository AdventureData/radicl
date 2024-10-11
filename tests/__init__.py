from radicl.probe import RAD_Probe
import pandas as pd
import numpy as np
from radicl.gps import USBGPS
from pynmeagps.nmeamessage import NMEAMessage
from pynmeagps.nmeahelpers import get_parts
from types import SimpleNamespace


def probe_not_connected():

    # Create a bool to use for skipping tests
    try:
        p = RAD_Probe()
        p.connect()
        not_connected = False

    except:
        not_connected = True

    return not_connected


def gps_not_connected():

    dev = USBGPS()
    if dev.cnx is None:
        not_connected = True
    else:
        not_connected = False

    return not_connected


class MockSerialPort:
    def __init__(self, **kwargs):
        # Add a byte array to be returned from read
        self.payload = 10

    def setDTR(self, num):
        pass

    def close(self):
        pass

    def reset_output_buffer(self):
        pass

    def write(self, data):
        return len(data)

    def read(self):
        pass

    def inWaiting(self):
        pass


class MockRADPort:
    def __init__(self, payload):
        self.payload = payload

    def openPort(self):
        pass

    def closePort(self):
        pass

    def flushPort(self):
        pass

    def writePort(self, data):
        return 1

    def writePortClean(self):
        return 1

    def readPort(self, nbytes):
        return self.payload

    def numBytesInBuffer(self):
        return len(self.payload)


class MockProbe:
    pass


class MOCKCLI:

    def grab_data(self, data_name):
        """
        Return a dataframe of the requested data
        Args:
            data_name: String of the data name to dataframe

        Returns:
            result: Dataframe
        """
        data = {}
        samples = 20
        if data_name == 'rawsensor':
            data['time'] = np.linspace(0, 1, samples)

            for c in ['Sensor1', 'Sensor2', 'Sensor3']:
                data[c] = np.linspace(1000, 4000, samples)

        elif data_name == 'filtereddepth':
            alt_samples = int(samples/3)
            data['time'] = np.linspace(0, 1, alt_samples)
            data['filtereddepth'] = np.linspace(100, 0, alt_samples)

        elif data_name == 'rawacceleration':
            alt_samples = int(samples/2)
            data['time'] = np.linspace(0, 1, alt_samples)
            data['Y-Axis'] = np.linspace(0, 2, alt_samples)

        result = pd.DataFrame(data)

        return result


class MockGPSStream:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        if self.payload:
            message = self.payload.pop()
            content, talker, msgid, payload, checksum = get_parts(message)

            return message,  NMEAMessage(
                    talker, msgid, 0, payload=payload, checksum=checksum)

        else:
            return b'', SimpleNamespace(msgID='NAN')

