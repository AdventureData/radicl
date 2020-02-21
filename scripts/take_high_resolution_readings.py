"""
This script shows the simplicity of using the radicl framework to access
settings information from the Lyte Probe.

This example the script collects the full calibrated signal from the probe
in addition to the depth data, allowing for high resolution profiles

Usage:  1. plug in the probe.
        2. Open a terminal
        3. python take_high_resolution_readings.py

"""

# import a number crunching library
import numpy as np

# Import the radicl probe class
from radicl.radicl import RADICL

# Import the colored logging from radicl to report more human readable info
from radicl.ui_tools import get_logger

from plot_hi_res import plot_hi_res
import matplotlib.pyplot as plt

# Start this scripts logging
log = get_logger("Hi-Res Script", level='DEBUG')

finished = False
log.info("Starting High Resolution DAQ Script")
cli = RADICL()
i = 0
response = cli.probe.resetMeasurement()

# Loop through each sensor and retrieve the calibration data
while not finished:

    # take a measurment
    input("\nPress enter to start listening for the probe to start...\n")
    print("Press probe button to start...")
    cli.listen_for_a_reading()

    # Grab the calibrated, raw sensor and the filtereddepth
    ts = cli.grab_data('calibratedsensor')
    #rts = cli.grab_data('rawsensor')
    depth = cli.grab_data('filtereddepth')

    # Upsample the depth data
    log.info("Interpolating depth data...")
    ndepth = len(depth.index)
    nsamples = len(ts.index)
    new_data = np.zeros_like(ts['Sensor1'].values).astype(np.float64)
    # Set it on zero
    depth['filtereddepth'] = depth['filtereddepth'] - depth['filtereddepth'].min()
    # Invert it so bottom is negative max depth
    depth['filtereddepth'] = depth['filtereddepth'] - depth['filtereddepth'].max()
    # Convert to meters
    depth['filtereddepth'] = depth['filtereddepth'].div(100)

    # Replace zeros with nans
    new_data[new_data==0] = np.NaN

    iz = 0
    ratio = nsamples/ndepth

    # Repopulate around the nans
    for ii in np.arange(ndepth):
        if ii != 0:
            iz = int(ii * ratio)
        new_data[iz] = depth['filtereddepth'].iloc[ii]

    # Calculate the min
    min_depth = np.nanmin(new_data)

    # Assign the data
    ts['depth'] = new_data.copy()
    ts['depth'] = ts['depth'].interpolate()
    ts = ts.set_index('depth')

    plot_hi_res(ts)

    # ouptut the data to a datetime file
    cli.write_probe_data(ts, filename='')
    response = cli.probe.resetMeasurement()

    i+=1
    log.info("{} measurements taken this session".format(i))
