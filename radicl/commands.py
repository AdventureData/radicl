from enum import Enum


class CMDEnum(Enum):
    @property
    def cmd(self):
        return self.value


class AttributeCMD(CMDEnum):
    """Commands to retrieve non-measurement attributes """
    SERIAL = 0x04
    HW_ID = 0x01
    HW_REV = 0x02
    FW_REV = 0x03
    FULL_FW_REV = 0x09


class MeasCMD(CMDEnum):
    """Commands for measurements"""
    START = 0x42
    STOP = 0x43
    STATE = 0x40
    RESET = 0x41
    NUM_SEGMENTS = 0x44
    DATA_SEGMENT = 0x45
    TEMP = 0x4F


class SettingsCMD(CMDEnum):
    """Commands for probe settings"""

    SAMPLING_RATE = 0x46
    ZPFO = 0x47
    PPMM = 0x48
    ALG = 0x49
    APPP = 0x4A
    TCM = 0x4B
    USERTEMP = 0x4C
    IR = 0x4D
    CALIBDATA = 0x4E
    ACCTHRESH = 0x50
    ACCZPFO = 0x51
    ACCRANGE = 0x52


class SystemCMD(CMDEnum):
    """Commands for the system"""
    START_BOOTLOADER = 0x05
    STATUS = 0x06
    STATE = 0x07  # Run state


class FWUpdateCMD(CMDEnum):
    """Commands for the firmware"""
    ENTER = 0xF0
    STATE = 0xF1
    SIZE = 0xF2
    DOWNLOAD = 0xF3
    CRC = 0xF4
    CLOSE = 0xF5
