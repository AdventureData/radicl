# coding: utf-8

import sys
import serial
from serial.tools import list_ports
from .ui_tools import get_logger

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
		if (com_port == None):
			self.log.info("No COM port provided. Scanning for COM ports...")
			match_list = list()

			# Run through all available COM ports and filter out the ones that match our requirement
			port_list = list_ports.comports()
			for p in port_list:
				if ('STMicroelectronics' in p[1] or 'STM32' in p[1]):
					match_list.append(p)

			#Throw an exception if there are no ports
			if not match_list:
				raise IOError("No COM ports found")

			#Check if more than one was found. If so, simply self.log.info a message
			if(len(match_list) > 1):
				self.log.info('Multiple COM ports found - using the first')

			#Finally, assign the found port to the serial_port variable
			this_p = match_list[0]
			try:
				self.serial_port = serial.Serial(port=this_p[0],
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
				self.log.error("Serial port open failed: %s" %e)
				self.serial_port = None
				raise IOError("Could not open port %s" % com_port.port)
			self.log.info("COM port found. Using %s" % self.serial_port.port)

		else:
			try:
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
				self.serial_port = None
				raise IOError("Could not open port %s" % com_port)

			self.log.info("Using %s" % serial_port.port)

	def closePort(self):
		if (self.serial_port != None):
			self.serial_port.close

	def flushPort(self):
		if (self.serial_port != None):
			self.serial_port.flushOutput()

	def writePort(self, data):
		"""
		Writes data to the serial port
		"""

		if (self.serial_port != None):
			return self.serial_port.write(serial.to_bytes(data))

	def writePortClean(self, data):
		"""
		Writes data to the serial port, but first clears the input buffer if
		there is data. This ensures that the next read will be alligned with
		the response from this write
		"""

		if (self.serial_port != None):
			if (self.self.numBytesInBuffer() > 0):
				self.self.flushPort()

			return self.serial_port.write(serial.to_bytes(data))

	def readPort(self, numBytes=None):
		if (self.serial_port != None):
			if (numBytes == None):
				# No number of specifed bytes to read. Read all available bytes
				return self.serial_port.read(self.serial_port.inWaiting())
			else:
				return self.serial_port.read(numBytes)

	def numBytesInBuffer(self):
		if (self.serial_port != None):
			return self.serial_port.inWaiting()
		return 0
