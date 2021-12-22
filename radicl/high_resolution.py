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
import numpy as np

from radicl import __version__
from radicl.radicl import RADICL
from radicl.ui_tools import get_logger
from radicl.plotting import plot_hi_res


def pad_with_nans(ts, match_ts):
    """
    Resamples a dataframe to match another dataframe

    Args:
        ts: numpy array of time series thats not the same size as the timeseries to match
        match_ts: numpy array time series that the is to be matched in size
    Returns:

    """
    # Grab the ratio of indicies between the two datasets
    ratio = len(match_ts) / len(ts)

    # Create an empty array of nans
    new_data = np.zeros_like(match_ts).astype(np.float64)
    new_data[new_data == 0] = np.NaN

    # New data set index
    iz = 0

    # Repopulate around the nans where we have values
    for ii in np.arange(len(ts)):
        if ii != 0:
            iz = int(ii * ratio)

        new_data[iz] = ts[ii]

    return new_data


def build_high_resolution_data(cli, log):
    """
    Grabs the bottom sensors (sampled at the highest rate) then grabs the supporting sensors
    and pads with nans to fit into the same dataframe

    Args:
        cli: Instantiated Radicl() class
        log: Instantiated logger object

    Returns:
        ts: Single data frame containing Force, NIR, Ambient NIR, Accel, Depth
    """
    # Grab the calibrated data
    ts = cli.grab_data('rawsensor')[
        ['Sensor1', 'Sensor2', 'Sensor3']]

    # rts = cli.grab_data('rawsensor')
    depth = cli.grab_data('filtereddepth')['filtereddepth']

    # Grab accelerometer data
    acc = cli.grab_data('rawacceleration')['Y-Axis']

    log.info('Processing the depth data...')
    # Set the 0 point of depth to the Starting point or the snow Surface
    depth = depth - depth.values.min()

    # Invert Depth so bottom is negative max depth
    depth = depth - depth.values.max()

    log.info("Depth achieved: {} cm".format(abs(depth.max() - depth.min())))
    log.info("Depth Samples: {}".format(len(depth)))
    log.info("Acceleration Samples: {}".format(acc))

    supplemental_data = {'acceleration': acc,
                         'depth': depth
                         }

    # Reshape the supplemental_data and pad with Nans
    for name, data in supplemental_data.items():
        log.info("Padding {} data with Nans...".format(name))

        # Pad with nans
        new_data = pad_with_nans(data.values, ts['Sensor1'].values)

        # Assign the data
        ts[name] = new_data.copy()
    log.info("Interpolating between nan's...")
    ts = ts.interpolate()
    return ts


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
        '* Hardness\n'
        '* Active NIR\n'
        '* Passive NIR\n'
        '* Depth\n'
        '* Acceleration in the line of pole\n\n'
        'NOTE: The depth and accelerometer timeseries are all recorded at a lower'
        ' sampling rate than the sensors in the tip so they are interpolated to'
        ' match the Hardness and NIR timeseries')

    p = argparse.ArgumentParser(description='\n'.join([hdr, help_string]),
                                formatter_class=RawTextHelpFormatter)
    p.add_argument('-d', '--debug', dest='debug', action='store_true',
                   help="Debug flag will print out much more info")
    p.add_argument('-a', '--plot_all', dest='all', action='store_true',
                   help="When used will plot all datasets, otherwise it will "
                        " just plot the depth corrected data.")
    p.add_argument('--version', action='version',
                   version=('%(prog)s v{version}').format(version=__version__))
    args = p.parse_args()

    print(hdr)
    # Manage logging
    # Start this scripts logging
    log = get_logger("RAD Hi-Res Script", debug=args.debug)

    finished = False

    log.info("Starting High Resolution DAQ Script")

    # Retrieve a connection to the probe
    cli = RADICL()

    # Keep count of measurements taken
    i = 0

    # Reset the probe in the event the probe was closed out without reset
    response = cli.probe.resetMeasurement()

    # Loop through each sensor and retrieve the calibration data
    while not finished:
        # take a measurement
        input("\nPress enter to start listening for the probe to start...\n")
        print("Press probe button to start...")
        cli.listen_for_a_reading()

        ts = build_high_resolution_data(cli, log)

        plot_hi_res(df=ts)

        # ouptut the data to a datetime file
        cli.write_probe_data(ts, filename='')
        response = cli.probe.resetMeasurement()

        i += 1
        log.info("{} measurements taken this session".format(i))


if __name__ == '__main__':
    main()
