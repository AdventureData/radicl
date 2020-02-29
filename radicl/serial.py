# coding: utf-8

import sys

import serial
from serial.tools import list_ports

from .ui_tools import get_logger


def find_kw_port(kw):
    """
    Find a com port by looking at Keyword attributes of the port

    Args:
            kw: List of kw to use (not case sensitive)
    Return:
            match_list: list of port names that have at least one matching keyword
    """

    match_list = []

    # Run through all available COM ports grabs ones that match our keywords
    port_list = list_ports.comports()

    for p in port_list:
        # Make a list of true for every keyword we find in the port data
        kw_match = [True for k in kw if k.lower() in p[1].lower()]

        # If the match list is not empty append this port name
        if kw_match:
            match_list.append(p)

    # Throw an exception if there are no ports
    if not match_list:
        raise IOError("No COM ports found")

    return match_list


class RAD_Serial():
    """
    This class handles all serial communication and simply acts
    as an abstraction layer
    """

    def __init__(self):
        self.serial_port = None
        self.log = get_logger(__name__, level='DEBUG')

    def openPort(self, com_port=None):

        # No COM port has been provided. Need to detect port automatically
        if (com_port is None):
            self.log.info("No COM port provided. Scanning for COM ports...")

            match_list = find_kw_port(['STMicroelectronics', 'STM32'])

            # Check if more than one was found
            if(len(match_list) > 1):
                self.log.warn('Multiple COM ports found, using the first')

            # Finally, assign the found port to the serial_port variable
            this_p = match_list[0]
            com_port = this_p[0]

        try:
            self.log.debug(
                "Attempting to establish a connection with the probe...")
            self.serial_port = serial.Serial(port=com_port,
                                             baudrate=115200,
                                             parity=serial.PARITY_NONE,
                                             stopbits=serial.STOPBITS_ONE,
                                             bytesize=serial.EIGHTBITS,
                                             timeout=0.01,
                                             write_timeout=0,
                                             xonxoff=False,
                                             rtscts=False,
                                             dsrdtr=False)
            self.serial_port.setDTR(1)

        except Exception as e:
            self.log.error("Serial port open failed: %s" % e)
            raise IOError("Could not open COM port")

            self.log.info("Using %s" % serial_port.port)

    def closePort(self):
        if (self.serial_port is not None):
            self.serial_port.close
            self.serial_port = None

    def flushPort(self):
        if (self.serial_port is not None):
            self.serial_port.flushOutput()

    def writePort(self, data):
        """
        Writes data to the serial port
        """

        if (self.serial_port is not None):
            return self.serial_port.write(serial.to_bytes(data))

    def writePortClean(self, data):
        """
        Writes data to the serial port, but first clears the input buffer if
        there is data. This ensures that the next read will be alligned with
        the response from this write
        """

        if (self.serial_port is not None):
            if (self.self.numBytesInBuffer() > 0):
                self.self.flushPort()

            return self.serial_port.write(serial.to_bytes(data))

    def readPort(self, numBytes=None):
        if (self.serial_port is not None):
            if (numBytes is None):
                # No number of specifed bytes to read. Read all available bytes
                return self.serial_port.read(self.serial_port.inWaiting())
            else:
                return self.serial_port.read(numBytes)

    def numBytesInBuffer(self):
        if (self.serial_port is not None):
            return self.serial_port.inWaiting()
        return 0
