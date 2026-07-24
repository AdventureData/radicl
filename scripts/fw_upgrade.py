
import argparse
import os
import re
import time

from radicl.update import FW_Update
from radicl.ui_tools import get_logger
from radicl.probe import  RAD_Probe

# Probe hardware revision: filename token -> hw_rev integer reported by the probe
FW_REV_MAP = {'REVB': 1, 'REVC': 2, 'REVD': 3}


def rev_from_filename(path):
    """Return the hw_rev int encoded in a firmware filename, or None if absent."""
    m = re.search(r'REV([BCD])', os.path.basename(path).upper())
    return FW_REV_MAP.get('REV' + m.group(1)) if m else None


def rev_name(rev):
    """Reverse-map an hw_rev int back to its REVB/C/D token for readable messages."""
    for name, idx in FW_REV_MAP.items():
        if idx == rev:
            return name
    return 'REV?({})'.format(rev)


def Upgrade(fw_image):
    log = get_logger(__name__)

    probe = RAD_Probe()
    probe.connect()

    # Verify the firmware file's hardware revision matches the attached probe
    file_rev = rev_from_filename(fw_image)
    probe_rev = probe.api.hw_rev
    if file_rev is None:
        log.error("Firmware filename '%s' has no REVB/C/D token; cannot verify it "
                  "matches the probe. Aborting." % os.path.basename(fw_image))
        probe.disconnect()
        return
    if file_rev != probe_rev:
        log.error("Firmware revision mismatch. File is for %s but the attached probe "
                  "is %s. Aborting." % (rev_name(file_rev), rev_name(probe_rev)))
        probe.disconnect()
        return

    # RE: Transfer size - Prior to FW revision 1.45, only 16 byte packages were possible. With FW revision 1.45 and above,
    # the package size can be increased up to 64 byes. Although it is technically possible to send up to 256
    # bytes in a package, there is a bug in the USB transport layer that causes issues when transferring more
    # than 64 bytes at a time. Until this is resolved, 64 bytes is the max.


    # The FW Update class is linked to the API object
    fw = FW_Update(probe.api)

    # If the identification succeeded, carry on with the normal operation
    ret = 1
    if ret:
        # The device was successfully identified.
        # NORMAL OPERATION
        ret = fw.loadFile(fw_image)
        if ret == 1:
            ret = fw.upgrade()
            if ret == 1:
                # FW upgrade succeeded. Close the port, wait a bit, and
                # then attempt to read the new FW version
                probe.disconnect()
                log.info("***** CHECK NEW FW VERSION ON PROBE *****")
                log.info("Wait for probe to finish internal upgrade")
                num_attempt = 1

                while num_attempt < 4:
                    log.info(f"Attempt {num_attempt}")
                    num_attempt += 1
                    num_delay = 10
                    while num_delay > 0:
                        log.info(
                            "\rAttempting to reconnect in %d seconds    " %
                            num_delay)
                        num_delay -= 1
                        time.sleep(1)
                    # Attempt to reconnect and read the FW version
                    log.info("\n")
                    try:
                        probe = RAD_Probe()
                        probe.connect()

                    except Exception as e:
                        log.error(e)
                        probe.disconnect()

                    if probe.api.port.serial_port is None:
                        log.info("No device found.")
                        probe.disconnect()
                    else:
                        # Create the API
                        fw = FW_Update(probe.api)  # The FW Update class is linked to the API object

                        # Delay a bit and then identify the attached device
                        time.sleep(0.5)
                        ret = probe.api.Identify()
                        if ret == 1:
                            log.info("Device successfully identified")
                            log.info("FW UPDATE COMPLETE AND VERIFIED. EXITING...")
                            probe.disconnect()
                            exit()
                # If we get here then we have failed all retries and not
                # probe is present
                log.info("##### NO PROBE FOUND #####")
        else:
            log.error("Unable to load file. Exiting")

        fw.closeFile()

    probe.disconnect()


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
            print(f"Invalid file {fw_image_file}")

    # Upgrade("RAD_PB3_REVC_1_45_3_0.bin")
