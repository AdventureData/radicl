# coding: utf-8

import os
import time
import numpy as np

from radicl.ui_tools import get_logger


def get_avg_sensor(probe, delay=3, sensor='Sensor1'):
    """
    Take a probe measurement of 3 seconds and return the mean of that data.

    Args:
        probe: radicl.probe.RAD_Probe object
        delay: Measurement time in seconds
        sensor: String name of the column of the data to avg
    Returns:
        probe_data: Mean of the Raw Sensor over the delay time period
    """
    log = get_logger(__name__)

    # Start the probe
    probe.startMeasurement()
    log.info("\tProbe measurement started...")
    time.sleep(delay)

    # Stop probe
    probe.stopMeasurement()
    log.info("Measurement Stopped.")

    # Probe data extraction and average
    probe_data = np.array((probe.readRawSensorData())[sensor])
    probe_data = probe_data[probe_data < 4096].mean()

    # Start the reset in another thread
    probe.resetMeasurement()

    # If we like the data
    if probe_data in [None, 65535]:
        log.error("Probe data invalid! Trying again")

    return int(probe_data)


if __name__ == '__main__':
    main()
