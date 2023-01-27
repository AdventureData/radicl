from radicl.probe import RAD_Probe
import pandas as pd
import numpy as np


def probe_not_connected():

    # Create a bool to use for skipping tests
    try:
        RAD_Probe()
        not_connected = False

    except:
        not_connected = True

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

class MockProbe():
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
        if data_name == 'rawsensor':
            data['time'] = np.linspace(0, 1, 4)

            for c in ['Sensor1', 'Sensor2', 'Sensor3']:
                data[c] = np.linspace(1000, 4000, 4)

        elif data_name == 'filtereddepth':
            data['time'] = np.linspace(0, 1, 2)
            data['filtereddepth'] = np.linspace(0, 100, 2)

        elif data_name == 'rawacceleration':
            data['time'] = np.linspace(0, 1, 3)
            data['Y-Axis'] = np.linspace(0, 2, 3)

        result = pd.DataFrame(data)

        return result
