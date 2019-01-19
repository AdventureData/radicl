=====
Usage
=====

To use the command line program simple the following in a command prompt::

  radicl


To use radicl in a project::


    from radicl.radicl import RADICL

    cli = radicl.radicl.RADICL()
    probe = cli.probe


The following is a simple data acquisition script::


    from radicl.radicl import RADICL

    cli = radicl.radicl.RADICL()
    probe = cli.probe

    # Confirm the probe is ready
    probe.resetMeasurement()

    # Start the probe
    probe.startMeasurement()

    # Wait for the probe to acknowledge a measurement started
    probe.wait_for_state(1)

    # Delay some time
    time.sleep(2)

    # Stop Measurment
    probe.stopMeasurement()

    # Wait for processing
    probe.wait_for_state(3)

    # Accelerometer data extract
    accel_data = probe.readRawAccelerationData()

The probe has a lot of data that can be pulled from it. If you would like
to see what options are available please see: 
