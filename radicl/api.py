# coding: utf-8

import sys
import binascii
import serial
import time
from radicl import serial as rs
from radicl.ui_tools import get_logger

pca_id_list = ["UNKNOWN", "PB1", "PB2", "PB3"]

class RAD_API():
	"""
	Class for directly interacting with the probe in a non-human friendly way
	"""

	def __init__(self, port):
		self.port = port
		self.log = get_logger(__name__, level='DEBUG')

	def __sendCommand(self, data):
		"""
		Generic send function
		Returns 1 of successfull, 0 otherwise
		"""

		success = 0
		try:
			#Send the data
			self.port.writePort(data)

		except Exception as e:
			self.log.error(e)

		else:
			success = 1

		finally:
			return success

	def __getResponse(self):
		"""
		Generic read function
		Returns 1 if successfull, 0 otherwise
		"""

		success = 0
		response = ""

		try:
			num_bytes_in_buffer = self.port.numBytesInBuffer()
			if (num_bytes_in_buffer > 0):
				response = self.port.readPort(num_bytes_in_buffer)

		except Exception as e:
			self.log.error(e)

		else:
			success = 1

		finally:
			if (success):
				return response
			else:
				return None

	def __send_receive(self, data, read_delay=0.05):
		"""
		Generic send/receive function
		Returns the response if successfull, empty result otherwise
		"""

		delay_counter = 0
		#Make sure that the read delay is at least 1ms (i.e. it cannot be 0)
		if (read_delay < 0.001):
			read_delay = 0.001
		ret = self.__sendCommand(data)

		if (ret):
			#The command was successfully sent. Now read the response
			time.sleep(0.001)
			ret = self.__getResponse()
			# Read the response as long as we don't get anything back AND
			# we haven't exceeded the max. read delay
			while (((ret == None) or (ret == "")) and (delay_counter < read_delay)):
				time.sleep(0.001)
				delay_counter = delay_counter + 0.001
				ret = self.__getResponse()
			# If we get here either we have exceeded the max. read delay, or
			#  we have received a response.
			return ret

		else:
			#There was an issue with sending the command
			return None

	def __isACK(self, message, cmd=None):
		"""
		Returns 1 if the message contains an ACK
		"""
		if (len(message) >= 5):
			#If a command was specified, check that it matches the message
			if (cmd != None):
				if (message[1] != cmd):
					return 0
			#If we get here then we have passed the additional specified checks.
			if (message[2] == 0x04):
				#ACK detectec
				return 1
			else:
				#No ACK found
				return 0
		else:
			#Message is not long enough. Indicate an error
			return 0

	def __isNACK(self, message, cmd=None):
		"""
		Returns 1 if the message contains a NACK
		"""

		if (len(message) >= 5):

			# If a command was specified, check that it matches the message
			if (cmd != None):
				if (message[1] != cmd):
					return 0

			# If we get here then we have passed the additional user specified checks.
			if (message[2] == 0x05):
				# NACK detectec
				return 1
			else:
				# No NACK found
				return 0
		else:
			# Message is not long enough. Indicate an error
			return 0

	def __getNACKValue(self, message):
		"""
		Returns the NACK message value
		If an error is detected, this will simply return 0
		"""

		if (len(message) >= 7):
			nack_val = message[5:7]
			return int.from_bytes(nack_val, byteorder='little')

		else:
			return 0;

	def __isResponse(self, message, cmd=None, data_len=None):
		"""
		Returns 1 if the message is a valid response
		0 for data_len means that the payload length could be variable
		"""

		length = len(message)
		if (length >= 5):
			if (message[2] == 0x02):
				calc_len = message[4] + 5
				# If a command was specified we need to check if it matches.
				# If it is incorrect we will return immediately
				if (cmd != None):
					if (message[1] != cmd):
						return 0
				# If a data length was specified we need to check if it
				# matches the message's data payload length. If it is incorrect we will return immediately
				if ((data_len != None) and (data_len != 0)):
					if (message[4] != data_len):
						return 0
				# If we get here then we have passed the additional
				# specified checks. Finally, check if the overall length
				# matches (integrity check)
				if (length == calc_len):
					#The length is correct
					return 1
				else:
					#Not a response or incorrect length
					return 0
			elif ( (message[2] == 0x06) and (length == 261) ):
				return 1
			else:
				return 0
		else:
			return 0

	def __getNumPayloadBytes(self, message):
		"""
		Returns the number of bytes present in the payload. This takes long #
		responses into account
		"""

		if (message[2] == 0x02):
			return message[4]
		elif (message[2] == 0x06):
			return 256
		else:
			return 0

	def __isPushMessage(self, message, cmd=None, data_len=None):
		"""
		Returns 1 if the message is a valid push message/response
		"""
		length = len(message)
		if (length >= 5):
			calc_len = message[4] + 5
			# If a command was specified we need to check if it matches.
			# If it is incorrect we will return immediately
			if (cmd != None):
				if (message[1] != cmd):
					return 0
			#If a data length was specified we need to check if it matches the
			#  message's data payload length. If it is incorrect we will
			# return immediately
			if (data_len != None):
				if (message[4] != data_len):
					return 0
			#If we get here then we have passed the additional user specified
			# checks. Finally, check if the message is a response and if the
			# overall length matches (integrity check)
			if ((message[2] == 0x03) and (length == calc_len)):
				# This is a response and the length is correct
				return 1
			else:
				# Not a response or incorrect length
				return 0
		else:
			# Message is not long enough. Indicate an error
			return 0

	def __waitForMessage(self, timeout):
		"""
		This function simply waits for a message. It is like a read, but waits
		up to the specified timeout for new data to arrive
		Args:
			timeout: specified in seconds. The smallest delay period is 0.01s
		"""

		delay_time = 0.01
		# Force the timeout to be at least 10ms
		if (timeout < delay_time):
			timeout = delay_time
		num_iter = timeout / delay_time
		while(num_iter):
			try:
				num_bytes_in_buffer = self.port.numBytesInBuffer()

				if (num_bytes_in_buffer > 0):
					response = self.port.readPort(num_bytes_in_buffer)
			except Exception as e:
				self.log.error(e)
			else:
				if (num_bytes_in_buffer >= 5):
					return response
				else:
					num_iter = num_iter - 1
					time.sleep(delay_time)
		return None

	def __EvaluateAndReturn(self, response, expected_command, num_expected_payload_bytes):
		"""
		This function evaluates the response and prepares the API return value
		If 'num_expected_payload_bytes' is 0, then the response guides how
		many bytes will be returned
		"""

		if (response == None):
			return {'status': 0, 'errorCode': None, 'data': None}

		elif (self.__isResponse(response, expected_command,
										  num_expected_payload_bytes)):
			return {'status': 1, 'errorCode': None,
								 'data': response[-(
								 		 self.__getNumPayloadBytes(response)):]}

		elif (self.__isPushMessage(response, expected_command,
											 num_expected_payload_bytes)):
			return {'status': 1, 'errorCode': None,
								 'data': response[-(
								 		 self.__getNumPayloadBytes(response)):]}

		elif (self.__isACK(response)):
			return {'status': 1, 'errorCode': None, 'data': None}

		elif (self.__isNACK(response)):
			nack_value = self.__getNACKValue(response)
			return {'status': 0, 'errorCode': nack_value, 'data': None}

		else:
			return {'status': 0, 'errorCode': None, 'data': None}

	#********************
	#* PUBLIC FUNCTIONS *
	#********************

	def sendApiPortEnable(self):
		"""
		Sends a '*' to enable the API port which tells the probe to interact
		via the radicl API
		"""
		self.port.writePort([0x21])

	def Identify(self):
		"""
		Identifies the connected device
		Returns 1 if a valid device was detected
		"""

		ret = self.getHWID()
		self.hw_id = ret['data']
		time.sleep(0.5)
		ret = self.getHWREV()
		self.hw_rev = ret['data']
		time.sleep(0.5)
		ret = self.getFWREV()
		self.fw_rev = ret ['data']

		if (self.hw_id != None):
			if (self.hw_id < len(pca_id_list)):
				self.log.info("Attached device: %s, Rev=%s, FW=%s" % \
				  									(pca_id_list[self.hw_id],
													self.hw_rev,
													format(self.fw_rev, '.02f')))
				return 1

			else:
				self.log.info("Unknown device detected!")
				return 0

		else:
			self.log.error("Invalid response to ID request")
			return 0


	# ***************************
	# ***** BASIC COMMANDS ******
	# ***************************
	def getSerialNumber(self):
		"""
		Queries the board's serial number
		"""
		response = self.__send_receive([0x9F, 0x04, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x04, 8)

	def getHWID(self):
		"""
		Queries the board's HW ID
		"""

		response = self.__send_receive([0x9F, 0x01, 0x00, 0x00, 0x00])
		ret_val = self.__EvaluateAndReturn(response, 0x01, 1)
		if (ret_val['status'] == 1):
			byte_arr = ret_val['data']
			data = int.from_bytes(byte_arr, byteorder='little')
			ret_val['data'] = data

		return ret_val

	def getHWREV(self):
		"""
		Queries the board's HW revision
		"""

		response = self.__send_receive([0x9F, 0x02, 0x00, 0x00, 0x00])
		ret_val = self.__EvaluateAndReturn(response, 0x02, 1)
		if (ret_val['status'] == 1):
			byte_arr = ret_val['data']
			data = int.from_bytes(byte_arr, byteorder='little')
			ret_val['data'] = data

		return ret_val

	def getFWREV(self):
		"""
		Queries the board's FW revision
		"""

		response = self.__send_receive([0x9F, 0x03, 0x00, 0x00, 0x00])
		ret_val = self.__EvaluateAndReturn(response, 0x03, 2)
		if (ret_val['status'] == 1):
			value = ret_val['data']
			major = value[0] #value[-2]
			minor = value[1] #value[-1]
			fw_rev = major + minor/100
			ret_val['data'] = fw_rev
		return ret_val

	def startBootloader(self):
		"""
		Starts the bootloader
		"""

		response = self.__send_receive([0x9F, 0x05, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x05, 0)

	def getSystemStatus(self):
		"""
		Queries the system status
		"""

		response = self.__send_receive([0x9F, 0x06, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x06, 4)

	def getRunState(self):
		response = self.__send_receive([0x9F, 0x07, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x07, 1)

	# ***************************************
	# ***** SENSOR/MEASUREMENT COMMANDS *****
	# ***************************************

	def getMeasState(self):
		"""
		Queries the state of the measurement state machine
		"""

		response = self.__send_receive([0x9F, 0x40, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x40, 1)

	def MeasReset(self):
		"""
		Resets the measurement state machine
		Returns 1 if successfull
		"""

		response = self.__send_receive([0x9F, 0x41, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x41, 0)


	def MeasStart(self):
		"""
		Starts a measurement
		Returns 1 if successful
		"""

		response = self.__send_receive([0x9F, 0x42, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x42, 0)


	def MeasStop(self):
		"""
		Stops a measurement
		Returns 1 if successfull
		"""

		response = self.__send_receive([0x9F, 0x43, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x43, 0)

	def MeasGetNumSegments(self, buffer_id):
		"""
		Queries the number of data segments for a particular data buffer
		"""
		message = [0x9F, 0x44, 0x00, 0x00, 0x01]
		message.extend(buffer_id.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x44, 4)

	def MeasReadDataSegment(self, buffer_id, numPacket):
		"""
		Reads a specific data segment of a specific data buffer
		"""

		message = [0x9F, 0x45, 0x00, 0x00, 0x05]
		message .extend(buffer_id.to_bytes(1, byteorder='little'))
		message.extend(numPacket.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)

		# Check if only the command matches. The length may be variable
		return self.__EvaluateAndReturn(response, 0x45, 0)

	def MeasGetSamplingRate(self):
		"""
		Reads/Returns the IR sampling rate
		"""

		response = self.__send_receive([0x9F, 0x46, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x46, 4)

	def MeasSetSamplingRate(self, sampling_rate):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Sets the sensor sampling rate
		"""

		message = [0x9F, 0x46, 0x01, 0x00, 0x04]
		message.extend(sampling_rate.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x46, 0)

	def MeasGetZPFO(self):
		"""
		Reads/returns the Zero Phase Filter Order used on the depth data.
		"""

		response = self.__send_receive([0x9F, 0x47, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x47, 4)

	def MeasSetZPFO(self, zpfo):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Set the Zero Phase Filter Order used on the depth data.
		"""

		message = [0x9F, 0x47, 0x01, 0x00, 0x04]
		message.extend(zpfo.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x47, 0)

	def MeasGetPPMM(self):
		"""
		Reads/returns the Points per millimeter parameter
		"""

		response = self.__send_receive([0x9F, 0x48, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x48, 1)

	def MeasSetPPMM(self, ppmm):
		"""
		helpme - Sets the Points per millimeter parameter
		"""

		message = [0x9F, 0x48, 0x01, 0x00, 0x01]
		message.extend(ppmm.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x48, 0)

	def MeasGetALG(self):
		"""
		Reads/Returns the algorithm (1 - depth corrected, 2 for timeseries only)
	 	parameter
		"""

		response = self.__send_receive([0x9F, 0x49, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x49, 1)

	def MeasSetALG(self, alg):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Sets the algorithm (1 - depth corrected, 2 for timeseries only)
		"""

		message = [0x9F, 0x49, 0x01, 0x00, 0x01]
		message.extend(alg.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x49, 0)

	def MeasGetAPPP(self):
		"""
		Reads the APPP parameter
		"""

		response = self.__send_receive([0x9F, 0x4A, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x4A, 1)

	def MeasSetAPPP(self, appp):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Sets the APPP parameter which smooths the timeseries data

		"""

		message = [0x9F, 0x4A, 0x01, 0x00, 0x01]
		message.extend(appp.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4A, 0)

	def MeasGetTCM(self):
		"""
		Reads the TCM parameter
		"""

		response = self.__send_receive([0x9F, 0x4B, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x4B, 1)

	def MeasSetTCM(self, tcm):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Sets the Temperature correction method for the barometer data

		"""

		message = [0x9F, 0x4B, 0x01, 0x00, 0x01]
		message.extend(tcm.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4B, 0)

	def MeasGetUserTemp(self):
		"""
		Reads the user set tempreature
		"""

		response = self.__send_receive([0x9F, 0x4C, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x4C, 4)

	def MeasSetUserTemp(self, user_temp):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Set the user specifed temperature for TCM=3
		"""
		message = [0x9F, 0x4C, 0x01, 0x00, 0x04]
		message.extend(user_temp.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4C, 0)

	def MeasGetIR(self):
		"""
		Reads the IR parameter

		"""
		response = self.__send_receive([0x9F, 0x4D, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x4D, 1)

	def MeasSetIR(self, ir):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Turns on the IR emitter
		"""
		message = [0x9F, 0x4D, 0x01, 0x00, 0x01]
		message.extend(ir.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4D, 0)

	def MeasGetCalibData(self, num_sensor):
		"""
		Reads a sensor's calibration value
		"""

		message = [0x9F, 0x4E, 0x00, 0x00, 0x01]
		message.extend(num_sensor.to_bytes(1, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4E, 4)

	def MeasSetCalibData(self, num_sensor, calibration_value):
		"""
		Returns status=1 if successfull, status=0 otherwise

		helpme - Sets the calibration data for the specified sensor
		"""

		message = [0x9F, 0x4E, 0x01, 0x00, 0x05]
		message.extend(num_sensor.to_bytes(1, byteorder='little'))
		message.extend(calibration_value.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0x4E, 0)

	def MeasGetMeasTemp(self):
		"""
		Reads the current temperature reading (from last measurement)
		Returns status=1 if successfull, status=0 otherwise
		"""

		response = self.__send_receive([0x9F, 0x4F, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0x4F, 0)

	# ******************************
	# ***** FW UPDATE COMMANDS *****
	# ******************************

	def UpdateEnter(self):
		"""
		Enters the FW Update FSM
		Returns status=1 if successfull, status=0 otherwise
		"""

		response = self.__send_receive([0x9F, 0xF0, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0xF0, 0)

	def UpdateGetState(self):
		"""
		Gets the FW update FSM state
		"""

		response = self.__send_receive([0x9F, 0xF1, 0x00, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0xF1, 1)

	def UpdateWaitForStateChange(self, wait_time):
		"""
		Waits for the state change message
		"""

		response = self.__waitForMessage(wait_time)
		return self.__EvaluateAndReturn(response, 0xF1, 1)

	def UpdateSetSize(self, num_packets, packet_size):
		"""
		Sets the update size
		Returns status=1 if successfull, status=0 otherwise
		"""

		message = [0x9F, 0xF2, 0x01, 0x00, 0x06]
		message.extend(num_packets.to_bytes(4, byteorder='little'))
		message.extend(packet_size.to_bytes(2, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0xF2, 0)

	def UpdateDownload_Short(self, data, crc8, packet_id):
		"""
		Downloads a 16-byte chunck of data
		Returns status=1 if successfull, status=0 otherwise
		"""

		message = [0x9F, 0xF3, 0x01, 0x00, 0x00]
		message[3] = crc8
		message[4] = 16
		message.extend(data)
		self.__sendCommand(message)
		response = self.__waitForMessage(20)
		return self.__EvaluateAndReturn(response, 0xF3, 0)

	def UpdateDownload_Long(self, data, crc8, packet_id):
		"""
		Downloads a 256-byte chunck of data
		Returns status=1 if successfull, status=0 otherwise
		"""

		message = [0x9F, 0xF3, 0x07, 0x00, 0x00]
		message[3] = crc8
		message[4] = 0
		message.extend(data)
		self.__sendCommand(message)
		response = self.__waitForMessage(20)
		return self.__EvaluateAndReturn(response, 0xF3, 0)

	def UpdateSetCRC(self, crc32):
		"""
		Sets the CRC32 of the FW image
		Returns status=1 if successfull, status=0 otherwise
		"""

		message = [0x9F, 0xF4, 0x01, 0x00, 0x04]
		message.extend(crc32.to_bytes(4, byteorder='little'))
		response = self.__send_receive(message)
		return self.__EvaluateAndReturn(response, 0xF4, 0)

	def UpdateClose(self):
		"""
		Closes the FW update FSM
		Returns status=1 if successfull, status=0 otherwise
		"""

		response = self.__send_receive([0x9F, 0xF5, 0x01, 0x00, 0x00])
		return self.__EvaluateAndReturn(response, 0xF5, 0)
