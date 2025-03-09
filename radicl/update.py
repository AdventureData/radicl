# coding: utf-8

import binascii
import hashlib
import time
from enum import Enum
from .ui_tools import get_logger
from .info import Firmware
from .api import RAD_API


class FWState(Enum):
    """Mirror class of the FW update states"""
    IDLE = 0
    PREPARE = 1
    READY_TO_UPDATE = 2
    DOWNLOAD = 3
    DOWNLOAD_COMPLETE = 4
    VERIFICATION = 5
    DONE = 6
    ERROR = 7
    # If we cant id the state use this
    UNKNOWN = None

    @classmethod
    def from_int(cls, state_int):
        result = cls.UNKNOWN

        for e in cls:
            if e.value == state_int:
                result = e
                break
        return result


class FW_Update:

    # *********************
    # * PRIVATE FUNCTIONS *
    # *********************

    def __init__(self, api:RAD_API):
        self.f = None
        self.api = api
        self.file_crc = 0
        self._packet_size = None
        self.log = get_logger(__name__, debug=True)
        self.state = FWState.UNKNOWN

    @property
    def packet_size(self):
        """ Get the packet size based on the fw"""

        if self._packet_size is None:
            if self.api.fw_rev >= Firmware('1.45'):
                self._packet_size = 64
            else:
                self._packet_size = 16
        return self._packet_size

    def __getFileSize(self):
        """
        Returns the file size of the specified file
        """

        self.f.seek(0, 2)  # move the cursor to the end of the file
        size = self.f.tell()
        return size

    def __swapBytesInWord(self, fourBytes):
        """
        Helper function to swap a word (4 bytes)
        """

        return [fourBytes[3], fourBytes[2], fourBytes[1], fourBytes[0]]

    def __swapBytesInArray(self, byteArray):
        """
        Helper function to swap bytes in an array (LSByte to MSByte)
        """

        length = len(byteArray)
        swappedArray = bytearray(length)
        index = 0
        offset = 0
        four_count = 4
        for b in byteArray:
            swappedArray[offset + four_count - 1] = byteArray[index]
            index += 1
            four_count = four_count - 1
            if four_count == 0:
                offset = index
                four_count = 4
        return swappedArray

    def __LoadFileHeader(self):
        """
        Loads/reads the file header
        """

        self.f.seek(2048, 0)
        bytes = self.f.read(4)
        hex_string1 = "".join("%02x" %
                              b for b in self.__swapBytesInWord(bytes))
        bytes = self.f.read(4)
        hex_string2 = "".join("%02x" %
                              b for b in self.__swapBytesInWord(bytes))

        if hex_string1 == "dabbad00" and hex_string2 == "a5b6c7d8":
            bytes = self.f.read(4)
            hex_string = "".join("%02x" %
                                 b for b in self.__swapBytesInWord(bytes))

            self.app_header_version = int(hex_string, 16)
            bytes = self.f.read(4)
            hex_string = "".join("%02x" %
                                 b for b in self.__swapBytesInWord(bytes))

            self.app_header_length = int(hex_string, 16)
            bytes = self.f.read(4)
            hex_string = "".join("%02x" %
                                 b for b in self.__swapBytesInWord(bytes))

            self.app_header_entry = int(hex_string, 16)
            bytes = self.f.read(4)
            hex_string = "".join("%02x" %
                                 b for b in self.__swapBytesInWord(bytes))

            self.app_header_crc = int(hex_string, 16)
            return 1

        # Header magic words did not match.
        else:
            return 0

    def __DumpHeaderInfo(self):
        """
        Dumps the header info
        """

        self.log.info("*** Header Info ***"
                      "\nVersion\t=\t%d"
                      "\nApp length =\t%d"
                      "\nEntry\t=\t0x%0.8X"
                      "\nCRC\t=\t0x%0.8X" % (self.app_header_version,
                                             self.app_header_length,
                                             self.app_header_entry,
                                             self.app_header_crc))
        return 0

    def __CalculateAppCRC(self):
        # Set the file pointer to the beginning of the application section
        self.f.seek(self.app_header_entry, 0)
        # Read the entire application section from the file
        app_bytes = self.f.read(self.app_header_length)
        byte_string = "".join("%02x" %
                              b for b in self.swapBytesInWord(app_bytes))
        self.log.debug(
            "CRC non-swapped =\t0x%.08X, 0x%.08X" %
            (binascii.crc32(
                app_bytes,
                0x4C11DB7),
             (0x100000000 -
              binascii.crc32(
                  app_bytes,
                  0x4C11DB7))))
        self.log.debug(
            "CRC swapped =\t0x%.08X, 0x%.08X" %
            (binascii.crc32(
                self.__swapBytesInArray(app_bytes),
                0x4C11DB7),
             (0x100000000 -
              binascii.crc32(
                  self.__swapBytesInArray(app_bytes),
                  0x4C11DB7))))

        # return sum(app_bytes)
        return binascii.crc32(app_bytes)

    def __CalculateImageCRC32(self):
        """
        Calculates the CRC32 of the entire FW image file
        """

        file_len = self.__getFileSize()
        self.f.seek(0, 0)
        data = self.f.read(file_len)
        return binascii.crc32(data)

    def __CalculateChecksum(self, data):
        """
        Calculates the checmsum of the supplied data package
        """

        s = sum(data)
        return s % 256

    def __calculateNumDataPackets(self):
        """
        Calculates the number of data packets based on the file size
        """

        file_size = self.__getFileSize()
        num_packets = file_size / self.packet_size
        self.num_packets = num_packets
        return num_packets

    # ********************
    # * PUBLIC FUNCTIONS *
    # ********************

    def loadFile(self, file_name):
        """
        Loads and opens a FW update file
        This also verifies the file integrity and CRC
        Returns 1 if operation succeeded
        """

        try:
            self.f = open(file_name, "rb")
        except Exception as e:
            self.log.error(e)
            self.f = None
            return 0
        else:
            self.file_crc = self.__CalculateImageCRC32()
            self.log.debug("File CRC32 = 0x%08X" % self.file_crc)
            hash_md5 = hashlib.md5()
            self.f.seek(0, 0)
            for chunk in iter(lambda: self.f.read(4096), b""):
                hash_md5.update(chunk)
            self.log.debug("MD5 = %s" % hash_md5.hexdigest())

            # If we get here then the file is valid and can be used
            return 1

    def closeFile(self):
        """
        Closes the file
        """

        self.f.close()
        self.f = None

    def getState(self):
        """
        Returns the current state of the update FSM
        Returns the state if successful, None otherwise
        """
        ret = self.api.UpdateGetState()
        state = FWState.UNKNOWN

        if ret['status'] == 1:
            byte_arr = ret['data']
            state_int = int.from_bytes(byte_arr, byteorder='little')
            state = FWState.from_int(state_int)
            self.log.info(f"State = {state}({state_int})")
        else:
            if ret['errorCode'] is not None:
                self.log.error(
                    "FW_Update.getState returned error %d" %
                    ret['errorCode'])
            state = FWState.ERROR

        self.state = state

        return self.state

    def waitForStateChange(self, timeout):
        """
        Waits for an update FSM state change message
        Returns the new state if successful, None if timeout or incorrect
        response
        """
        state = FWState.UNKNOWN
        ret = self.api.UpdateWaitForStateChange(timeout)

        if ret['status'] == 1:
            byte_arr = ret['data']
            state_int = int.from_bytes(byte_arr, byteorder='little')
            state = FWState.from_int(state_int)

        # Retry in case of timeout
        else:
            self.log.debug("Timeout - Retrying!")
            state = self.getState()

        if ret['errorCode'] is not None:
            self.log.error("FW_Update.waitForStateChange returned error %d" %
                           ret['errorCode'])
            state = FWState.ERROR
        return state

    def closeFSM(self):
        """
        Closes the update FSM (i.e. reset)
        Returns 1 if successful, 0 otherwise
        """

        ret = self.api.UpdateClose()

        if ret['status'] == 1:
            return 1

        if ret['errorCode'] is not None:
            self.log.error(
                "FW_Update.closeFSM returned error %d" %
                ret['errorCode'])
        return 0

    def enterFSM(self):
        """
        Enter the FW update FSM (starts the process)
        Returns 1 if successful, 0 otherwise
        """
        ret = self.api.UpdateEnter()

        if ret['status'] == 1:
            self.log.info(
                "Enter bootloader mode - Waiting for Flash memory to be cleared. This could take a few seconds")
            state = self.waitForStateChange(10)

            if state is None:
                self.log.error("Timeout: No response")
                return 0

            else:
                if state == FWState.READY_TO_UPDATE:
                    self.log.info(
                        "Probe is in bootloader mode. Flash memory is ready!")
                    return 1

                self.log.error(f"Incorrect state ({state}")
                return 0

        if ret['errorCode'] is not None:
            self.log.error(
                "FW_Update.enterFSM returned error %d" %
                ret['errorCode'])
        self.log.error("Entering bootloader mode failed!!")
        return 0

    def sendNumPackets(self):
        """
        Sends the number of data packets and ensures we advance to the next step
        Returns 1 if successful, 0 otherwise
        """
        state = self.getState()

        if state == FWState.READY_TO_UPDATE:
            self.__calculateNumDataPackets()
            self.log.debug("Total number of packets = %d" % self.num_packets)
            ret = self.api.UpdateSetSize(int(self.num_packets),
                                         self.packet_size)
            if ret['status'] != 1:
                self.log.error("Unable to set number of packets")
                if ret['errorCode'] is not None:
                    self.log.error("FW_Update.sendNumPackets returned error %d" %
                                   ret['errorCode'])
                return 0

            time.sleep(1)
            state = self.getState()

            if state is None:
                self.log.error("Timeout - No response")
                return 0
            elif state != FWState.DOWNLOAD:
                self.log.error(f"Unexpected state ({state})")
                return 0
            else:
                self.log.info("Number of packages set and accepted")
                return 1
        else:
            if state is None:
                self.log.error("Incorrect or no response from device...")
            else:
                self.log.error(f"Incorrect state ({state})")
            return 0

    def download_packet(self, packet_id):
        """Attempts to download a single packet to the device for fw update"""
        data = self.f.read(self.packet_size)
        packet_id_arr = packet_id.to_bytes(4, byteorder='little')
        retry = True
        retry_count = 0
        error = True

        while retry:
            crc8 = self.__CalculateChecksum(data)
            if self.packet_size == 256:
                ret = self.api.UpdateDownload_Long(data,
                                                   crc8,
                                                   packet_id_arr[0])
            else:
                ret = self.api.UpdateDownload_Short(data,
                                                    crc8,
                                                    packet_id_arr[0])

            if ret['status'] != 1:
                # Packet was not accepted. Check if it was checksum
                # mismatch
                if ret['errorCode'] == 5121:
                    if retry_count > 3:
                        self.log.error(
                            "Max retries exceeded. Stopping.")
                        retry = False
                        error = True
                    else:
                        # Retry, by simply allowing to loop again
                        retry = True
                        retry_count = retry_count + 1
                        self.log.error(f"Checksum mismatch error. Retrying packet"
                                       f" {packet_id} (retry={retry_count})")

                # Error other than checksum mismatch.
                else:
                    self.log.error(f"Download error (Packet={packet_id})")
                    retry = False
                    error = True


            # Packet was accepted by device. Skip retry/ update
            # progress
            else:
                retry = False
                error = False

        return error

    def downloadFile(self):
        """
        Downloads the file in chunks
        Returns 1 if successful, 0 otherwise
        """
        state = self.getState()
        if state == FWState.DOWNLOAD:
            # Set the file pointer to the very beginning
            self.f.seek(0)
            packet_id = 0

            while packet_id < self.num_packets:
                error = self.download_packet(packet_id)
                if not error:
                    packet_id = packet_id + 1

            # If we get here then the entire download succeeded
            self.log.info("Download done - Waiting for state change")
            time.sleep(1)
            state = self.getState()
            if state is None:
                self.log.error("Timeout: No response")
                return 0
            elif state != FWState.DOWNLOAD_COMPLETE:
                self.log.error(f"Unexpected state ({state}")
                return 0
            # If we get here then the probe is in state 4 and we can move on
            return 1
        else:
            if state is None:
                self.log.error("Incorrect or no response from device...")
            else:
                self.log.error(f"Incorrect state ({state})")
            return 0

    def sendImageCRC32(self):
        """
        Sends the CRC32 of the entire FW image
        Returns 1 if successful, 0 otherwise
        """
        success = False
        # Check that we are in the right state
        state = self.getState()

        if state == FWState.DOWNLOAD_COMPLETE:
            ret = self.api.UpdateSetCRC(self.file_crc)

            if ret['status'] != 1:
                self.log.error("Error sending CRC32")

                if ret['errorCode'] is not None:
                    self.log.error("FW_Update.sendImageCRC32 returned error %d" %
                                   ret['errorCode'])
                success = False
            else:
                success = True
        else:
            self.log.warning(f"Probe not in the write state to set CRC, ({self.state})")
            success = False

        return success

    def verify(self):
        """Wait for the probe to respond after verification of the update image"""
        # Grab the state
        state = self.getState()

        # probe is still verifying
        if state == FWState.VERIFICATION:
            self.log.debug(
                "CRC32 set - Waiting for verification to complete")

        elif state == FWState.DONE:
            self.log.info(
                "Verification complete. FW image integrity check passed!")
            success = True

        else:
            self.log.error(f"Verification failed. New state = {state}")
            success = False

        return success

    def upgrade(self):
        """
        Upgrades the FW on the device
        """

        self.log.info("*** FW UPDATE PROCESS STARTED ***")
        # First, check if we need to reset the FSM
        state = self.getState()

        if state is FWState.UNKNOWN:
            self.log.error("No response from probe")
            return 0

        elif state != FWState.IDLE:
            self.log.warning(
                "Probe not ready for FW updates. Resetting the state machine...")
            if self.closeFSM() != 1:
                self.log.error("Unable to reset state machine")
                return 0

        self.log.info("*** Step 1: Enter the probe's bootloader mode ***")
        if self.enterFSM() != 1:
            self.log.error("Could not enter bootloader mod")
            return 0

        self.log.info("*** Step 2: Send number of packets ***")
        if self.sendNumPackets() != 1:
            self.log.error("Could not set number of packets")
            return 0

        self.log.info("*** Step 3: Downloading firmware ***")
        if self.downloadFile() != 1:
            self.log.error("Download failed")
            return 0

        self.log.info("*** Step 4: Setting CRC ***")
        if self.sendImageCRC32() != 1:
            self.log.error("Sending and verifying CRC32 failed")
            return 0

        self.log.info("Waiting for update completion.")
        while self.state not in [FWState.DONE, FWState.ERROR]:
            # TODO: This will advance even when there is an error...
            time.sleep(1)
            self.getState()

        self.log.info("*** Step 5: Apply (close state machine) ***")
        if self.closeFSM() != 1:
            self.log.error("Closing failed")
            return 0

        self.log.info(
            "===>>> FW Update COMPLETE. Device will disconnect and reboot <<<===")

        return 1
