# coding: utf-8

import os
import time
from radicl.serial import RadConnection, MessageColors, ProbeCommand

out = MessageColors()

def calibrate(probe, value_str):

    # raw_input(out.msg("Press enter to start a reading:"))
    # probe.send('meas start')
    # raw_input(out.msg("Press enter to stop a reading:"))
    # probe.send('meas stop')
    probe.take_a_reading(method = 'keyboard', timed = 1)

    cmd = ProbeCommand('fDump')
    try:
        result = probe.get_data(cmd)
    except:
        out.msg('ERROR: Failed to retrieve data. Exiting...','FAIL')
        probe.close()
        sys.exit()
    calib = []
    i = 1
    for col in result[1:]:
        if value_str == 'max':
            value = max(col)
        else:
            value = min(col)
        out.msg("Detected Sensor {1} calibration value = {0}".format(value,i))
        i+=1
        calib.append(value)

    time.sleep(0.25)
    probe.reset_probe()

    return calib

def main():
    if 'nt' in os.name:
        os.system('cls')  # for Windows
    else:
        os.system('clear')  # for Linux/OS X
    out.msg(out.BOLD + "-------------LYTE Probe Calibrator-------------",'HEADER')
    out.msg("USE:",'BOLD')
    out.msg("\tCalibrator will first take a reading\n\tto calibrate the high value then the\n\tlow value. Use targets to accomplish\n\tthe values for each high and low.")
    out.msg(out.BOLD + "----------------------------------------------",'HEADER')

    probe = RadConnection()
    out.msg("\nCover sensors using the high value producing target.")
    hi = calibrate(probe,"max")
    out.msg("\nCover sensors using the low value producing target.")
    low = calibrate(probe,"min")

    for i in range(4):
        if low[i] > hi[i]:
            out.msg('ERROR: Sensor {0}s Low calibration value is greater than the high calibration value.'.format(i),'FAIL')
        else:
            out.msg('\nApplying calibration values to sensor {0}'.format(i))
            probe.send('meas setCalib {0} {1} {2}'.format(i,low[i],hi[i]))

            probe.listen_for('calibration')
            out.msg("\n\tSensor {0} calibrated!".format(i),'OKGREEN')

if __name__ == '__main__':
    main()
