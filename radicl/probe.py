# coding: utf-8

import datetime
import inspect
import struct
import time
import numpy as np
import pandas as pd
from pathlib import Path

from . import __version__
from .com import RAD_Serial, find_kw_port
from .api import RAD_API
from .ui_tools import get_logger, parse_func_list
from .info import ProbeState, AccelerometerRange, SensorReadInfo


class RAD_Probe:
    """
    Class for directly interacting with the probe.

    """
    __data_buffer_guide = ['Raw Sensor', 'Acceleration', ' Raw Pressure',
                           'Raw Depth', 'Filtered Depth',
                           'Acceleration Correlation',
                           'Pressure/Depth Correlation',
                           'Depth Corrected Sensor']

    def __init__(self, ext_api: RAD_API=None, debug=False):
        """
        Args:
            ext_api: rad_api.RAD_API object pre-instantiated
        """

        self._state = ProbeState.NOT_SET
        self._last_state = ProbeState.NOT_SET
        self._sampling_rate = None
        self._accelerometer_range = None
        self._zpfo = None
        self._serial_number = None

        self._settings = None
        self._getters = None

        self.debug = debug
        self.api:RAD_API = ext_api
        self.available_devices = []

        self.log = get_logger(__name__, debug=self.debug)

    def update_devices(self):
        self.log.info("Scanning for COM ports...")
        self._available_devices = find_kw_port(['STMicroelectronics', 'STM32'])

    @property
    def serial_number(self):
        if self._serial_number is None:
            self._serial_number = self.getProbeSerial()
        return self._serial_number

    @property
    def multiple_devices_available(self):
        return len(self.available_devices) > 1

    @property
    def no_devices_available(self):
        return len(self.available_devices) == 0

    def connect(self, device=None):
        """ Attempt to establish a connection with the probe"""

        if self.api is None:
            # No external API object was provided. Create new serial and API
            # objects for internal use
            port = RAD_Serial(debug=self.debug)
            port.openPort()

            if not port:
                self.log.info("No device present")
            else:
                port.flushPort()
                # Create the API and FMTR instances The API class is linked to
                # the port object
                api = RAD_API(port, debug=self.debug)

                # Switch the device over to API mode
                api.sendApiPortEnable()
                self.api = api
                self.api.Identify()

        ret = self.getProbeMeasState()
        connected = True if ret is not None else False
        if not connected:
            self.log.error("Unable to connect to the probe. Unplug and"
                           " power cycle it.")
        return connected

    def disconnect(self):
        self.log.info("Disconnecting probe.")
        self.api.port.closePort()
        self.api = None

    @property
    def state(self):
        return  self._state

    @property
    def last_state(self):
        return self._last_state

    @property
    def sampling_rate(self):
        if self._sampling_rate is None:
            self._sampling_rate = self.getSetting(setting_name='samplingrate')
        return self._sampling_rate

    @property
    def zpfo(self):
        if self._zpfo is None:
            self._zpfo = self.getSetting(setting_name='zpfo')
        return self._zpfo

    @property
    def accelerometer_range(self):
        # Grab the range to scale the incoming data
        if self._accelerometer_range is None:
            sensing_range = self.getSetting(setting_name='accrange')
            # Add in a default
            if sensing_range is None:
                sensing_range = 16
            self._accelerometer_range = sensing_range
        return self._accelerometer_range

    def _assign_settings_functions(self):
        # Manages the settings
        settings_funcs = inspect.getmembers(self.api,
                                            predicate=inspect.ismethod)
        ignores = ['reset']
        self._settings = parse_func_list(settings_funcs,
                                        ['Meas', 'Set'],
                                        ignore_keywords=ignores)
        self._getters = parse_func_list(settings_funcs,
                                       ['Meas', 'Get'],
                                       ignore_keywords=ignores)

    @property
    def settings(self):
        """Dictionary of function to set settings"""
        if self._settings is None:
            self._assign_settings_functions()
        return self._settings

    @property
    def getters(self):
        """ Dictionary of functions to get settings"""
        if self._getters is None:
            self._assign_settings_functions()
        return self._getters


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

    def readData_by_segment(self, buffer_id, segment):
        """
        Read segments one at a time
        """
        # Data Segments to collect
        result = False

        # Request the data
        ret = self.api.MeasReadDataSegment(buffer_id, segment)

        if ret['status'] == 1 and ret['data'] is not None:
            data_chunk = ret['data']
        else:
            data_chunk = None
        return data_chunk

    def get_number_of_segments(self, buffer_id):
        """ Retrieve the number of data segments available from measurement"""
        ret = self.api.MeasGetNumSegments(buffer_id)
        if ret['status'] == 1:
            num_segments = int.from_bytes(ret['data'], byteorder='little')
        else:
            num_segments = None
        return num_segments

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
        num_segments = self.get_number_of_segments(buffer_id)
        if num_segments is not None:
            self.log.debug('Retrieving {:,} segments of {} data...'.format(num_segments, buffer_name.lower()))

        # No data returned
        else:

            self.log.debug(f"getNumSegments Error (buffer_id = {buffer_id})")

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
                    data_chunk = self.readData_by_segment(buffer_id, ii)

                    if data_chunk is not None:
                        data.extend(data_chunk)
                        byte_counter = len(data)
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
            result = self.manage_data_return(ret, dtype='hex') #.upper()
            if result is not None:
                result = result.upper()
        return result

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

        if self.state != data:
            self._last_state = self._state
            self._state = ProbeState.from_state(data)

        return data

    def startMeasurement(self):
        """
        Starts a new measurement. Returns 1 if successful, 0 otherwise
        """

        ret = self.api.MeasStart()
        self.log.debug("Start measurement requested.")

        if ret['status'] == 1:
            self.wait_for_state(ProbeState.MEASURING)
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
            self.wait_for_state(ProbeState.PROCESSING)
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
            result = self.wait_for_state(ProbeState.IDLE, delay=0.1)
            self.log.info("Probe measurement reset...")

            return 1

        else:
            self.manage_error(ret)

            return 0

    def wait_for_state(self, state:ProbeState, retry=500, delay=0.2):
        """
        Waits for the specified state to occur. This is particularly useful when
        a command is requested.

        Args:
            state: single integer
            retry: Number of attempts to try while Waiting for the states
            delay: time in seconds to wait between each attempt

        """

        attempts = 0
        result = False
        self.log.info(f"Waiting for state {state.value}, current state = {self.state.value}")

        while not result:
            result = self.state == state

            # Check for a probe advanced past the state
            if state != ProbeState.IDLE:
                if self.state >= state:
                    result = True

            if ProbeState.ready(state):
                if self.state == ProbeState.IDLE:
                        result = True

            if attempts > retry:
                self.log.error(
                    "Retry Exceeded waiting for state(s) {0}".format(state))
                result = False
                break
            else:
                attempts += 1

            time.sleep(delay)

            # Update the state
            self.getProbeMeasState()

        if result:
            self.log.debug(
                "{} queries while waiting for state {}".format(
                    attempts, state))

        return result

    def read_check_data_integrity(self, buffer_id, ret_dict, nbytes_per_value=None,
                                  nvalues=None, from_spi=False):
        """
        Receives a data function and  performs the data integrity check
        If the data is from _spi then we know how long the segments are.
        If there are not, then it is possible we receive an incomplete segment
        so we check for integer_multiples of that data

        Args:
            ret_dict: Returned dictionary of data and supporting meta
            nbytes_per_value: how many bytes expected per value per sample
            nvalues: Number of values expecter per sample
            from_spi: Is the data coming from SPI flash which guarantees a
                      segment size
        Returns:
            final: dict containing data in bytes, number of samples and
                   segments and return status.
        """

        buffer_name = self.__data_buffer_guide[buffer_id]
        final = None

        # successfully read data
        if ret_dict['data'] is None:
            self.log.error('Read error: No data available!')

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

    def unpack_sensor(self, data, sensor:SensorReadInfo):
        """
        Attempt to standardize the conversion of downloaded data for more usages
        Args:
            data: Data to unpack
            sensor: Sensor storage info
            extra_conversion: Option to add a more dynamic conversion like in accelerometer

        Returns:
            final: Dictionary of unpacked data

        """
        offset = 0
        final = {name: [] for name in sensor.data_names}

        unpack_bytes = sensor.unpack_type is not None
        convert = sensor.conversion_factor is not None

        samples = len(data) // sensor.bytes_per_sample

        for ii in range(0, samples):

            # Loop over each sensor and add it to the final dict
            for idx, name in enumerate(sensor.data_names):
                # Form the index for the bytes for the start of each value.
                byte_idx = idx * sensor.nbytes_per_value + offset

                # Certain datasets need to be unpacked
                if unpack_bytes:
                    # Form a byte object and unpack it
                    byte_list = data[byte_idx: (byte_idx + sensor.nbytes_per_value)]
                    byte_object = bytes(byte_list)
                    value = struct.unpack(sensor.unpack_type, byte_object)[0]

                else:
                    value = data[byte_idx] + \
                                   data[byte_idx + 1] * sensor.bytes_per_segment

                # Perform conversion of units
                if convert:
                    value *= sensor.conversion_factor

                # Grab each sensor value in the byte array
                final[name].append(value)

            # Move farther down the bytes to read the next segment.
            offset += sensor.nbytes_per_value * sensor.expected_values
        df = pd.DataFrame.from_dict(final)

        # Special Treatment of the accelerometer data
        if sensor == SensorReadInfo.ACCELEROMETER:
            self.log.info('Scaling accelerometer data')
            sensitivity = AccelerometerRange.from_range(self.accelerometer_range)
            df = df.mul(sensitivity.value_scaling)

        df = self.time_decimate(df, sensor)
        return df

    def time_decimate(self, df, sensor: SensorReadInfo):
        """
        Form the data into a dataframe and scale it according to the ratio of max
        sample rate as is done in the FW
        """
        n_samples = df.index.size
        # Decimation ratio for peripheral sensors
        ratio = self.sampling_rate / SensorReadInfo.RAWSENSOR.max_sample_rate
        sr = int(sensor.max_sample_rate * ratio)
        seconds = np.linspace(0, n_samples / sr, n_samples)
        df['time'] = seconds
        df = df.set_index('time')
        return df

    def _parse_data(self, sensor):
        ret = self.__readData(sensor.buffer_id)
        ret = self.read_check_data_integrity(sensor.buffer_id, ret, nbytes_per_value=sensor.nbytes_per_value,
                                             nvalues=sensor.expected_values, from_spi=sensor.uses_spi)
        final = None
        if ret is not None:
            final = self.unpack_sensor(ret['data'], sensor)
        return final

    def readRawSensorData(self):
        """
        Reads the RAW sensor data.
        helpme - Raw NIR data for 4 sensors

        Returns:
            dict - containing data or None if read failed
        """
        sensor = SensorReadInfo.RAWSENSOR
        return self._parse_data(sensor)

    # TODO update for calibration scheme
    # def readCalibratedSensorData(self):
    #     """
    #     Reads the Read Calibrated sensor data.
    #     helpme - Calibrated data for 4 sensors
    #
    #     Returns:
    #         dict - containing data or None if read failed
    #     """
    #     calib_data = {}
    #     raw = self.readRawSensorData()
    #
    #     for id in range(1, 5):
    #         sensor = "Sensor{}".format(id)
    #         d = self.getSetting(setting_name='calibdata', sensor=id)
    #
    #         # For the calibration for sensor 1 we invert
    #         if id == 1:
    #             # Set the slope to the negative difference
    #             m = 4095 / (d[0] - d[1])
    #             # Set the intercept to the LOW value
    #             b = d[1]
    #
    #         else:
    #             # Set the slope to the positive difference
    #             m = 4095 / (d[1] - d[0])
    #             # Set the intercept to the LOW value
    #             b = d[0]
    #
    #         calib_data[sensor] = [m * (x - b) for x in raw[sensor]]
    #
    #     return calib_data

    def readRawAccelerationData(self):
        """
        Reads the raw 3 axis  acceleration data
        helpme - Raw 3 axis accelerometer data from the probe

        Returns:
            dict: containing accel data (x,y,z) or None if read failed

        """
        sensor = SensorReadInfo.ACCELEROMETER
        return self._parse_data(sensor)

    def readRawPressureData(self):
        """
        Reads the RAW pressure data, including the correlation index
        """
        sensor = SensorReadInfo.RAW_BAROMETER_PRESSURE
        return self._parse_data(sensor)

    def readFilteredDepthData(self):
        """
        Retrieves the filtered depth data according to the zero-phase low-pass
        filter (equivalent to Matlab's 'filtfilt'). The amount of filtering
        applied is set by :func:`~radicl.RAD_API.MeasSetZPFO`

        helpme - The probe's filtered depth data is the raw depth data made
                 relative to the change and the amount filtered set by the ZPFO
                 option.

        """
        sensor = SensorReadInfo.FILTERED_BAROMETER_DEPTH
        return self._parse_data(sensor)

    def readMeasurementTemperature(self):
        """
        Reads the temperature from the last measurement
        """

        ret = self.api.MeasGetMeasTemp()
        result = struct.unpack('<i', ret['data'][5:])[0]
        return result

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
                  "FIRMWARE REVISION": self.api.full_fw_rev,
                  "HARDWARE REVISION": self.api.hw_rev,
                  "MODEL NUMBER": self.api.hw_id,
                  "Serial Num.":self.serial_number,
                  "Baro Temp.":self.readMeasurementTemperature(),
                  "ACC. Range": str(self.accelerometer_range)}
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
        # Successful change!
        if ret['status'] == 1:
            # Reset properties to pull again
            if setting_name == 'accrange':
                self._accelerometer_range = None

            elif setting_name == 'samplingrate':
                self._sampling_rate = None

            elif setting_name == 'zpfo':
                self._zpfo = None

            return True

        else:
            self.manage_error(ret)

        return None
