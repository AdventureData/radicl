"""
This script shows the simplicity of using the radicl framework to access
settings information from the Lyte Probe.

In this example, the probe calibration values for each sensor are on already on
the probe. This script retrieves, sets, reports them. Modifiying the settings
is done using the  `getSetting` and `setSetting` functions using the setting
name 'calibdata' which is short hand for calibration data.

Usage:  1. plug in the probe.
        2. Open a terminal
        3. python get_calibrated_data.py

"""

# Import the radicl probe class
from radicl.probe import RAD_Probe

# Import the colored logging from radicl to report more human readable info
from radicl.ui_tools import get_logger

# Instantiate the interface
probe = RAD_Probe()

# Start this scripts logging
log = get_logger(__name__, debug=True)

# Loop through each sensor and retrieve the calibration data
log.info("Retrieving the calibration values for each sensor...")
for sensor in range(1, 5):
    # Grab setting data
    d = probe.getSetting(setting_name='calibdata', sensor=sensor)

    # Report data without decimals
    log.info("Sensor {}: LOW = {:0.0f}, HIGH = {:0.0f}\n".format(sensor, d[0], d[1]))
