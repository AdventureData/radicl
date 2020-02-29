# coding: utf-8

import binascii
import datetime
import inspect
import os
import struct
import sys
import time

import numpy as np
import serial

from radicl import __version__
from radicl import serial as rs
from radicl.api import RAD_API
from radicl.ui_tools import (
    Messages, get_logger, parse_func_list, parse_help, print_helpme)

error_codes = {2049: "The probe measurement/sensor is not running"}


class RAD_Probe():
    """
    Class for directly interacting with the probe.

    """

    def __init__(self, ext_api=None, debug=False):
        """
        Args:
            ext_api: rad_api.RAD_API object preinstantiated
        """

        self.log = get_logger(__name__, level='debug')

        # Check if an external API object was passed in.
        if (ext_api is not None):
            # An external API object was provided. Use it. Note: We assume here
            # that the appropriate initialization, identification, and API port
            # enable procedure has already taken place
            self.api = ext_api
        else:
            # No external API oject was provided. Create new serial and API
            # objects for internal use
            port = rs.RAD_Serial()
            port.openPort()

            if not port:
                self.log.info("No device present")
            else:
                port.flushPort()
                # Create the API and FMTR instances The API class is linked to
                # the port object
                api = RAD_API(port)

                # Switch the device over to API mode
                api.sendApiPortEnable()
                self.api = api

                # Delay a bit and then identify the attached device
                time.sleep(0.5)
                ret = api.Identify()

                if ret == 0:
                    self.log.error("Unable to connect to the probe. Unplug and"
                                   " power cycle it.")
                    sys.exit()
                time.sleep(0.5)

                # Manages the settings
                settings_funcs = inspect.getmembers(self.api,
                                                    predicate=inspect.ismethod)
                ignores = ['reset']
                self.settings = parse_func_list(settings_funcs,
                                                ['Meas', 'Set'],
                                                ignore_keywords=ignores)
                self.getters = parse_func_list(settings_funcs,
                                               ['Meas', 'Get'],
                                               ignore_keywords=ignores)

    def manage_error(self, ret_dict, stack_id=1):
        """
        Handles the common scenario of looking at the returned Dictionary
        from the probe where there may be an error or simply a com error.
        This function reports the name of the function and reports the error
        function.

        Args:
            ret_dict: Dictionary of keys ['status','data','errorCode']
            stack_id: number of functions up the stack to use for reporting
                      function name when errors occur.
        """
        name = inspect.stack()[stack_id][3]

        if (ret_dict['errorCode'] is not None):
            self.log.error("{} error:{}".format(name, ret_dict['errorCode']))

        else:
            self.log.error("{} error: COM".format(name))

    def manage_data_return(self, ret, num_values=1, dtype=int):
        """
        Manage a return from the probe when were expecting an integer

        Args:
            ret: Dictionary of the return with keys status, errorCode, and data
            num_values: Number of expect values to be returned
            dtype: Data type expected back

        Returns:
            result: None when no data was received. Integer when its not.
        """
        result = []

        if ((ret['status'] == 1) and (ret['data'] is not None)):

            data_size = len(ret['data'])
            increment = int(data_size / num_values)

            if data_size % num_values != 0:
                raise IOError("Data received (length = {}) is not evenly "
                              "divided by the expected number of values = "
                              "{}".format(data_size, num_values))

            for i in range(0, data_size, increment):
                data = ret['data'][i:i + increment]
                if dtype == int:
                    value = int.from_bytes(data, byteorder='little')

                elif dtype == str:
                    value = data.decode('utf-8')

                else:
                    raise ValueError(
                        "No types other than str and int are implemented")

                result.append(value)

            if num_values == 1:
                result = result[0]

        else:
            self.manage_error(ret, stack_id=2)
            result = None

        return result

    # Generic read function

    def __readData(self, buffer_ID):
        """
        Prive function to retrieve data from the probe.
         Args:
            buffer_ID:
        """
        num_segments = 0
        data = []
        ret1 = self.api.MeasGetNumSegments(buffer_ID)
        # Returns a positive status
        if (ret1['status'] == 1):
            num_segments = int.from_bytes(ret1['data'], byteorder='little')

            if (num_segments != 0 and num_segments is not None):
                self.log.debug("Reading %d segments" % num_segments)
                byte_counter = 0

                for ii in range(1, (num_segments + 1)):
                    ret2 = self.api.MeasReadDataSegment(buffer_ID, (ii - 1))

                    if (ret2['status'] == 1):
                        # Data segment read successfull

                        if (ret2['data'] is not None):
                            byte_counter = byte_counter + len(ret2['data'])
                            data_chunk = ret2['data']
                            data.extend(data_chunk)

                    # Data segment read failed. Retry
                    else:
                        wait_time = 0.005

                        for jj in range(0, 10):
                            time.sleep(wait_time)
                            wait_time = wait_time * 2
                            ret3 = self.api.MeasReadDataSegment(buffer_ID, ii)

                            if (ret3['status'] ==
                                    1 and ret2['data'] is not None):
                                byte_counter = byte_counter + len(ret3['data'])

                                data_chunk = ret3['data']
                                data.extend(data_chunk)
                                break

                            elif (ret3['errorCode'] is not None):
                                self.log.error("readSegmentData error: %d (Retry %d, "
                                               "Segment=%d, buffer_ID=%d)" %
                                               (ret3['errorCode'], jj, ii, buffer_ID))

                            else:
                                self.log.error("readSegmentData error: COM "
                                               "(Retry %d, Segment=%d, "
                                               "buffer_ID=%d)" %
                                               (jj, ii, buffer_ID))

                        # Retry failed! Return here
                        if ((ret3['status'] != 1) or (ret3['data'] is None)):
                            return {'status': 0,
                                    'SegmentsAvailable': num_segments,
                                    'SegmentsRead': ii,
                                    'BytesRead': byte_counter,
                                    'Data': None}
                # -- END OF FOR LOOP --
                # Read process has successfully completed
                return {'status': 1, 'SegmentsAvailable': num_segments,
                                     'SegmentsRead': ii,
                                     'BytesRead': byte_counter,
                                     'Data': data}
            else:
                self.log.error("Data read error: No data segments available")

        # No error code provided
        elif (ret1['errorCode'] is not None):
            self.log.error("getNumSegments error: %d (buffer_ID = %d)" %
                           (ret1['errorCode'], buffer_ID))
        else:
            self.log.error("getNumSegments error: COM")
        return {'status': 0, 'SegmentsAvailable': 0, 'SegmentsRead': 0,
                                                     'BytesRead': 0,
                                                     'Data': None}

    # ********************
    # * PUBLIC FUNCTIONS *
    # ********************
    def getProbeSerial(self):
        """
        Returns the probe's serial number. The return value is a string. If the
        request fails it will return None
        """

        ret = self.api.getSerialNumber()
        return self.manage_data_return(ret, dtype=str)

    def getProbeSystemStatus(self):
        """
        Returns the probe's system status. The return value is an integer.
        If the request fails it will return None
        """

        ret = self.api.getSystemStatus()

        return self.manage_data_return(ret, dtype=int)

    def getProbeRunState(self):
        """
        Returns the probe's run state. The return value is an integer.
        If the request fails it will return None
        """

        ret = self.api.getRunState()
        return self.manage_data_return(ret, dtype=int)

    def getProbeMeasState(self):
        """
        Retrieves the probe measurement state and converts it to an integer

        Returns:
            integer-measurement state of the probe, or none if error arises.
        """
        data = None
        attempts = 0

        while data is None and attempts < 10:
            ret = self.api.getMeasState()
            data = self.manage_data_return(ret, dtype=int)
            attempts += 1

        return data

    def startMeasurement(self):
        """
        Starts a new measurement. Returns 1 if successfull, 0 otherwsie
        """

        ret = self.api.MeasStart()
        self.log.debug("Start Measurement Reqested.")

        if (ret['status'] == 1):
            self.wait_for_state(1)
            self.log.info("Measurement Started...")

            return 1

        else:
            self.manage_error(ret)

            return 0

    def stopMeasurement(self):
        """
        Stops an ongoing measurement. Returns 1 if successfull, 0 otherwise
        """

        ret = self.api.MeasStop()
        self.log.debug("Stop Measurement Reqested.")

        if (ret['status'] == 1):
            self.wait_for_state(3)
            self.log.info("Measurement stopped...")

            return 1
        else:
            self.manage_error(ret)

            return 0

    def resetMeasurement(self):
        """
        Resets the measurement FSM to prepare for a new measurement.
        Returns 1 if successfull, 0 otherwise
        """

        ret = self.api.MeasReset()
        self.log.debug("Measurement reset requested...")

        if (ret['status'] == 1):
            self.wait_for_state(0, delay=0.3)
            self.log.info("Probe measurement reset...")

            return 1

        else:
            self.manage_error(ret)

            return 0

    def wait_for_state(self, state, retry=500, delay=0.2):
        """
        Waits for the specifed state to occur. This is particularly useful when
        a command is requested.

        Args:
            state: single integer
            retry: Number of attempts to try while Waiting for the states
            delay: time in seconds to wait between each attempt

        """

        attempts = 0
        pstate = self.getProbeMeasState()
        result = False
        self.log.info(
            "Waiting for state {0}, current state = {1}".format(
                state, pstate))

        while not result:
            result = pstate == state

            # Check for a probe advanced past the state
            if isinstance(pstate, int):
                if state != 0:
                    if pstate >= state:
                        result = True
                if state == 5:
                    if pstate == 0:
                        result = True

            if attempts > retry:
                self.log.error(
                    "Retry Exceeded waiting for state(s) {0}".format(state))
                result = False
                break
            else:
                attempts += 1

            time.sleep(delay)
            pstate = self.getProbeMeasState()

        if result:
            self.log.debug(
                "{} queries while waiting for state {}".format(
                    attempts, state))

        return result

    def readRawSensorData(self):
        """
        Reads the RAW sensor data.
        helpme - Raw NIR data for 4 sensors

        Returns:
            dict - containing data or None if read failed
        """
        ret = self.__readData(0)

        # Sucessfully read data
        if (ret['status'] == 1):
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readRawSensorData error: Data integrity error (not all "
                               "segments read)")
                return None
            expected_bytes = ret['SegmentsRead'] * 256
            if (expected_bytes != ret['BytesRead']):
                # Data integrity error (not all bytes read - incomplete segment)
                # For the raw sensor data, this is also the check to ensure we
                # have an even amount of bytes to break into sensor pairs
                self.log.error("readRawSensorData error: Data integrity error (not all "
                               "bytes read - incomplete segment)")
                self.log.error(
                    "Expected=%d, Read=%d" %
                    (expected_bytes, ret['BytesRead']))
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            sensor1 = []
            sensor2 = []
            sensor3 = []
            sensor4 = []
            total_runs = expected_bytes // 8
            offset = 0

            for ii in range(0, total_runs):
                sensor1.append(data[offset] + data[(offset + 1)] * 256)
                sensor2.append(data[(offset + 2)] + data[(offset + 3)] * 256)
                sensor3.append(data[(offset + 4)] + data[(offset + 5)] * 256)
                sensor4.append(data[(offset + 6)] + data[(offset + 7)] * 256)
                offset = offset + 8
            return {'Sensor1': sensor1, 'Sensor2': sensor2, 'Sensor3': sensor3,
                    'Sensor4': sensor4}

        # Read failed!
        else:
            return None

    def readCalibratedSensorData(self):
        """
        Reads the Read Calibrated sensor data.
        helpme - Calibrated data for 4 sensors

        Returns:
            dict - containing data or None if read failed
        """
        calib_data = {}
        raw = self.readRawSensorData()

        for id in range(1, 5):
            sensor = "Sensor{}".format(id)
            d = self.getSetting(setting_name='calibdata', sensor=id)

            # For the calibration for sensor 1 we invert
            if id == 1:
                # Set the slope to the negative difference
                m = 4095 / (d[0] - d[1])
                # Set the intercept to the LOW value
                b = d[1]

            else:
                # Set the slope to the positive difference
                m = 4095 / (d[1] - d[0])
                # Set the intercept to the LOW value
                b = d[0]

            calib_data[sensor] = [m * (x - b) for x in raw[sensor]]

        return calib_data

    def readRawAccelerationData(self):
        """
        Reads the raw 3 axis  acceleration data
        helpme - Raw 3 axis accelerometer data from the probe

        Returns:
            dict: containing accel data (x,y,z) or None if read failed


        """
        ret = self.__readData(1)

        # Sucessfully read data
        if (ret['status'] == 1):
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readRawAccelerationData error: Data integrity error (not"
                               " all segments read)")
                return None

            total_bytes = ret['BytesRead']

            # Data integrity error (not all bytes read - incomplete data
            # segment)
            if ((total_bytes % 6) != 0):
                # The data set is not an integer multiple of 6 (2 bytes per
                # axis, 3 axes total)
                self.log.error("readRawAccelerationData error: Data integrity error "
                               "(incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            x_axis = []
            y_axis = []
            z_axis = []
            total_runs = total_bytes // 6
            offset = 0

            for ii in range(0, total_runs):
                acc_data_x = struct.unpack('<h', bytes(
                    data[(offset + 0): (offset + 2)]))
                acc_data_y = struct.unpack('<h', bytes(
                    data[(offset + 2): (offset + 4)]))
                acc_data_z = struct.unpack('<h', bytes(
                    data[(offset + 4): (offset + 6)]))
                x_axis.append(acc_data_x[0] / 1000)
                y_axis.append(acc_data_y[0] / 1000)
                z_axis.append(acc_data_z[0] / 1000)
                offset = offset + 6
            return {'X-Axis': x_axis, 'Y-Axis': y_axis, 'Z-Axis': z_axis}
        # Read failed!
        else:
            return None

    def readAccelerationCorrelationData(self):
        """
        Reads the acceleration correllation data
        """

        ret = self.__readData(5)
        if (ret['status'] == 1):
            # Sucessfully read data
            # ***** DATA INTEGRITY CHECK *****
            # Data integrity error (not all segments read)
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                               "error (not all segments read)")
                return None
            total_bytes = ret['BytesRead']
            if ((total_bytes % 4) != 0):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation
                # number is a 32-bit int => 4 bytes)
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                               "error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            correll_data = []
            total_runs = total_bytes // 4
            offset = 0

            for ii in range(0, total_runs):
                correll_data.append(data[(offset + 0)] + (data[(offset + 1)] * 256) + (
                    data[(offset + 2)] * 65536) + (data[(offset + 3)] * 16777216))
                offset = offset + 4
            return correll_data
        else:
            # Read failed!
            return None

    def readRawPressureData(self):
        """
        Reads the RAW pressure data, including the correlation index
        """

        ret = self.__readData(2)

        # Sucessfully read data
        if (ret['status'] == 1):
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readRawPressureData error: Data integrity error (not "
                               "all segments read)")
                return None

            # Data integrity error (not all bytes read - incomplete data
            # segment)
            total_bytes = ret['BytesRead']
            if ((total_bytes % 3) != 0):
                # The data set is not an integer multiple of 3 (Raw pressure is
                # in 24-bit format => 3 bytes)
                self.log.error(
                    "readRawPressureData error: Data integrity error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            pressure_data = []
            total_runs = total_bytes // 3
            offset = 0

            for ii in range(0, total_runs):
                this_value = data[(offset + 0)] + (data[(offset + 1)] * 256) + \
                    (data[(offset + 2)] * 65536)

                pressure_data.append(this_value / 4096)
                offset = offset + 3
            return pressure_data

        # Read failed!
        else:
            return None

    def readRawDepthData(self):
        """
        Reads the converted depth data, including the correlation index
        Return type is a dict containing data or None if read failed
        helpme - Unfiltered elevation data from the depth sensor
        """
        ret = self.__readData(3)
        if (ret['status'] == 1):
            # Sucessfully read data
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readDepthData error: Data integrity error (not all "
                               "segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ((total_bytes % 4) != 0):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Floatingpoint
                # values are 32-bit long => 4 bytes)
                self.log.error("readDepthData error: Data integrity error "
                               "(incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            depth_data = []
            total_runs = total_bytes // 4
            offset = 0
            for ii in range(0, total_runs):
                this_byte_list = data[(offset + 0):(offset + 4)]
                this_byte_object = bytes(this_byte_list)
                this_value = struct.unpack('f', this_byte_object)
                depth_data.append(this_value)
                offset = offset + 4
            return depth_data
        else:
            # Read failed!
            return None

    def readFilteredDepthData(self):
        """
        Retrieves the filtered depth data according to the zero-phase low-pass
        filter (equivalent to Matlab's 'filtfilt'). The amount of filtering
        applied is set by :func:`~radicl.RAD_API.MeasSetZPFO`

        helpme - The probe's filtered depth data is the raw depth data made
                 relative to the change and the amount filtered set by the ZPFO
                 option.

        """

        ret = self.__readData(4)
        if (ret['status'] == 1):
            # Sucessfully read data
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readFilteredDepthData error: Data integrity error "
                               "(not all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ((total_bytes % 4) != 0):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Floatingpoint
                # values are 32-bit long => 4 bytes)
                self.log.error("readFilteredDepthData error: Data integrity error "
                               "(incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            depth_data = []
            total_runs = total_bytes // 4
            offset = 0

            for ii in range(0, total_runs):
                this_byte_list = data[(offset + 0):(offset + 4)]
                this_byte_object = bytes(this_byte_list)
                this_value = struct.unpack('f', this_byte_object)
                depth_data.append(this_value)
                offset = offset + 4

            if depth_data is not None:
                # Convert to cm
                depth_data = [(c[0] / 100,) for c in depth_data]

            return depth_data

        else:
            # Read failed!
            return None

    def readPressureDepthCorrelationData(self):
        """
        Reads the pressure/depth correllation data
        """

        ret = self.__readData(6)
        if (ret['status'] == 1):
            # Sucessfully read data
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                               "error (not all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ((total_bytes % 4) != 0):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation
                # number is a 32-bit int => 4 bytes)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                               "error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            correll_data = []
            total_runs = total_bytes // 4
            offset = 0

            for ii in range(0, total_runs):
                correll_data.append(data[(offset + 0)] + (data[(offset + 1)] *
                                                          256) + (data[(offset + 2)] * 65536) +
                                    (data[(offset + 3)] * 16777216))
                offset = offset + 4
            return correll_data

        else:
            # Read failed!
            return None

    def readSensorDepthComboData(self):
        """
        Reads the processed data as a sensor-depth combo
        """

        ret = self.__readData(7)
        if (ret['status'] == 1):
            # Sucessfully read data
            # ***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readSensorDepthCombo error: Data integrity error (not "
                               "all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ((total_bytes % 16) != 0):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation
                # number is a 32-bit int => 4 bytes)
                self.log.error("readSensorDepthCombo error: Data integrity"
                               " error (incomplete data set)")
                return None

            self.log.info("Total Datapoints = %d" % ret['SegmentsRead'])
            # ***** DATA PARSING *****
            data = ret['Data']
            total_runs = total_bytes // 16
            offset = 0
            transaction_id = []
            sensor1 = []
            sensor2 = []
            sensor3 = []
            sensor4 = []
            depth = []

            for ii in range(0, total_runs):
                this_data_set = data[offset: (offset + 16)]
                transaction_id.append(this_data_set[0] + (this_data_set[1] *
                                                          256) + (this_data_set[2] * 65536) +
                                      (this_data_set[3] * 16777216))
                depth.append(this_data_set[4] + (this_data_set[5] * 256) +
                             (this_data_set[6] * 65536) + (this_data_set[7] *
                                                           16777216))
                sensor1.append(this_data_set[8] + (this_data_set[9] * 256))
                sensor2.append(this_data_set[10] + (this_data_set[11] * 256))
                sensor3.append(this_data_set[12] + (this_data_set[13] * 256))
                sensor4.append(this_data_set[14] + (this_data_set[15] * 256))
                offset = offset + 16
            return {'Sensor1': sensor1,
                    'Sensor2': sensor2,
                    'Sensor3': sensor3,
                    'Sensor4': sensor4,
                    'Depth': depth}
        else:
            # Read failed!
            return None

    def readMeasurementTemperature(self):
        """
        Reads the temperature from the last measurement
        """

        ret = self.api.MeasGetMeasTemp()
        if (ret['status'] == 1):
            data = ret['data']
            this_byte_object = bytes(data)
            this_value = struct.unpack('i', this_byte_object)
            return this_value

        else:
            self.manage_error(ret)

        return None

    def getZPFO(self):
        """
        Reads the probes zero phase shift applied to the depth data

        """

        ret = self.api.MeasGetZPFO()
        return self.manage_data_return(ret, dtype=int)

    def getProbeHeader(self):
        """
        Returns the lines that should be in every data file produced.
        """
        t = datetime.datetime.now()
        fstr = "{0}-{1:02d}-{2:02d}--{3:02d}:{4:02d}:{5:02d}"
        time_stamp = fstr.format(t.year, t.month, t.day,
                                 t.hour, t.minute, t.second)

        header = "RECORDED={0}\n"
        header += "radicl VERSION={1}\n"
        header += "FIRMWARE REVISION={2}\n"
        header += "HARDWARE REVISION={3}\n"
        header += "MODEL NUMBER={4}\n"
        #header += "SERIAL NUMBER={5}\n"

        final = header.format(time_stamp,
                              __version__,
                              self.api.fw_rev,
                              self.api.hw_rev,
                              self.api.hw_id,
                              )
        return final

    def getSetting(self, **kwargs):
        """
        Reads the probes setting from the dictionary of functions. Calls the
        function and manages the data.

        Args:
            setting_name: name of the function minus Meas and get
            sensor: Sensor ID for calibration data

        Returns:
            int: from the function getting the probe setting, or list of 2 for calibration data
        """
        setting_name = kwargs['setting_name']
        if setting_name == 'calibdata':
            ret = self.getters[setting_name](kwargs['sensor'])
            num_values = 2
        else:
            ret = self.getters[setting_name]()
            num_values = 1

        return self.manage_data_return(ret, num_values=num_values, dtype=int)

    def setSetting(self, **kwargs):
        """
        sets the probe's setting
        """
        setting_name = kwargs['setting_name']

        if setting_name == 'calibdata':
            ret = self.settings[setting_name](kwargs['sensor'],
                                              kwargs['low_value'],
                                              kwargs['hi_value'])

        else:
            ret = self.settings[setting_name](kwargs['value'])

        if (ret['status'] == 1):
            return True

        else:
            self.manage_error(ret)

        return None
