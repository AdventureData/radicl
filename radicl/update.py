#============================================================
# This class handles all serial communication and simply acts
# as an abstraction layer
#============================================================
import time
import binascii
import hashlib

class FW_Update():

	#*********************
	#* PRIVATE FUNCTIONS *
	#*********************
	
	def __init__(self, api, packet_size):
		self.f = None
		self.api = api
		self.file_crc = 0
		self.packet_size = packet_size
	
	#Returns the file size of the specified file
	def __getFileSize(self):
		self.f.seek(0,2) # move the cursor to the end of the file
		size = self.f.tell()
		return size

	#Helper function to swap a word (4 bytes)
	def __swapBytesInWord(self, fourBytes):
		return [fourBytes[3], fourBytes[2], fourBytes[1], fourBytes[0]]
	
	#Helper function to swap bytes in an array (LSByte to MSByte)
	def __swapBytesInArray(self, byteArray):
		length = len(byteArray)
		swappedArray = bytearray(length)
		index = 0
		offset = 0
		four_count = 4
		for b in byteArray:
			swappedArray[offset + four_count - 1] = byteArray[index]
			index += 1
			four_count = four_count - 1
			if (four_count == 0):
				offset = index
				four_count = 4
		return swappedArray

	#Loads/reads the file header
	def __LoadFileHeader(self):
		self.f.seek(2048, 0)
		bytes = self.f.read(4)
		hex_string1 = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
		#print("Magic Word1 = 0x%s" % hex_string1)
		bytes = self.f.read(4)
		hex_string2 = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
		#print("Magic Word2 = 0x%s" % hex_string2)
		
		if (hex_string1 == "dabbad00" and hex_string2 == "a5b6c7d8"):
			bytes = self.f.read(4)
			hex_string = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
			#print("Header Version = %d" % int(hex_string, 16))
			self.app_header_version = int(hex_string, 16)
			bytes = self.f.read(4)
			hex_string = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
			#print("App Length = %d" % int(hex_string, 16))
			self.app_header_length = int(hex_string, 16)
			bytes = self.f.read(4)
			hex_string = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
			#print("App Entry Addr = 0x%s" % hex_string)
			self.app_header_entry = int(hex_string, 16)
			bytes = self.f.read(4)
			hex_string = "".join("%02x" % b for b in self.__swapBytesInWord(bytes))
			#print("App CRC = 0x%s" % hex_string)
			self.app_header_crc = int(hex_string, 16)
			return 1
		else:
			#Header magic words did not match.
			#print("Magic Word1 = 0x%s" % hex_string1)
			#print("Magic Word2 = 0x%s" % hex_string2)
			return 0

	def __DumpHeaderInfo(self):
		print("*** Header Info ***\nVersion\t=\t%d\nApp length =\t%d\nEntry\t=\t0x%0.8X\nCRC\t=\t0x%0.8X" % (self.app_header_version, self.app_header_length, self.app_header_entry, self.app_header_crc))
		return 0

	def __CalculateAppCRC(self):
		self.f.seek(self.app_header_entry, 0)	#Set the file pointer to the beginning of the application section
		app_bytes = self.f.read(self.app_header_length)	#Read the entire application section from the file
		byte_string = "".join("%02x" % b for b in self.swapBytesInWord(app_bytes))
		print("CRC non-swapped =\t0x%.08X, 0x%.08X" % (binascii.crc32(app_bytes, 0x4C11DB7), (0x100000000 - binascii.crc32(app_bytes, 0x4C11DB7))))
		print("CRC swapped =\t0x%.08X, 0x%.08X" % (binascii.crc32(self.__swapBytesInArray(app_bytes), 0x4C11DB7), (0x100000000 - binascii.crc32(self.__swapBytesInArray(app_bytes), 0x4C11DB7))))
	
		#return sum(app_bytes)
		return binascii.crc32(app_bytes)
	
	#Calculates the CRC32 of the entire FW image file
	def __CalculateImageCRC32(self):
		file_len = self.__getFileSize()
		self.f.seek(0, 0)
		data = self.f.read(file_len)
		return binascii.crc32(data)
	
	#Checks if the CRC of the app section reported in the file matches
	def __CheckAppCRC(self):
		return 1
	
	#Calculates the checmsum of the supplied data package
	def __CalculateChecksum(self, data):
		s = sum(data)
		return (s % 256)
	
	#Calculates the number of data packets based on the file size
	def __calculateNumDataPackets(self):
		file_size = self.__getFileSize()
		num_packets = file_size / self.packet_size
		self.num_packets = num_packets
		#self.num_packets = 16
		return num_packets
		
	#********************
	#* PUBLIC FUNCTIONS *
	#********************
	
	#Loads and opens a FW update file
	#This also verifies the file integrity and CRC
	#Returns 1 if operation succeeded
	def loadFile(self, file_name):
		try:
			self.f = open(file_name, "rb")
		except Exception as e:
			print (e)
			self.f = None
			return 0
		else:
			#self.__LoadFileHeader()
			#print("File Size = %d bytes" % self.__getFileSize())
			#self.__DumpHeaderInfo()
			self.file_crc = self.__CalculateImageCRC32()
			print("File CRC32 = 0x%08X" % self.file_crc)
			hash_md5 = hashlib.md5()
			self.f.seek(0,0)
			for chunk in iter(lambda: self.f.read(4096), b""):
				hash_md5.update(chunk)
			print("MD5 = %s" % hash_md5.hexdigest())
			
			#ret = self.__CheckAppCRC()
			#if (ret != 1):
			#	print("CRC mismatch!")
			#	return 0
			#If we get here then the file is valid and can be used
			return 1
	
	#Closes the file
	def closeFile(self):
		self.f.close()
		self.f = None
	
	#Returns the current state of the update FSM
	#Returns the state if successfull, None otherwise
	def getState(self):
		ret = self.api.UpdateGetState()
		if (ret['status'] == 1):
			byte_arr = ret['data']
			return int.from_bytes(byte_arr, byteorder='little')
		if (ret['errorCode'] != None):
			print("FW_Update.getState returned error %d" % ret['errorCode'])
		return None
	
	#Waits for an update FSM state change message
	#Returns the new state if successfull, None if timeout or incorrect response
	def waitForStateChange(self, timeout):
		ret = self.api.UpdateWaitForStateChange(timeout)
		if (ret['status'] == 1):
			byte_arr = ret['data']
			return int.from_bytes(byte_arr, byteorder='little')
		else:
			#Retry in case of timeout
			print("Timeout - Retry!")
			return self.getState()
		if (ret['errorCode'] != None):
			print("FW_Update.waitForStateChange returned error %d" % ret['errorCode'])
		return None
	
	#Closes the update FSM (i.e. reset)
	#Returns 1 if successfull, 0 otherwise
	def closeFSM(self):
		ret = self.api.UpdateClose()
		if (ret['status'] == 1):
			return 1
		if (ret['errorCode'] != None):
			print("FW_Update.closeFSM returned error %d" % ret['errorCode'])
		return 0
	
	#Enter the FW update FSM (starts the process)
	#Returns 1 if successfull, 0 otherwise
	def enterFSM(self):
		ret = self.api.UpdateEnter()
		if (ret['status'] == 1):
			print("Enter FSM - Waiting for state change")
			state = self.waitForStateChange(10)
			if (state == None):
				print("Timeout: No response")
				return 0
			else:
				if (state == 1):
					print("Waiting for preparation stage to finish...")
					state = self.waitForStateChange(10)
					if (state == None):
						print("Timeout: No response")
						return 0
				if (state == 2):
					print("FSM Enter Done!")
					return 1
				print("Error: Incorrect state (%d)" % state)
				return 0
		if (ret['errorCode'] != None):
			print("FW_Update.enterFSM returned error %d" % ret['errorCode'])
		print("Enter FSM - Failed!")
		return 0
		
	#Sends the number of data packets and ensures we advance to the next step
	#Returns 1 if successfull, 0 otherwise
	def sendNumPackets(self):
		state = self.getState()
		if (state == 2):
			self.__calculateNumDataPackets()
			print("Total number of packets = %d" % self.num_packets)
			ret = self.api.UpdateSetSize(int(self.num_packets), self.packet_size)
			if (ret['status'] != 1):
				print("Error setting number of packets")
				if (ret['errorCode'] != None):
					print("FW_Update.sendNumPackets returned error %d" % ret['errorCode'])
				return 0
			time.sleep(1)
			state = self.waitForStateChange(5)
			if (state == None):
				print("Timeout: No response")
				return 0
			else:
				print("New state = %s" % state)
				if (state == 3):
					return 1
				return 0
		else:
			if (state == None):
				print("Error: Incorrect or no response from device...")
			else:
				print("Error: Incorrect state (%d)" % state)
			return 0
			
	#Downloads the file in chuncks
	#Returns 1 if successfull, 0 otherwise
	def downloadFile(self):
		state = self.getState()
		if (state == 3):
			#Set the file pointer to the very beginning
			self.f.seek(0)
			packet_counter = 0
			retry_count = 0
			packet_id = 0
			
			for ii in range(0, int(self.num_packets)):
				data = self.f.read(self.packet_size)
				packet_id_arr = packet_id.to_bytes(4, byteorder='little')
				retry = 1
				retry_count = 0
				
				while(retry == 1):
					crc8 = self.__CalculateChecksum(data)
					if (self.packet_size == 256):
						ret = self.api.UpdateDownload_Long(data, crc8, packet_id_arr[0])
					else :
						ret = self.api.UpdateDownload_Short(data, crc8, packet_id_arr[0])
					if (ret['status'] != 1):
						#Packet was not accepted. Check if it was because of a checksum mismatch
						if (ret['errorCode'] == 5121):
							#Checksum mismatch detected. Check if we exceeded max. retries. If so, stop and exit with an error
							if (retry_count > 3):
								print ("Max retries exceeded. Stopping.")
								return 0
							#Retry, by simply allowing to loop again
							retry = 1
							retry_count = retry_count + 1
							print("Checksum mismatch error. Retrying packet %d (%d)" % (packet_id, retry_count))
						else:
							#Error other than checksum mismatch. Stop and exit with an error
							print("Download error (%d, Packet=%d)" % (ii, packet_id))
							return 0
					else:
						#Packet was accepted by device. Skip retry and update progress
						retry = 0
						pct = (100 * ii)/self.num_packets
						print("Progress = %d%%    " % pct, end="\r", flush=True)
						packet_id = packet_id + 1
						retry_count = 0
						
			#If we get here then the entire download succeeded
			print("Download done - Waiting for state change")
			time.sleep(1)
			state = self.waitForStateChange(5)
			if (state == None):
				print("Timeout: No response")
				print("Manually checking if state has changed")
				state = self.getState()
				print("New state = %d" % state)
				if (state == 4):
					return 1
				else:
					return 0
			return 1
		else:
			if (state == None):
				print("Error: Incorrect or no response from device...")
			else:
				print("Error: Incorrect state (%d)" % state)
			return 0
	
	#Sends the CRC32 of the entire FW image
	#Returns 1 if successfull, 0 otherwise
	def sendImageCRC32(self):
		#Check that we are in the right state
		state = self.getState()
		if (state == 4):
			ret = self.api.UpdateSetCRC(self.file_crc)
			if (ret['status'] != 1):
				print("Error sending CRC32")
				if (ret['errorCode'] != None):
					print("FW_Update.sendImageCRC32 returned error %d" % ret['errorCode'])
				return 0
			time.sleep(1)
			state = self.waitForStateChange(5)
			if (state == None):
				print("Timeout: No response")
				return 0
			if (state == 5):
				print("CRC32 set - Waiting for verification to complete")
				#upd_state = self.api.UpdateWaitForStateChange(2000)
				state = self.waitForStateChange(20)
				if (state == None):
					print("Timeout: No response")
					return 0
				if (state == 6):
					print("Verification complete")
					return 1
				else:
					print("Verification failed. New state = %d" % state)
					return 0
			elif (state == 6):
				print("CRC32 set - Verification complete!")
				return 1
			else:
				print("Setting CRC32 failed. New state = %d" % state)
				return 0
		else:
			if (state == None):
				print("Error: Incorrect or no response from device...")
			else:
				print("Error: Incorrect state (%d)" % state)
			return 0
	
	#Upgrades the FW on the device
	def upgrade(self):
		print("*** FW UPDATE PROCESS STARTED ***")
		#First, check if we need to reset the FSM
		state = self.getState()
		if (state == None):
			print("Error. No response")
			return 0
		elif (state != 0):
			print("FSM not in IDLE. Resetting...")
			if (self.closeFSM() != 1):
				print("Error: Closing failed")
				return 0
		print("Step 1: Enter FSM")
		if (self.enterFSM() != 1):
			print("Error: Could not enter FW Update FSM");
			return 0
		print("Step 2: Send number of packets")
		if (self.sendNumPackets() != 1):
			print("Error: Could not set number of packets")
			return 0
		print("Step 3: Downloading data")
		if (self.downloadFile() != 1):
			print("Error: Download failed")
			return 0
		print("Step 4: Setting CRC")
		if (self.sendImageCRC32() != 1):
			print("Error: Sending and verifying CRC32 failed")
			return 0
		print("Step 5: Close")
		if (self.closeFSM() != 1):
			print("Error: Closing failed")
			return 0
		print ("FW Update complete. Device will disconnect and reboot")
			
		return 1
	