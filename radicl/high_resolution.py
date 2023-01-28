"""
This script shows the simplicity of using the radicl framework to access
settings information from the Lyte Probe.

This example the script collects the full calibrated signal from the probe
in addition to the depth data, allowing for high resolution profiles

Usage:  1. plug in the probe.
        2. Open a terminal
        3. python take_high_resolution_readings.py

"""

import argparse
from argparse import RawTextHelpFormatter
import pandas as pd
import json
import sys

from radicl import __version__
from radicl.interface import RADICL
from radicl.ui_tools import get_logger, exit_requested
from radicl.plotting import plot_hi_res


def build_high_resolution_data(cli, log):
    """
    Grabs the bottom sensors (sampled at the highest rate) then grabs the supporting sensors
    and pads with nans to fit into the same dataframe

    Args:
        cli: Instantiated Radicl() class
        log: Instantiated logger object

    Returns:
        result: Single data frame containing Force, NIR, Ambient NIR, Accel, Depth
    """
    # Grab the Raw data
    ts = cli.grab_data('rawsensor')

    # Grab relative, filtered barometer data
    depth = cli.grab_data('filtereddepth')

    # Grab Acceleration
    acc = cli.grab_data('rawacceleration')

    # Set the 0 point of depth to the Starting point or the snow Surface
    depth['depth'] = depth['filtereddepth'] - depth['filtereddepth'].min()

    # Invert Depth so bottom is negative max depth
    depth['depth'] = depth['depth'] - depth['depth'].max()
    depth = depth.drop(columns=['filtereddepth'])

    log.info("Barometer Depth achieved: {:0.1f} cm".format(abs(depth['depth'].max() - depth['depth'].min())))
    log.info("Depth Samples: {:,}".format(len(depth.index)))
    log.info("Acceleration Samples: {:,}".format(len(acc.index)))
    log.info("Sensor Samples: {:,}".format(len(ts)))

    log.info("Infilling and interpolating dataset...")
    result = pd.merge_ordered(ts, depth, on='time')
    result = pd.merge_ordered(result, acc, on='time')
    result = result.interpolate(method='index')
    return result


def main():
    # Parse command line arguments
    hdr = 'Lyte Probe High Resolution DAQ Script v{}'.format(__version__)
    underline = '=' * len(hdr)
    hdr = '\n'.join([hdr, underline, ''])

    help_string = (
        '\nThis script is used to take high resolution hand driven measurements with'
        ' the Lyte probe. This script requires: \n'
        '* A USB connection to the probe\n'
        '* The user to press the probe button for start and stop\n\n'
        'To accurately take High resolution measurements this script automatically'
        ' downloads the following timeseries from the probe per measurement:\n'
        '* Force\n'
        '* Active NIR\n'
        '* Passive NIR\n'
        '* Depth\n'
        '* Acceleration in the line of pole\n\n'
        'NOTE: The depth and accelerometer timeseries are all recorded at a lower'
        ' sampling rate than the sensors in the tip so they are interpolated to'
        ' match the Force and NIR timeseries'
        'Provide calibration coefficients via the calibration.json file to plot'
        ' data calibrated (Note data is still stored raw)'
    )

    p = argparse.ArgumentParser(description='\n'.join([hdr, help_string]),
                                formatter_class=RawTextHelpFormatter)
    p.add_argument('-d', '--debug', dest='debug', action='store_true',
                   help="Debug flag will print out much more info")
    p.add_argument('-c', '--calibration', dest='calibration',
                   help='Path to a json containing any calibration coefficients for any of the sensors')
    p.add_argument('--version', action='version',
                   version='%(prog)s v{version}'.format(version=__version__))
    p.add_argument('--plot_time', default=10, type=int, help='Automatically close a plot after number of seconds')

    p.add_argument('--n_measurements', default=0, type=int, help='Number of measurements to take without asking to exit')
    args = p.parse_args()

    if args.calibration is not None:
        with open(args.calibration, 'r') as fp:
            calibration = json.load(fp)
    else:
        calibration = {'Sensor1': [1, 0], 'Sensor2': [1, 0], 'Sensor3': [1, 0], 'Sensor4': [1, 0]}

    # Start this scripts logging
    log = get_logger("RAD Hi-Res Script", debug=args.debug)

    log.info("Starting High Resolution DAQ Script")

    # Retrieve a connection to the probe
    cli = RADICL()

    # Keep count of measurements taken
    i = 0

    # Reset the probe in the event the probe was closed out without reset
    response = cli.probe.resetMeasurement()

    # Grab the probe sample rate
    SR = cli.probe.getSetting(setting_name='samplingrate')
    zpfo = cli.probe.getSetting(setting_name='zpfo')
    acc_range = cli.probe.getSetting(setting_name='accrange')

    finished = exit_requested()

    # Loop through each sensor and retrieve the calibration data
    while not finished:

        # take a measurement
        cli.listen_for_a_reading()

        # Collect and build the data
        ts = build_high_resolution_data(cli, log)

        # Output the data to a datetime file
        cli.write_probe_data(ts, extra_meta={"SAMPLE RATE": str(SR),
                                             "ZPFO": str(zpfo),
                                             "ACC. Range": str(acc_range)})

        # Plot the data
        plot_hi_res(df=ts, calibration_dict=calibration, timed_plot=args.plot_time)

        # Reset the probe / clear out the data
        cli.probe.resetMeasurement()

        i += 1
        log.info(f"{i} measurements taken this session")
        if i >= args.n_measurements:
            finished = exit_requested()

    log.info(f"{i} measurements taken this session")
    log.info("Exiting High Resolution DAQ Script")
    sys.exit()


if __name__ == '__main__':
    main()
