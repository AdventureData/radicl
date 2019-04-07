# coding: utf-8

import sys
import binascii
import serial
import time
import inspect
from radicl.api import RAD_API
from radicl import serial as rs
from radicl.ui_tools import get_logger
from radicl import __version__
from radicl.ui_tools import Messages, parse_func_list, print_helpme, parse_help

import struct
import datetime


class RAD_Probe():
    """
    Class for directly interacting with the probe.
    """
    def __init__(self, ext_api=None):
        """
        Args:
            ext_api: rad_api.RAD_API object preinstantiated
        """

        self.log = get_logger(__name__, level='DEBUG')

        # Check if an external API object was passed in.
        if (ext_api != None):
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

                #Switch the device over to API mode
                api.sendApiPortEnable()
                self.api = api

                #Delay a bit and then identify the attached device
                time.sleep(0.5)
                ret = api.Identify()
                time.sleep(0.5)

                # Manages the settings
                settings_funcs = inspect.getmembers(self.api,
                                                    predicate=inspect.ismethod)
                self.settings = parse_func_list(settings_funcs,['Meas','Set'])
                self.getters = parse_func_list(settings_funcs,['Meas','Get'])

    #Generic read function
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
            num_segments = int.from_bytes(ret1['data'],byteorder='little')

            if (num_segments != 0 and num_segments != None):
                self.log.debug("Reading %d segments" % num_segments)
                byte_counter = 0

                for ii in range(1, (num_segments+1)):
                    ret2 = self.api.MeasReadDataSegment(buffer_ID, (ii-1))

                    if (ret2['status'] == 1):
                        # Data segment read successfull

                        if (ret2['data'] != None):
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

                            if (ret3['status'] == 1):
                                byte_counter = byte_counter + len(ret3['data'])

                                data_chunk = ret3['data']
                                data.extend(data_chunk)
                                break

                            elif (ret3['errorCode'] != None):
                                self.log.error("readSegmentData error: %d (Retry %d, "
                                      "Segment=%d, buffer_ID=%d)" % \
                                      (ret3['errorCode'], jj, ii, buffer_ID))

                            else:
                                self.log.error("readSegmentData error: COM "
                                                "(Retry %d, Segment=%d, "
                                                "buffer_ID=%d)" % \
                                                (jj, ii, buffer_ID))

                        # Retry failed! Return here
                        if ((ret3['status'] != 1) or (ret3['data'] == None) ):
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
        elif (ret1['errorCode'] != None):
            self.log.error("getNumSegments error: %d (buffer_ID = %d)" % \
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

        if ( (ret['status'] == 1) and (ret['data'] != None) ):
            return ret['data'].decode("utf-8")
        else:

            if (ret['errorCode'] != None):
                self.log.error("getProbeSerial error: %d" % ret['errorCode'])

            else:
                self.log.error("getProbeSerial error: COM")

            return None

    def getProbeSystemStatus(self):
        """
        Returns the probe's system status. The return value is an integer.
        If the request fails it will return None
        """

        ret = self.api.getSystemStatus()

        if ( (ret['status'] == 1) and (ret['data'] != None) ):
            return int.from_bytes(ret['data'], byteorder='little')

        else:

            if (ret['errorCode'] != None):
                self.log.error("getProbeSystemStatus error: %d" % \
                                                              ret['errorCode'])

            else:
                self.log.error("getProbeSystemStatus error: COM")

            return None

    def getProbeRunState(self):
        """
        Returns the probe's run state. The return value is an integer.
        If the request fails it will return None
        """

        ret = self.api.getRunState()

        if ((ret['status'] == 1) and (ret['data'] != None)):
            return int.from_bytes(ret['data'], byteorder='little')

        else:

            if (ret['errorCode'] != None):
                self.log.error("getProbeRunState error: %d" % ret['errorCode'])

            else:
                self.log.error("getProbeRunState error: COM")

            return None

    def getProbeMeasState(self):
        """
        Retrieves the probe measurement state and converts it to an integer

        Returns:
            integer-measurement state of the probe, or none if error arises.
        """
        ret = self.api.getMeasState()
        if ( (ret['status'] == 1) and (ret['data'] != None) ):
            return int.from_bytes(ret['data'],byteorder ='little')
        else:
            if (ret['errorCode'] != None):
                self.log.error("getState error: %d" % ret['errorCode'])
            else:
                self.log.error("getState error: COM")
            return None

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
            if (ret['errorCode'] != None):
                self.log.error("measStart error: %d" % ret['errorCode'])

            else:
                self.log.error("measStart error: COM")

            return 0

    def stopMeasurement(self):
        """
        Stops an ongoing measurement. Returns 1 if successfull, 0 otherwise
        """

        ret = self.api.MeasStop()
        self.log.debug("Stop Measurement Reqested.")

        if (ret['status'] == 1):
            self.log.info("Measurement stopped...")

            return 1
        else:
            if (ret['errorCode'] != None):
                self.log.error("measStop error: %d" % ret['errorCode'])
            else:
                self.log.error("measStop error: COM")
            return 0

    def resetMeasurement(self):
        """
        Resets the measurement FSM to prepare for a new measurement.
        Returns 1 if successfull, 0 otherwise
        """

        ret = self.api.MeasReset()

        if (ret['status'] == 1):
            self.wait_for_state(5)

            return 1
        else:
            if (ret['errorCode'] != None):
                self.log.error("measStop error: %d" % ret['errorCode'])

            else:
                self.log.error("measStop error: COM")

            return 0

    def wait_for_state(self, state, retry = 10):
        """
        Waits for the specifed state to occur. This is particularly useful when
        a command is requested.
        """

        attempts = 0
        pstate = None
        result = False
        self.log.debug("Waiting for state {0}".format(state))

        while not result:
            pstate = self.getProbeMeasState()
            result = pstate==state

            if attempts > retry:
                self.log.error("Retry Exceeded waiting for state {0}".format(state))
                result = False
                break
            else:
                attempts +=1

            time.sleep(0.1)
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
            #***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readRawSensorData error: Data integrity error (not all "
                      "segments read)")
                return None
            expected_bytes = ret['SegmentsRead'] * 256
            if (expected_bytes != ret['BytesRead']):
                # Data integrity error (not all bytes read - incomplete segment)
                # For the raw sensor data, this is also the check to ensure we have an even amount of bytes to break into sensor pairs
                self.log.error("readRawSensorData error: Data integrity error (not all "
                      "bytes read - incomplete segment)")
                self.log.error("Expected=%d, Read=%d" % (expected_bytes, ret['BytesRead']))
                return None

            #***** DATA PARSING *****
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

    def readRawAccelerationData(self):
        """
        Reads the RAW acceleration data
        helpme - Accelerometer data from the probe

        Returns:
            dict: containing accel data (x,y,z) or None if read failed


        """
        ret = self.__readData(1)

        # Sucessfully read data
        if (ret['status'] == 1):
            #***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                # Data integrity error (not all segments read)
                self.log.error("readRawAccelerationData error: Data integrity error (not"
                      " all segments read)")
                return None

            total_bytes = ret['BytesRead']

            # Data integrity error (not all bytes read - incomplete data segment)
            if ( (total_bytes % 6) != 0 ):
                # The data set is not an integer multiple of 6 (2 bytes per
                # axis, 3 axes total)
                self.log.error("readRawAccelerationData error: Data integrity error "
                      "(incomplete data set)")
                return None

            #***** DATA PARSING *****
            data = ret['Data']
            x_axis = []
            y_axis = []
            z_axis = []
            total_runs = total_bytes // 6
            offset = 0

            for ii in range(0, total_runs):
                x_axis.append((data[(offset + 0)] + (data[(offset + 1)] * 256) ) / 1000)
                y_axis.append((data[(offset + 2)] + (data[(offset + 3)] * 256) ) / 1000)
                z_axis.append((data[(offset + 4)] + (data[(offset + 5)] * 256) ) / 1000)
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
            #Sucessfully read data
            #***** DATA INTEGRITY CHECK *****
            # Data integrity error (not all segments read)
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                      "error (not all segments read)")
                return None
            total_bytes = ret['BytesRead']
            if ( (total_bytes % 4) != 0 ):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation number is a 32-bit int => 4 bytes)
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                      "error (incomplete data set)")
                return None

            #***** DATA PARSING *****
            data = ret['Data']
            correll_data = []
            total_runs = total_bytes // 4
            offset = 0

            for ii in range(0, total_runs):
                correll_data.append(data[(offset + 0)] + (data[(offset + 1)] * 256) + (data[(offset + 2)] * 65536) + (data[(offset + 3)] * 16777216))
                offset = offset + 4
            return correll_data
        else:
            #Read failed!
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

            # Data integrity error (not all bytes read - incomplete data segment)
            total_bytes = ret['BytesRead']
            if ((total_bytes % 3) != 0):
                # The data set is not an integer multiple of 3 (Raw pressure is in 24-bit format => 3 bytes)
                self.log.error("readRawPressureData error: Data integrity error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['Data']
            pressure_data = []
            total_runs = total_bytes // 3
            offset = 0
            for ii in range(0, total_runs):
                this_value = data[(offset + 0)] + (data[(offset + 1)] * 256) + \
                            (data[(offset + 2)] * 65536)

                pressure_data.append(this_value/4096)
                offset = offset + 3
            return pressure_data

        # Read failed!
        else:
            return None

    def readDepthData(self):
        """
        Reads the converted depth data, including the correlation index
        Return type is a dict containing data or None if read failed
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
                #values are 32-bit long => 4 bytes)
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

        helpme - The probe's filtered depth data is the filtered depth
        calculated from barometer data where the amount of filtering is set by
        the ZPFO option under settings.

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
                # The data set is not an integer multiple of 4 (Floatingpoint values are 32-bit long => 4 bytes)
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
            #Sucessfully read data
            #***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                #Data integrity error (not all segments read)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                      "error (not all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ( (total_bytes % 4) != 0 ):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation number is a 32-bit int => 4 bytes)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                      "error (incomplete data set)")
                return None

            #***** DATA PARSING *****
            data = ret['Data']
            correll_data = []
            total_runs = total_bytes // 4
            offset = 0

            for ii in range(0, total_runs):
                correll_data.append(data[(offset + 0)] + (data[(offset + 1)] * \
                                    256) + (data[(offset + 2)] * 65536) + \
                                    (data[(offset + 3)] * 16777216))
                offset = offset + 4
            return correll_data

        else:
            #Read failed!
            return None

    def readSensorDepthCombo(self):
        """
        Reads the processed data as a sensor-depth combo
        """

        ret = self.__readData(7)
        if (ret['status'] == 1):
            #Sucessfully read data
            #***** DATA INTEGRITY CHECK *****
            if (ret['SegmentsAvailable'] != ret['SegmentsRead']):
                #Data integrity error (not all segments read)
                self.log.error("readSensorDepthCombo error: Data integrity error (not "
                      "all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if ( (total_bytes % 16) != 0 ):
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation number is a 32-bit int => 4 bytes)
                self.log.error("readPressureDepthCorrelationData error: Data integrity"
                      " error (incomplete data set)")
                return None

            self.log.info("Total Datapoints = %d" % ret['SegmentsRead'])
            #***** DATA PARSING *****
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
                transaction_id.append(this_data_set[0] + (this_data_set[1] * \
                                      256) + (this_data_set[2] * 65536) + \
                                      (this_data_set[3] * 16777216))
                depth.append(this_data_set[4] + (this_data_set[5] * 256) + \
                             (this_data_set[6] * 65536) + (this_data_set[7] * \
                             16777216))
                sensor1.append(this_data_set[8] + (this_data_set[9] * 256))
                sensor2.append(this_data_set[10] + (this_data_set[11] * 256))
                sensor3.append(this_data_set[12] + (this_data_set[13] * 256))
                sensor4.append(this_data_set[14] + (this_data_set[15] * 256))
                offset = offset + 16
            return {'ID': transaction_id, 'Sensor1': sensor1,
                                          'Sensor2': sensor2,
                                          'Sensor3': sensor3,
                                          'Sensor4': sensor4,
                                          'Depth': depth}
        else:
            #Read failed!
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

        elif (ret['errorCode'] != None):
            self.log.error("getMeasTemp error: %d" % ret['errorCode'])
        else:
            self.log.error("getMeasTemp error: COM")
        return None

    def getZPFO(self):
        """
        Reads the probes zpfo
        """

        ret = self.api.MeasGetZPFO()
        if (ret['status'] == 1):
            data = ret['data']
            value = int.from_bytes(data,byteorder = 'little')
            return value

        elif (ret['errorCode'] != None):
            self.log.error("getZPFO error: %d" % ret['errorCode'])
        else:
            self.log.error("getZPFO error: COM")
        return None

    def getProbeHeader(self):
        """
        Returns the lines that should be in every data file produced.
        """
        t = datetime.datetime.now()
        fstr = "{0}-{1:02d}-{2:02d}--{3:02d}:{4:02d}:{5:02d}"
        time_stamp = fstr.format(t.year,t.month,t.day,
                                 t.hour,t.minute,t.second)

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

    def getSetting(self,**kwargs):
        """
        Reads the probes setting
        helpme - Zero phase filter order for smoothing the depth data

        """
        setting_name = kwargs['setting_name']
        if setting_name == 'calibdata':
            ret = self.getters[setting_name](kwargs['sensor'])

        else:
            ret = self.getters[setting_name]()

        if (ret['status'] == 1):
            data = ret['data']
            value = int.from_bytes(data,byteorder = 'little')
            return value
        elif (ret['errorCode'] != None):
            out.error("get{0} error: {1}".format(setting_name, ret['errorCode']))
            return None

        else:
            out.error("get{0} error: COM".format(setting_name))
            return None

    def setSetting(self,**kwargs):
        """
        sets the probe's setting
        """
        setting_name = kwargs['setting_name']

        if setting_name == 'calibdata':
            ret = self.settings[setting_name](kwargs['sensor'],
                                              kwargs['hi_value'])

        else:
            ret = self.settings[setting_name](kwargs['value'])

        if (ret['status'] == 1):
            return True
        elif (ret['errorCode'] != None):
            out.error("get{0} error: {1}".format(setting_name, ret1['errorCode']))
        else:
            out.error("get{0} error: COM".format(setting_name))
        return None
