# coding: utf-8

import datetime
import inspect
import struct
import sys
import time

from . import __version__
from .com import RAD_Serial
from .api import RAD_API
from .ui_tools import get_logger, parse_func_list

error_codes = {2049: "The probe measurement/sensor is not running",
               2048: 'Generic Measurement error',
               2050: "Measurement FSM not ready to start measurement",
               2051: " Measurement FSM already stopped (i.e. in ready/idle state)",
               2052: "Setting a parameter failed",
               2053: "Invalid buffer was addressed",
               2054: "Reading data failed"}

# From Data sheet for accelerometer in REV C
acc_sensitivity = {2: 0.06,
                   4: 0.12,
                   6: 0.18,
                   8: 0.24,
                   16: 0.73}


class RAD_Probe:
    """
    Class for directly interacting with the probe.

    """
    __data_buffer_guide = ['Raw Sensor', 'Acceleration', ' Raw Pressure',
                           'Raw Depth', 'Filtered Depth',
                           'Acceleration Correlation',
                           'Pressure/Depth Correlation',
                           'Depth Corrected Sensor']

    def __init__(self, ext_api=None, debug=False):
        """
        Args:
            ext_api: rad_api.RAD_API object preinstantiated
        """

        self.log = get_logger(__name__, debug=debug)

        # Check if an external API object was passed in.
        if ext_api is not None:
            # An external API object was provided. Use it. Note: We assume here
            # that the appropriate initialization, identification, and API port
            # enable procedure has already taken place
            self.api = ext_api
        else:
            # No external API object was provided. Create new serial and API
            # objects for internal use
            port = RAD_Serial(debug=debug)
            port.openPort()

            if not port:
                self.log.info("No device present")
            else:
                port.flushPort()
                # Create the API and FMTR instances The API class is linked to
                # the port object
                api = RAD_API(port, debug=debug)

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
                time.sleep(0.1)

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
            ret_dict: Dictionary of keys ['Status','data','errorCode']
            stack_id: number of functions up the stack to use for reporting
                      function name when errors occur.
        """
        name = inspect.stack()[stack_id][3]

        if ret_dict['errorCode'] is not None:
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

        if (ret['status'] == 1) and (ret['data'] is not None):

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

                elif dtype == 'hex':
                    value = data.hex()

                else:
                    raise ValueError(
                        "No types other than str, hex, and int are implemented")

                result.append(value)

            if num_values == 1:
                result = result[0]

        else:
            self.manage_error(ret, stack_id=2)
            result = None

        return result

    def __readData(self, buffer_id, max_retry=10, init_delay=0.004):
        """
        Private function to retrieve data from the probe.
         Args:
            buffer_id: Integer specifying location in the probe buffer
            max_retry: Integer number of attempts before exiting with a fail
        """

        result = False
        num_segments = 0
        data = []

        buffer_name = self.__data_buffer_guide[buffer_id]
        self.log.info("Querying probe for {} data...".format(buffer_name.lower()))

        # Final data to return
        final = {'status': 0, 'SegmentsAvailable': 0, 'SegmentsRead': 0,
                 'BytesRead': 0,
                 'data': None}

        # Get the number of data segments available
        ret = self.api.MeasGetNumSegments(buffer_id)

        if ret['status'] == 1:
            num_segments = int.from_bytes(ret['data'], byteorder='little')
            self.log.debug('Retrieving {:,} segments of {} data...'.format(num_segments, buffer_name.lower()))

        # No data returned
        else:

            self.log.debug("getNumSegments error: %d (buffer_id = %d)" %
                           (ret['errorCode'], buffer_id))

            if ret['errorCode'] is not None:
                self.log.debug("Error {:d} occurred.".format(ret['errorCode']))

                if ret['errorCode'] in error_codes.keys():
                    self.log.error(error_codes[ret['errorCode']])
                else:
                    self.log.warning("Unknown error code!")

        # If we do have number of segments
        if num_segments != 0 and num_segments is not None:
            self.log.debug("Reading %d segments" % num_segments)
            byte_counter = 0

            # Data Segments to collect
            for ii in range(0, num_segments):
                result = False

                # initial delay time
                wait_time = init_delay

                # Delays and retry
                for jj in range(0, max_retry):

                    time.sleep(wait_time)

                    # Request the data
                    ret = self.api.MeasReadDataSegment(buffer_id, ii)

                    if ret['status'] == 1 and ret['data'] is not None:
                        byte_counter = byte_counter + len(ret['data'])
                        data_chunk = ret['data']
                        data.extend(data_chunk)
                        result = True
                        # Break the retry loop
                        break

                    else:
                        if jj >= max_retry:
                            self.log.warning('Missed data segment, after {0:d} attempts.'.format(jj + 1))

                        # Developer friendly response in event of read error
                        msg = ("{0} Data Error: Buffer ID = {1:d}, "
                               "Segment ID={2:d}/{3:d}, Retry #{4:d}, "
                               " COM Delay = {5}s "
                               "").format(buffer_name, buffer_id, ii,
                                          num_segments, jj, wait_time)

                        self.log.debug(msg)

                        # Increase the wait time every failed request
                        wait_time += wait_time

                        if ret['errorCode'] is not None:
                            if ret['errorCode'] in error_codes.keys():
                                self.log.warning("Received error code:{}".format(error_codes[ret['errorCode']]))
                            else:
                                self.log.warning("Received unknown error code:{}".format(ret['errorCode']))

            # Was the data read successful?
            final['status'] = int(result)
            final['SegmentsAvailable'] = num_segments
            final['SegmentsRead'] = ii + 1  # Report this not zero based
            final['BytesRead'] = byte_counter

            if final['SegmentsRead'] > 0:
                final['data'] = data

        return final

    # ********************
    # * PUBLIC FUNCTIONS *
    # ********************
    def getProbeSerial(self):
        """
        Returns the probe's serial number. The return value is a string. If the
        request fails it will return None
        """

        ret = self.api.getSerialNumber()
        if ret['data'] is not None:
            # Flip the byte array since it comes in backwards
            ret['data'] = ret['data'][::-1]
            # upper case to match the store serial number lists
            return self.manage_data_return(ret, dtype='hex').upper()
        else:
            return self.manage_data_return(ret, dtype='hex')

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
        Starts a new measurement. Returns 1 if successful, 0 otherwise
        """

        ret = self.api.MeasStart()
        self.log.debug("Start measurement requested.")

        if ret['status'] == 1:
            self.wait_for_state(1)
            self.log.info("Measurement started...")

            return 1

        else:
            self.manage_error(ret)

            return 0

    def stopMeasurement(self):
        """
        Stops an ongoing measurement. Returns 1 if successful, 0 otherwise
        """

        ret = self.api.MeasStop()
        self.log.debug("Stop measurement requested.")

        if ret['status'] == 1:
            self.wait_for_state(3)
            self.log.info("Measurement stopped...")

            return 1
        else:
            self.manage_error(ret)

            return 0

    def resetMeasurement(self):
        """
        Resets the measurement FSM to prepare for a new measurement.
        Returns 1 if successful, 0 otherwise
        """

        ret = self.api.MeasReset()
        self.log.debug("Measurement reset requested...")

        if ret['status'] == 1:
            self.wait_for_state(0, delay=0.1)
            self.log.info("Probe measurement reset...")

            return 1

        else:
            self.manage_error(ret)

            return 0

    def wait_for_state(self, state, retry=500, delay=0.2):
        """
        Waits for the specified state to occur. This is particularly useful when
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

    def read_check_data_integrity(self, buffer_id, nbytes_per_value=None,
                                  nvalues=None, from_spi=False):
        """
        Receives a data function and  performs the data integrity check
        If the data is from _spi then we know how long the segments are.
        If there are not, then it is possible we receive an incomplete segment
        so we check for integer_multiples of that data

        Args:
            buffer_id: Index the data is in the probe buffer
            nbytes_per_value: how many bytes expected per value per sample
            nvalues: Number of values expecter per sample
            from_spi: Is the data coming from SPI flash which guarantees a
                      segment size
        Returns:
            final: dict containing data in bytes, number of samples and
                   segements and return status.
        """

        buffer_name = self.__data_buffer_guide[buffer_id]

        ret_dict = self.__readData(buffer_id)
        final = None

        # successfully read data
        if ret_dict['status'] != 1:
            self.log.error('Read {} error: No data available!'
                           ''.format(buffer_name))
            self.log.debug('Data received from probe:\n{}'.format(ret_dict))

        else:

            # ***** DATA INTEGRITY CHECK *****
            # Check for all segments read in
            all_segments = (ret_dict['SegmentsAvailable'] == \
                            ret_dict['SegmentsRead'])
            int_multiple = nbytes_per_value * nvalues

            # Grab the number of samples, NOTE this is only valid if the
            # ...conditions are true below
            samples = ret_dict['BytesRead'] // int_multiple

            # Data from SPI Flash
            if from_spi:
                expected_bytes = ret_dict['SegmentsRead'] * 256

                # Check we read all bytes:
                complete_bytes = expected_bytes == ret_dict['BytesRead']
                self.log.debug('Downloaded {:0,.2f}/{:0,.2f} Kb.'.format(
                    ret_dict['BytesRead'] / 1000,
                    expected_bytes / 1000))
            # From chip memory
            else:
                # We can have incomplete segments, so check for even numbers
                complete_bytes = ret_dict['BytesRead'] % int_multiple == 0
                self.log.debug('Byte Multiples: {:0,.2f}'.format(ret_dict['BytesRead'] / int_multiple))

            # Check the data integrity
            if not all_segments or not complete_bytes:
                self.log.error("Data Integrity Error: Unable to retrieve all "
                               "data for {}.".format(buffer_name))
                self.log.debug('All Segments not downloaded: {}, All bytes '
                               'downloaded: {}'.format(all_segments, complete_bytes))
            else:
                final = ret_dict
                final['samples'] = samples

                # Final reporting
                self.log.info('Retrieving {:,} samples of {} data...'
                              ''.format(ret_dict['samples'], buffer_name))

            self.log.debug("Segment Retrieved {:,d}/{:,d}."
                           " Bytes Retrieved {:0,.2f} Kb"
                           "".format(ret_dict['SegmentsRead'],
                                     ret_dict['SegmentsAvailable'],
                                     ret_dict['BytesRead'] / 1000))

            return final

    def readRawSensorData(self):
        """
        Reads the RAW sensor data.
        helpme - Raw NIR data for 4 sensors

        Returns:
            dict - containing data or None if read failed
        """

        # Index in the probe buffer
        buffer_id = 0

        # Expected bit size of the data
        sgbytes = 256
        nbytes_per_value = 2
        nvalues = 4

        ret = self.read_check_data_integrity(buffer_id,
                                             nbytes_per_value=nbytes_per_value,
                                             nvalues=nvalues, from_spi=True)

        # ***** DATA PARSING *****
        if ret is not None:
            data = ret['data']
            samples = ret['samples']
            offset = 0
            final = {'Sensor1': [], 'Sensor2': [], 'Sensor3': [], 'Sensor4': []}

            for ii in range(0, samples):

                # Loop over each sensor and add it to the final dict
                for idx in range(nvalues):
                    # Create a name for the dictionary
                    name = 'Sensor{}'.format(idx + 1)

                    # Form the index for the bytes for the start of each value.
                    byte_idx = idx * nbytes_per_value + offset

                    # Grab each sensor value in the byte array
                    final[name].append(data[byte_idx] + \
                                       data[byte_idx + 1] * sgbytes)

                # Move farther down the bytes to read the next segment.
                offset += nbytes_per_value * nvalues

            data = final
        return data

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
        acc_axes = ['X', 'Y', 'Z']
        name_str = '{}-Axis'
        # Index in the probe buffer
        buffer_id = 1

        # Expected bit size of the data
        nbytes_per_value = 2
        nvalues = len(acc_axes)

        ret = self.read_check_data_integrity(buffer_id,
                                             nbytes_per_value=nbytes_per_value,
                                             nvalues=nvalues)
        data = None

        if ret is not None:
            data = ret['data']

            samples = ret['samples']

            # Initialize the data
            final = {name_str.format(a): [] for a in acc_axes}
            offset = 0

            # Grab the range to scale the incoming data
            a_r = self.getSetting(setting_name='accrange')
            sensitivity = acc_sensitivity[a_r]

            # Loop over all the samples
            for ii in range(0, samples):
                # Loop over the sample and extract each axis
                for idx, axis in enumerate(acc_axes):
                    # Form the dictionary name
                    name = name_str.format(axis)

                    # Form the index of where each axis is in the sample
                    byte_idx = idx * nbytes_per_value + offset

                    # Grab the bytes from the list for a single axis
                    byte_list = data[byte_idx: (byte_idx + nbytes_per_value)]

                    # Form a byte object
                    byte_object = bytes(byte_list)

                    # Unpack bytes originally a 32 bit long and save
                    value = struct.unpack('<h', byte_object)[0]

                    # Convert to milli-gs while accounting for acc. range
                    value *= sensitivity
                    # Convert to Gs.
                    value /= 1000

                    final[name].append(value)

                # Advance forward in the data from probe for parsing
                offset += nbytes_per_value * nvalues

            # Assign final to the original data var for return
            data = final

        return data

    def readAccelerationCorrelationData(self):
        """
        Reads the acceleration correlation data
        """

        ret = self.__readData(5)
        if ret['status'] == 1:
            # successfully read data
            # ***** DATA INTEGRITY CHECK *****
            # Data integrity error (not all segments read)
            if ret['SegmentsAvailable'] != ret['SegmentsRead']:
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                               "error (not all segments read)")
                return None

            total_bytes = ret['BytesRead']

            if (total_bytes % 4) != 0:
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation
                # number is a 32-bit int => 4 bytes)
                self.log.error("readAccelerationCorrelationData error: Data integrity "
                               "error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['data']
            correll_data = []
            samples = total_bytes // 4
            offset = 0

            for ii in range(0, samples):
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

        # successfully read data
        if ret['status'] == 1:
            # ***** DATA INTEGRITY CHECK *****
            if ret['SegmentsAvailable'] != ret['SegmentsRead']:
                # Data integrity error (not all segments read)
                self.log.error("readRawPressureData error: Data integrity error (not "
                               "all segments read)")
                return None

            # Data integrity error (not all bytes read - incomplete data
            # segment)
            total_bytes = ret['BytesRead']
            if (total_bytes % 3) != 0:
                # The data set is not an integer multiple of 3 (Raw pressure is
                # in 24-bit format => 3 bytes)
                self.log.error(
                    "readRawPressureData error: Data integrity error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['data']
            pressure_data = []
            samples = total_bytes // 3
            offset = 0

            for ii in range(0, samples):
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
        if ret['status'] == 1:
            # successfully read data
            # ***** DATA INTEGRITY CHECK *****
            if ret['SegmentsAvailable'] != ret['SegmentsRead']:
                # Data integrity error (not all segments read)
                self.log.error("readDepthData error: Data integrity error (not all "
                               "segments read)")
                return None

            total_bytes = ret['BytesRead']
            if (total_bytes % 4) != 0:
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Floating point)
                # values are 32-bit long => 4 bytes)
                self.log.error("readDepthData error: Data integrity error "
                               "(incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['data']
            depth_data = []
            samples = total_bytes // 4
            offset = 0
            for ii in range(0, samples):
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

        # Index in the probe buffer
        buffer_id = 4

        # Expected bit size of the data
        nbytes_per_value = 4
        nvalues = 1

        ret = self.read_check_data_integrity(buffer_id,
                                             nbytes_per_value=nbytes_per_value,
                                             nvalues=nvalues)
        data = None

        if ret is not None:
            data = ret['data']
            samples = ret['samples']
            depth_data = []
            offset = 0

            for ii in range(0, samples):
                this_byte_list = data[offset:(offset + nbytes_per_value)]
                this_byte_object = bytes(this_byte_list)
                this_value = struct.unpack('f', this_byte_object)
                depth_data.append(this_value)
                offset += nbytes_per_value

            # Convert to cm
            depth_data = [(c[0] / 100.0) for c in depth_data]
            data = depth_data

        return data

    def readPressureDepthCorrelationData(self):
        """
        Reads the pressure/depth correlation data
        """

        ret = self.__readData(6)
        if ret['status'] == 1:
            # successfully read data
            # ***** DATA INTEGRITY CHECK *****
            if ret['SegmentsAvailable'] != ret['SegmentsRead']:
                # Data integrity error (not all segments read)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                               "error (not all segments read)")
                return None

            total_bytes = ret['BytesRead']
            if (total_bytes % 4) != 0:
                # Data integrity error (not all bytes read - incomplete data segment)
                # The data set is not an integer multiple of 4 (Correlation
                # number is a 32-bit int => 4 bytes)
                self.log.error("readPressureDepthCorrelationData error: Data integrity "
                               "error (incomplete data set)")
                return None

            # ***** DATA PARSING *****
            data = ret['data']
            correll_data = []
            samples = total_bytes // 4
            offset = 0

            for ii in range(0, samples):
                correll_data.append(data[(offset + 0)] + (data[(offset + 1)] *
                                                          256) + (data[(offset + 2)] * 65536) +
                                    (data[(offset + 3)] * 16777216))
                offset = offset + 4
            return correll_data

        else:
            # Read failed!
            return None

    def readDepthCorrectedSensorData(self):
        """
        Reads the processed data as a sensor-depth combo
        """
        # Data columns
        nsensors = 4
        name_str = 'Sensor{}'
        sensor_names = [name_str.format(i) for i in range(1, nsensors + 1)]

        # Index in the probe buffer
        buffer_id = 7

        # Expected byte size of the data
        nbytes_per_value = 4
        nvalues = 4

        ret = self.read_check_data_integrity(buffer_id,
                                             nbytes_per_value=nbytes_per_value,
                                             nvalues=nvalues, from_spi=False)
        data = None

        if ret is not None:
            # initialize
            data = ret['data']
            samples = ret['samples']
            final = {sensor: [] for sensor in sensor_names}
            final['depth'] = []
            nbytes = nbytes_per_value * nvalues
            sgbytes = 256
            offset = 0

            # Loop over all the samples
            for ii in range(0, samples):
                data_set = data[offset: offset + nbytes]

                # Grab the depth
                final['depth'].append(data_set[4] + (data_set[5] * sgbytes) +
                                      (data_set[6] * 65536) + (data_set[7] *
                                                               16777216))

                for idx, name in enumerate(sensor_names):
                    # Starts at idx 8 in the buffer
                    byte_idx = idx * 2 + 8
                    final[name].append(data_set[byte_idx] + \
                                       data_set[byte_idx + 1] * sgbytes)
                offset += nbytes

            data = final

        return data

    def readMeasurementTemperature(self):
        """
        Reads the temperature from the last measurement
        """

        ret = self.api.MeasGetMeasTemp()
        return self.manage_error(ret)

    def getProbeHeader(self):
        """
        Returns the lines that should be in every data file produced.
        """
        t = datetime.datetime.now()
        fstr = "{0}-{1:02d}-{2:02d}--{3:02d}:{4:02d}:{5:02d}"
        time_stamp = fstr.format(t.year, t.month, t.day,
                                 t.hour, t.minute, t.second)
        header = {"RECORDED": time_stamp,
                  "radicl VERSION": __version__,
                  "FIRMWARE REVISION": self.api.fw_rev,
                  "HARDWARE REVISION": self.api.hw_rev,
                  "MODEL NUMBER": self.api.hw_id}
        return header

    def getSetting(self, setting_name=None, sensor=None):
        """
        Reads the probes setting from the dictionary of functions. Calls the
        function and manages the data.

        Args:
            setting_name: name of the function minus Meas and get
            sensor: Sensor ID for calibration data

        Returns:
            int: from the function getting the probe setting, or list of 2 for calibration data
        """
        if setting_name == 'calibdata':
            ret = self.getters[setting_name](sensor)
            num_values = 2
        else:
            ret = self.getters[setting_name]()
            num_values = 1

        return self.manage_data_return(ret, num_values=num_values, dtype=int)

    def setSetting(self, setting_name=None, sensor=None, value=None, low_value=None,
                   hi_value=None):
        """
        sets the probe's setting
        """

        if setting_name == 'calibdata':
            ret = self.settings[setting_name](sensor, low_value, hi_value)

        else:
            ret = self.settings[setting_name](value)

        if ret['status'] == 1:
            return True

        else:
            self.manage_error(ret)

        return None
