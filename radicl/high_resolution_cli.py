"""
This script shows the simplicity of using the radicl framework to access
settings information from the Lyte Probe.

This example the script collects the full calibrated signal from the probe
in addition to the depth data, allowing for high resolution profiles

Usage:  1. plug in the probe.
        2. Open a terminal
        3. python take_high_resolution_readings.py

"""

from radicl import __version__
from radicl.interface import RADICL
from radicl.ui_tools import get_logger, exit_requested
from radicl.plotting import plot_hi_res
from radicl.high_resolution import build_high_resolution_data
from radicl.gps import USBGPS
import argparse
from argparse import RawTextHelpFormatter
import json
import sys
import logging


LOG = logging.getLogger(__name__)


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

    # Look for a gps
    gps = USBGPS()

    # Keep count of measurements taken
    i = 0

    # Reset the probe in the event the probe was closed out without reset
    response = cli.probe.resetMeasurement()

    # Grab the probe sample rate
    finished = exit_requested()

    # Loop through each sensor and retrieve the calibration data
    while not finished:

        # take a measurement
        cli.listen_for_a_reading()

        # Collect and build the data
        raw_sensor = cli.grab_data(data_request='rawsensor')
        baro_depth = cli.grab_data(data_request='filtereddepth')
        acceleration = cli.grab_data(data_request='rawacceleration')

        ts = build_high_resolution_data(raw_sensor, baro_depth, acceleration, log)
        meta = cli.probe.getProbeHeader()

        # Attempt to get a fix, if no gps cnx then no location data is returned
        location = gps.get_fix()
        if location is not None:
            meta['Latitude'] = location[0]
            meta['Longitude'] = location[1]
        # if a gps exists but were not able to get a fix, report back.
        elif location is None and gps.cnx is not None:
            log.warning("Unable to get GPS fix")
            meta['Latitude'] = 'N/A'
            meta['Longitude'] = 'N/A'
        # Output the data to a datetime file
        filename = cli.write_probe_data(ts, extra_meta=meta)

        # Plot the data
        plot_hi_res(fname=filename, calibration_dict=calibration, timed_plot=args.plot_time)

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
