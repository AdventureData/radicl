# coding: utf-8

import time

from .ui_tools import get_logger
from .commands import MeasCMD, SystemCMD, SettingsCMD, FWUpdateCMD, AttributeCMD

PCA_ID_LIST = ["UNKNOWN", "PB1", "PB2", "PB3"]


class RAD_API:
    """
    Class for directly interacting with the probe in a non-human friendly way
    """

    def __init__(self, port, debug=False):
        self.port = port
        self.log = get_logger(__name__, debug=debug)
        self._serial = None
        self._hw_id = None
        self._hw_id_str = None
        self._hw_rev = None
        self._fw_rev = None
        self._full_fw_rev = None

    def __sendCommand(self, data):
        """
        Generic send function
        Returns 1 of successful, 0 otherwise
        """

        success = 0
        try:
            # Send the data
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
        Returns 1 if successful, 0 otherwise
        """

        success = 0
        response = ""

        try:
            num_bytes_in_buffer = self.port.numBytesInBuffer()
            if num_bytes_in_buffer > 0:
                response = self.port.readPort(num_bytes_in_buffer)

        except Exception as e:
            self.log.error(e)

        else:
            success = 1

        finally:
            if success:
                return response
            else:
                return None

    def __send_receive(self, data, read_delay=0.05):
        """
        Generic send/receive function
        Returns the response if successful, empty result otherwise
        """
        # Dynamic delay variable, increases with each failed loop
        delay_counter = 0.001

        # Make sure that the read delay is at least 1ms (i.e. it cannot be 0)
        if read_delay < 0.001:
            read_delay = 0.001

        ret = self.__sendCommand(data)

        if ret:
            # The command was successfuly sent. Now read the response
            time.sleep(0.001)
            ret = self.__getResponse()
            # Read the response as long as we don't get anything back AND
            # we haven't exceeded the max. read delay
            while (((ret is None) or (ret == ""))
                   and (delay_counter < read_delay)):
                time.sleep(delay_counter)
                delay_counter += 0.001
                ret = self.__getResponse()
            # If we get here either we have exceeded the max. read delay, or
            #  we have received a response.
            return ret

        else:
            # There was an issue with sending the command
            return None

    def __isACK(self, message, cmd=None):
        """
        Returns 1 if the message contains an ACK
        """
        if len(message) >= 5:
            # If a command was specified, check that it matches the message
            if cmd is not None:
                if message[1] != cmd:
                    return 0
            # If we get here then we have passed the additional specified
            # checks.
            if message[2] == 0x04:
                # ACK detectec
                return 1
            else:
                # No ACK found
                return 0
        else:
            # Message is not long enough. Indicate an error
            return 0

    def __isNACK(self, message, cmd=None):
        """
        Returns 1 if the message contains a NACK
        """

        if len(message) >= 5:

            # If a command was specified, check that it matches the message
            if cmd is not None:
                if message[1] != cmd:
                    return 0

            # If we get here then we have passed the additional user specified
            # checks.
            if message[2] == 0x05:
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

        if len(message) >= 7:
            nack_val = message[5:7]
            return int.from_bytes(nack_val, byteorder='little')

        else:
            return 0

    def __isResponse(self, message, cmd=None, data_len=None):
        """
        Returns 1 if the message is a valid response
        0 for data_len means that the payload length could be variable
        """
        valid = 0
        length = len(message)
        if length >= 5:
            if message[2] == 0x02:
                calc_len = message[4] + 5
                # If a command was specified we need to check if it matches.
                # If it is incorrect, the response is invalid
                if message[1] == cmd:
                    valid = 1
                # If a data length was specified we need to check if it
                # matches the message's data payload length. If it is incorrect
                # we will return immediately
                if (data_len is not None) and (data_len != 0):
                    if message[4] == data_len:
                        valid = valid * 1

                # If we get here then we have passed the additional
                # specified checks. Finally, check if the overall length
                # matches (integrity check)
                if length == calc_len:
                    # The length is correct
                    valid = valid * 1
                else:
                    # Not a response or incorrect length
                    valid = 0

            elif (message[2] == 0x06) and (length == 261):
                valid = 1

        return valid

    def __getNumPayloadBytes(self, message):
        """
        Returns the number of bytes present in the payload. This takes long #
        responses into account
        """

        if message[2] == 0x02 or message[2] == 0x03:
            return message[4]
        elif message[2] == 0x06:
            return 256
        else:
            return 0

    def __isPushMessage(self, message, cmd=None, data_len=None):
        """
        Returns 1 if the message is a valid push message/response
        """
        length = len(message)
        if length >= 5:
            calc_len = message[4] + 5
            # If a command was specified we need to check if it matches.
            # If it is incorrect we will return immediately
            if cmd is not None:
                if message[1] != cmd:
                    return 0
            # If a data length was specified we need to check if it matches the
            #  message's data payload length. If it is incorrect we will
            # return immediately
            if data_len is not None:
                if message[4] != data_len:
                    return 0
            # If we get here then we have passed the additional user specified
            # checks. Finally, check if the message is a response and if the
            # overall length matches (integrity check)
            if (message[2] == 0x03) and (length == calc_len):
                # This is a response and the length is correct
                return 1
            else:
                # Not a response or incorrect length
                return 0
        else:
            # Message is not long enough. Indicate an error
            return 0

    def __waitForMessage(self, timeout, expected_bytes=5):
        """
        This function simply waits for a message. It is like a read, but waits
        up to the specified timeout for new data to arrive
        Args:
                timeout: specified in seconds. The smallest delay period is 0.01s
        """

        delay_time = 0.01
        # Force the timeout to be at least 10ms
        if timeout < delay_time:
            timeout = delay_time
        num_iter = timeout / delay_time
        response = []
        num_bytes_in_buffer = 0
        while num_iter:
            try:
                num_bytes_in_buffer += self.port.numBytesInBuffer()

                if num_bytes_in_buffer > 0:
                    response.extend(self.port.readPort(num_bytes_in_buffer))
            except Exception as e:
                self.log.error(e)
            else:
                if num_bytes_in_buffer >= expected_bytes:
                    return response
                else:
                    num_iter = num_iter - 1
                    time.sleep(delay_time)
        return None

    def __EvaluateAndReturn(self, response, expected_command,
                            num_expected_payload_bytes):
        """
        This function evaluates the response and prepares the API return value
        If 'num_expected_payload_bytes' is 0, then the response guides how
        many bytes will be returned

        Args:
                response: data in bytes from the probe received from __send_receive
                expected_command:
                num_expected_payload_bytes: Integer number of bytes expecting to receive
        """

        if response is None:
            result = {'status': 0, 'errorCode': None, 'data': None}

        elif (self.__isResponse(response, expected_command,
                                num_expected_payload_bytes)):
            result = {'status': 1, 'errorCode': None,
                      'data': response[-(
                          self.__getNumPayloadBytes(response)):]}

        elif (self.__isPushMessage(response, expected_command,
                                   num_expected_payload_bytes)):
            result = {'status': 1, 'errorCode': None,
                      'data': response[-(
                          self.__getNumPayloadBytes(response)):]}

        elif self.__isACK(response):
            result = {'status': 1, 'errorCode': None, 'data': None}

        elif self.__isNACK(response):
            nack_value = self.__getNACKValue(response)
            result = {'status': 0, 'errorCode': nack_value, 'data': None}

        else:
            result = {'status': 0, 'errorCode': None, 'data': None}
        return result

    # ********************
    # * PUBLIC FUNCTIONS *
    # ********************

    def sendApiPortEnable(self):
        """
        Sends a '*' to enable the API port which tells the probe to interact
        via the radicl API
        """
        self.port.writePort([0x21])

    @property
    def hw_id(self):
        """
        Gets the hardware id
        """
        if self._hw_id is None:
            ret = self.getHWID()
            self._hw_id = ret['data']
        return self._hw_id

    @property
    def hw_id_str(self):
        """
        Gets the hardware id string
        """
        if self._hw_id_str is None:
            if self.hw_id < len(PCA_ID_LIST):
                self._hw_id_str = PCA_ID_LIST[self.hw_id]
        return self._hw_id_str

    @property
    def hw_rev(self):
        """
        Gets the hardware revision
        """
        if self._hw_rev is None:
            ret = self.getHWREV()
            self._hw_rev = ret['data']
        return self._hw_rev

    @property
    def fw_rev(self):
        """
        Gets the hardware id
        """
        if self._fw_rev is None:
            ret = self.getFWREV()
            self._fw_rev = ret['data']
        return self._fw_rev

    @property
    def full_fw_rev(self):
        """
        Gets the hardware id
        """
        if self._full_fw_rev is None:
            ret = self.getFullFWREV()
            self._full_fw_rev = ret['data']
        return self._full_fw_rev

    @property
    def serial(self):
        """
        Gets the serial string
        """
        if self._serial is None:
            self._serial = self.getSerialNumber()
        return self._serial

    def Identify(self):
        """
        Identifies the connected device
        Returns 1 if a valid device was detected
        """
        self.log.debug("Retrieving probe information...")

        if self.hw_id is not None:
            if self.hw_id < len(PCA_ID_LIST):
                id_msg = f"Attached device: {self.hw_id_str}, " \
                         f"Revision={self.hw_rev}, "

                if self.full_fw_rev is not None:
                    id_msg += f"Firmware = {self.full_fw_rev}"
                else:
                    id_msg += f"Firmware = {self.fw_rev}"

                self.log.info(id_msg)
                return 1

            else:
                self.log.warning("Unknown device detected!")
                return 0

        else:
            self.log.warning("Invalid response to ID request")
            return 0

    # ***************************
    # ***** BASIC COMMANDS ******
    # ***************************
    def getSerialNumber(self):
        """
        Queries the board's serial number
        """
        code = AttributeCMD.SERIAL.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 8)

    def getHWID(self):
        """
        Queries the board's HW ID
        """
        code = AttributeCMD.HW_ID.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        ret_val = self.__EvaluateAndReturn(response, code, 1)

        if ret_val['status'] == 1:
            data = int.from_bytes(ret_val['data'], byteorder='little')
            ret_val['data'] = data

        return ret_val

    def getHWREV(self):
        """
        Queries the board's HW revision
        """
        code = AttributeCMD.HW_REV.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        ret_val = self.__EvaluateAndReturn(response, code, 1)
        if ret_val['status'] == 1:
            byte_arr = ret_val['data']
            data = int.from_bytes(ret_val['data'], byteorder='little')
            ret_val['data'] = data

        return ret_val

    def getFWREV(self):
        """
        Queries the board's FW revision in MAJOR.MINOR format
        """
        code = AttributeCMD.FW_REV.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        ret_val = self.__EvaluateAndReturn(response, code, 2)
        if ret_val['status'] == 1:
            major = ret_val['data'][0]  # value[-2]
            minor = ret_val['data'][1]  # value[-1]
            fw_rev = major + minor / 100
            ret_val['data'] = fw_rev
        return ret_val

    def getFullFWREV(self):
        """
        Queries the board's FW revision in the full A.B.C.D format
        """
        code = AttributeCMD.FULL_FW_REV.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        ret_val = self.__EvaluateAndReturn(response, code, 4)
        if ret_val['status'] == 1:
            value = ret_val['data']
            rev_string = str(value[0]) + "." + str(value[1]) + \
                         "." + str(value[2]) + "." + str(value[3])
            ret_val['data'] = rev_string
        return ret_val

    def startBootloader(self):
        """
        Starts the bootloader
        """
        code = SystemCMD.START_BOOTLOADER.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def getSystemStatus(self):
        """
        Queries the system status
        """
        code = SettingsCMD.STATUS.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def getRunState(self):
        code = SystemCMD.STATE.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    # ***************************************
    # ***** SENSOR/MEASUREMENT COMMANDS *****
    # ***************************************

    def getMeasState(self):
        """
        Queries the state of the measurement state machine
        """
        code = MeasCMD.STATE.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasReset(self):
        """
        Resets the measurement state machine
        Returns 1 if successful
        """
        code = MeasCMD.RESET.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasStart(self):
        """
        Starts a measurement
        Returns 1 if successful
        """
        code = MeasCMD.START.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasStop(self):
        """
        Stops a measurement
        Returns 1 if successful
        """
        code = MeasCMD.STOP.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetNumSegments(self, buffer_id):
        """
        Queries the number of data segments for a particular data buffer
        """
        code = MeasCMD.NUM_SEGMENTS.cmd
        message = [0x9F, code, 0x00, 0x00, 0x01]
        message.extend(buffer_id.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasReadDataSegment(self, buffer_id, numPacket):
        """
        Reads a specific data segment of a specific data buffer
        """
        code = MeasCMD.DATA_SEGMENT.cmd
        message = [0x9F, code, 0x00, 0x00, 0x05]
        message.extend(buffer_id.to_bytes(1, byteorder='little'))
        message.extend(numPacket.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)

        # Check if only the command matches. The length may be variable
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetSamplingRate(self):
        """
        Reads/Returns the IR sampling rate
        """
        code = SettingsCMD.SAMPLING_RATE.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetSamplingRate(self, sampling_rate):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Sets the sensor sampling rate
        """
        code = SettingsCMD.SAMPLING_RATE.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(sampling_rate.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetZPFO(self):
        """
        Reads/returns the Zero Phase Filter Order used on the depth data.
        """
        code = SettingsCMD.ZPFO.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetZPFO(self, zpfo):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Set the Zero Phase Filter Order used on the depth data.
        """
        code = SettingsCMD.ZPFO.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(zpfo.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetPPMM(self):
        """
        Reads/returns the Points per millimeter parameter
        """
        code = SettingsCMD.PPMM.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetPPMM(self, ppmm):
        """
        helpme - Sets the Points per millimeter parameter
        """
        code = SettingsCMD.PPMM.cmd
        message = [0x9F, code, 0x01, 0x00, 0x01]
        message.extend(ppmm.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetALG(self):
        """
        Reads/Returns the algorithm (1 - depth corrected, 2 for timeseries only)
        parameter
        """
        code = SettingsCMD.ALG.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetALG(self, alg):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Sets the algorithm (1 - depth corrected, 2 for timeseries only)
        """
        code = SettingsCMD.ALG.cmd
        message = [0x9F, code, 0x01, 0x00, 0x01]
        message.extend(alg.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetAPPP(self):
        """
        Reads the APPP parameter
        """
        code = SettingsCMD.APPP.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetAPPP(self, appp):
        """
        Returns status=1 if successful, status=0 otherwise
        helpme - Sets the APPP parameter which smooths the timeseries data
        """
        code = SettingsCMD.APPP.cmd
        message = [0x9F, code, 0x01, 0x00, 0x01]
        message.extend(appp.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetTCM(self):
        """
        Reads the TCM parameter
        """
        code = SettingsCMD.TCM.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetTCM(self, tcm):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Sets the Temperature correction method for the barometer data

        """
        code = SettingsCMD.TCM.cmd

        message = [0x9F, code, 0x01, 0x00, 0x01]
        message.extend(tcm.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetUserTemp(self):
        """
        Reads the user set temperature
        """
        code = SettingsCMD.USERTEMP.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetUserTemp(self, user_temp):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Set the user specified temperature for TCM=3
        """
        code = SettingsCMD.USERTEMP.cmd

        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(user_temp.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetIR(self):
        """
        Reads the IR parameter

        """
        code = SettingsCMD.IR.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetIR(self, ir):
        """
        Returns status=1 if successful, status=0 otherwise

        helpme - Turns on the IR emitter
        """
        code = SettingsCMD.IR.cmd
        message = [0x9F, code, 0x01, 0x00, 0x01]
        message.extend(ir.to_bytes(1, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetCalibData(self, num_sensor):
        """
        Reads a sensor's calibration value
        """
        code = SettingsCMD.CALIBDATA.cmd
        message = [0x9F, code, 0x00, 0x00, 0x01]
        message.extend(num_sensor.to_bytes(1, byteorder='little'))

        response = self.__send_receive(message)

        # Expect 4 bytes back two for the low value and 2 for the high value
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetCalibData(self, num_sensor, calibration_value_low,
                         calibration_value_high):
        """
        Sets the probes calibration values. A high and low are set where the
        low. This is applied linearly and thus the low value should be the
        y intercept. This will remap the raw's low value-high value to 0-4095

        The probe expects this number joined in bytes so we have to create a
        2, 2 byte integers and add them together to create a 4 byte message.

        Args:
                num_sensor: Integer indicating sensors 1,2,3, or 4.
                calibration_value_low: 12-bit integer indicating the y intercept of a linear
                                   calibration
                calibration_value_high: 12-bit integer for the

        Returns:
                status: 1 if successful, 0 otherwise

        helpme - Sets the calibration data for the specified sensor
        """
        code = SettingsCMD.CALIBDATA.cmd
        message = [0x9F, code, 0x01, 0x00, 0x05]

        # Convert values each into a 1 and 2 bytes
        message.extend(num_sensor.to_bytes(1, byteorder='little'))
        message.extend(calibration_value_low.to_bytes(2, byteorder='little'))
        message.extend(calibration_value_high.to_bytes(2, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetMeasTemp(self):
        """
        Reads the current temperature reading (from last measurement)
        Returns status=1 if successful, status=0 otherwise
        """
        code = MeasCMD.TEMP.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetAccThreshold(self):
        """
        Reads the accelerometer threshold setting (an unsigned 32-bit integer in mG)
        Returns status=1 if successful, status=0 otherwise
        """
        code = SettingsCMD.ACCTHRESH.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetAccThreshold(self, threshold):
        """
        Sets the accelerometer threshold setting (accelerometer thresholding algorithm)
        The parameter 'threshold' is an unsigned 32-bit (4-bytes) absolute value indicating the
        threshold in mG A value of 0 turns the accelerometer thresholding algorithm off
        Returns status=1 if successful, status=0 otherwise
        """
        code = SettingsCMD.ACCTHRESH.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(threshold.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetAccZPFO(self):
        """
        Reads the accelerometer zero-phase filter order setting (post-processing filter
        for accelerometer thresholding algorithm) Returns status=1 if successful,
        status=0 otherwise
        """
        code = SettingsCMD.ACCZPFO.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 4)

    def MeasSetAccZPFO(self, zpfo):
        """
        Sets the accelerometer zero-phase filter order setting (post-processing filter
        for accelerometer thresholding algorithm) The parameter 'zpfo' is an
        unsigned 32-bit (4-bytes) value indicaing the filter order A value of 0
        turns the filtering off (filter is bypassed) Returns status=1 if successful,
        status=0 otherwise
        """
        code = SettingsCMD.ACCZPFO.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(zpfo.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def MeasGetAccRange(self):
        """
        gets the accelerometer range
        """
        code = SettingsCMD.ACCRANGE.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def MeasSetAccRange(self, abs_range_gs):
        """
        Sets the accelerometer range

        Args:
            abs_range_gs: integer value for range e.g. 2 == +/-2g's

        Returns:
        """
        code = SettingsCMD.ACCRANGE.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(abs_range_gs.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    # ******************************
    # ***** FW UPDATE COMMANDS *****
    # ******************************

    def UpdateEnter(self):
        """
        Enters the FW Update FSM
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.ENTER.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)

    def UpdateGetState(self):
        """
        Gets the FW update FSM state
        """
        code = FWUpdateCMD.STATE.cmd
        response = self.__send_receive([0x9F, code, 0x00, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 1)

    def UpdateWaitForStateChange(self, wait_time):
        """
        Waits for the state change message
        """
        code = FWUpdateCMD.STATE.cmd
        response = self.__waitForMessage(wait_time, 6)
        return self.__EvaluateAndReturn(response, code, 1)

    def UpdateSetSize(self, num_packets, packet_size):
        """
        Sets the update size
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.SIZE.cmd
        message = [0x9F, code, 0x01, 0x00, 0x06]
        message.extend(num_packets.to_bytes(4, byteorder='little'))
        message.extend(packet_size.to_bytes(2, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def UpdateDownload_Short(self, data, crc8, packet_id):
        """
        Downloads a 16-byte chunk of data
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.DOWNLOAD.cmd
        message = [0x9F, code, 0x01, 0x00, 0x00]
        message[3] = crc8
        message[4] = len(data)
        message.extend(data)
        self.__sendCommand(message)
        response = self.__waitForMessage(20)
        return self.__EvaluateAndReturn(response, code, 0)

    def UpdateDownload_Long(self, data, crc8, packet_id):
        """
        Downloads a 256-byte chunck of data
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.DOWNLOAD.cmd
        message = [0x9F, code, 0x07, 0x00, 0x00]
        message[3] = crc8
        message[4] = 0
        message.extend(data)
        self.__sendCommand(message)
        response = self.__waitForMessage(20)
        return self.__EvaluateAndReturn(response, code, 0)

    def UpdateSetCRC(self, crc32):
        """
        Sets the CRC32 of the FW image
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.CRC.cmd
        message = [0x9F, code, 0x01, 0x00, 0x04]
        message.extend(crc32.to_bytes(4, byteorder='little'))
        response = self.__send_receive(message)
        return self.__EvaluateAndReturn(response, code, 0)

    def UpdateClose(self):
        """
        Closes the FW update FSM
        Returns status=1 if successful, status=0 otherwise
        """
        code = FWUpdateCMD.CLOSE.cmd
        response = self.__send_receive([0x9F, code, 0x01, 0x00, 0x00])
        return self.__EvaluateAndReturn(response, code, 0)
