from enum import Enum


class ProbeState(Enum):
    """ States for the probe running during a measurement"""
    NOT_SET = 10
    IDLE = 0
    MEASURING = 1
    PROCESSING = 2
    DATA_STAGED = 3
    SENDING_DATA = 4
    RESET = 5
    UNKOWN_STATE = 11


    @classmethod
    def from_state(cls, state):
        final = cls.UNKOWN_STATE
        for e in cls:
            if e.value == state:
                final = e
                break
        return final

    @classmethod
    def ready(cls, state):
        """Function to determine if the probe is in an idle state"""
        return state in [cls.IDLE, cls.RESET]

    def __ge__(self, other):
        return self.value >= other.value

    def __le__(self, other):
        return self.value <= other.value

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value


class CLIState(Enum):
    """Enum for managing the cli state"""
    HOME = 0
    DAQ_HOME = 1
    DAQ_CHOICE = 2
    DAQ_MEASUREMENT = 3
    DAQ_OUTPUT = 4
    DAQ_FINISHED = 5
    SETTINGS_HOME = 6
    SETTINGS_CHOICE = 7
    MODIFY_SETTING = 8
    UNKNOWN = 99
    @classmethod
    def from_choice(cls, choice):
        """Return state based on user input"""
        result = cls.UNKNOWN
        if choice == 'daq':
            result = cls.DAQ_HOME
        elif choice == 'settings':
            result = cls.SETTINGS_HOME
        return result

class ProbeErrors(Enum):
    # Define by code and error string
    MEASUREMENT_NOT_RUNNING = 2049,  "The probe measurement/sensor is not running"
    GENERIC_ERROR =  2048, 'Generic Measurement error'
    PROBE_NOT_READY = 2050, "Measurement FSM not ready to start measurement"
    PROBE_ALREADY_STOPPED = 2051, " Measurement FSM already stopped (i.e. in ready/idle state)"
    PROBE_FAILED_TO_SET_PARAM = 2052, "Setting a parameter failed",
    INVALID_DATA_BUFFER = 2053, "Invalid buffer was addressed"
    FAILED_DATA_READ = 2054, "Reading data failed"
    UNKNOWN_ERROR = None, "Unrecognized error code"

    @property
    def error_code(self):
        return self.value[0]

    @property
    def error_string(self):
        return self.value[1]


    @classmethod
    def from_code(cls, code):
        final = cls.UNKNOWN_ERROR
        for e in cls:
            if e.error_code == code:
                final = e
                break
        return final


    @classmethod
    def to_dict(cls):
        final = {}
        for e in cls:
            final[e.error_code] = e.error_string
        return final


class AccelerometerRange(Enum):
    # From Data sheet for accelerometer in REV C
    RANGE_2G = 2, 0.06
    RANGE_4G = 4, 0.12
    RANGE_6G = 6, 0.18
    RANGE_8G = 8, 0.24
    RANGE_16G = 16, 0.73

    @property
    def sensing_range(self):
        return self.value[0]

    @property
    def value_scaling(self):
        return self.value[1]

    @classmethod
    def from_range(cls, sensing_range):
        final = None
        for e in cls:
            if e.sensing_range == sensing_range:
                final = e
                break
        return final


class SensorReadInfo(Enum):

    # Buffer Index, bytes per seg, number of bytes per value, expected number of values, does the data live in spi mem.
    RAWSENSOR = 0, 256, 2, 4, True, 'Raw Sensor', ["Sensor1", "Sensor2", "Sensor3", "Sensor4"], None, None, 16000
    # 3 axis acc, convert from mG to G
    ACCELEROMETER = 1, None, 2, 3, False, 'Acceleration', ["X-Axis", "Y-Axis", "Z-Axis"], '<h', 0.001, 100
    RAW_BAROMETER_PRESSURE = 2, 256, 3, 1, False, 'Raw Pressure', ['raw_pressure'], None, None, 75
    FILTERED_BAROMETER_DEPTH = 4, None, 4, 1, False, 'Filtered Barometer Depth', ['filtereddepth'], 'f', 0.01, 75


    @property
    def buffer_id(self):
        return self.value[0]

    @property
    def bytes_per_segment(self):
        return self.value[1]

    @property
    def nbytes_per_value(self):
        return self.value[2]

    @property
    def expected_values(self):
        return self.value[3]

    @property
    def uses_spi(self):
        return self.value[4]

    @property
    def readable_name(self):
        return self.value[5]

    @property
    def data_names(self):
        return self.value[6]

    @property
    def unpack_type(self):
        return self.value[7]

    @property
    def conversion_factor(self):
        return self.value[8]

    @property
    def max_sample_rate(self):
        return self.value[9]

    @property
    def bytes_per_sample(self):
        """ Number of bytes per sample"""
        return self.nbytes_per_value * self.expected_values

    @classmethod
    def from_data_request(cls, data_request):
        if data_request == 'filtered_depth':
            result = cls.FILTERED_BAROMETER_DEPTH
        elif data_request in ['calibratedsensor', 'rawsensor']:
            result = cls.RAWSENSOR
        elif data_request == 'rawpressure':
            result = cls.RAW_BAROMETER_PRESSURE
        elif data_request == 'rawacceleration':
            result = cls.ACCELEROMETER
        else:
            result = None
        return result


class Firmware:
    """
    Small firmware class for comparing firmwares
    """
    def __init__(self, firmware_str):
        if firmware_str is not None:
            self._info = firmware_str.split('.')
        else:
            self._info = (-1,-1,-1,-1)
        self.sub_versions = ['major_version', 'minor_version', 'patch_version', 'build_number']
        # Default to 0
        self.major_version = 0
        self.minor_version = 0
        self.patch_version = 0
        self.build_number = 0
        # Assign if the value was provided, assumed order ie. 1.3 == 1.3.0.0
        for i, version in enumerate(self.sub_versions):
            if i < len(self._info):
                setattr(self, version, int(self._info[i]))

    def __eq__(self, other):
        comparisons = [getattr(self, version) == getattr(other, version) for version in self.sub_versions]
        return all(comparisons)

    def __ge__(self, other):
        gt_comparisons = [getattr(self, version) > getattr(other, version) for version in self.sub_versions]
        eq_comparisons = [getattr(self, version) == getattr(other, version) for version in self.sub_versions]
        result = False
        for greater_than, equal in zip(gt_comparisons, eq_comparisons):
            if greater_than:
                result = True
                break
            elif not greater_than and not equal:
                result = False
                break
            elif equal:
                result = True

        return result

    def __gt__(self, other):
        result = False
        for  version in self.sub_versions:
            v = getattr(self, version)
            ov = getattr(other, version)
            if v > ov:
                result = True
                break

        return result

    def __repr__(self):
        return f"v{self.major_version}.{self.minor_version}.{self.patch_version}.{self.build_number}"


class PCA_Name(Enum):
    UNKNOWN = None
    PB1 = 1
    PB2 = 2
    PB3 = 3

    @classmethod
    def from_index(cls, idx):
        result = cls.UNKNOWN
        for e in cls:
            if e.idx == idx:
                result = e
                break
        return result

    @property
    def idx(self):
        return self.value
