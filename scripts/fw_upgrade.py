
import argparse
import os
import time

from radicl import serial as rs
from radicl.api import RAD_API
from radicl.update import FW_Update
from radicl.ui_tools import get_logger


def Upgrade(fw_image):
    app_header_version = 0
    app_header_length = 0
    app_header_entry = 0
    app_header_crc = 0
    counter = 0
    log = get_logger(__name__)
    port = rs.RAD_Serial()

    try:
        port.openPort()

    except Exception as e:
        log.error(e)
    if (port.serial_port is None):
        log.info("No device present")
    else:
        port.flushPort()
        # Create the API
        api = RAD_API(port)  # The API class is linked to the port object
        api.sendApiPortEnable()

        # Delay a bit and then identify the attached device
        time.sleep(0.5)
        ret = api.Identify()

        # Prior to FW revision 1.45, only 16 byte packages were possible. With FW revision 1.45 and above, the package size can be increased up to
        # 64 byes. Although it is technically possible to send up to 256 bytes in a package, there is a bug in the USB transport layer that causes
        # issues when transfering more than 64 bytes at a time. Until this is
        # resolved, 64 bytes is the max.
        if api.FWRev() >= 1.45:
            transfer_size = 64
        else:
            transfer_size = 16

        # The FW Update class is linked to the API object
        fw = FW_Update(api, transfer_size)

        # If the identification succeeded, carry on with the normal operation
        ret = 1
        if (ret):
            # The device was successfully identified.
            # NORMAL OPERATION

            ret = fw.loadFile(fw_image)
            if (ret == 1):
                ret = fw.upgrade()
                if (ret == 1):

                    # FW upgrade succeeded. Close the port, wait a bit, and
                    # then attempt to read the new FW version
                    port.closePort()
                    log.info("***** CHECK NEW FW VERSION ON PROBE *****")
                    log.info("Wait for probe to finish internal upgrade")
                    num_attempt = 1

                    while (num_attempt < 4):
                        log.info("Attempt %d" % num_attempt)
                        num_attempt += 1
                        num_delay = 10
                        while (num_delay > 0):
                            log.info(
                                "\rAttempting to reconnect in %d seconds    " %
                                num_delay, end=" ")
                            num_delay -= 1
                            time.sleep(1)
                        # Attempt to reconnect and read the FW version
                        log.info("\n")
                        try:
                            port.openPort()
                        except Exception as e:
                            log.error(e)
                            port.closePort()

                        if (port.serial_port is None):
                            log.info("No device found.")
                            port.closePort()
                        else:
                            port.flushPort()
                            # Create the API
                            # The API class is linked to the port object
                            api = RAD_API(port)
                            fw = FW_Update(
                                api, 64)  # The FW Update class is linked to the API object
                            api.sendApiPortEnable()

                            # Delay a bit and then identify the attached device
                            time.sleep(0.5)
                            ret = api.Identify()
                            if (ret == 1):
                                log.info("Device successfully identified")
                                log.info("FW UPDATE COMPLETE AND VERIFIED. EXITING...")
                                port.closePort()
                                exit()
                    # If we get here then we have failed all retries and not
                    # probe is present
                    log.info("##### NO PROBE FOUND #####")
            else:
                log.error("Unable to load file. Exiting")

            fw.closeFile()

    port.closePort()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RAD Probe FW Upgrade Tool')
    parser.add_argument('file', help='path to .bin file', nargs='+')

    args = parser.parse_args()

    if args.file is not None:
        fw_image_file = args.file[0]
        if os.path.isfile(fw_image_file) and fw_image_file.split(
                '.')[-1] == 'bin':
            Upgrade(fw_image_file)
        else:
            log.error("Invalid file %s" % fw_image_file)

    # Upgrade("RAD_PB3_REVC_1_45_3_0.bin")
