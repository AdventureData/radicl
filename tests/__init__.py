class MockSerialPort():
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
    def __init__(self, payload=None,):
        self.payload = payload

    def openPort(self):
        pass

    def closePort(self):
        pass

    def flushPort(self):
        pass

    def writePort(self, data):
        pass

    def writePortClean(self):
        pass

    def readPort(self):
        return self.payload

    def numBytesInBuffer(self):
        pass
