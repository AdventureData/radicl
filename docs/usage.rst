=====
Usage
=====
Using radicl to interact with your Lyte probe has been made easy by the
developers here at Adventure Data. Simply connect the probe via USB, wait for
about a minute. Then you are ready to go.

There are two ways to use radicl:
1. Through the interactive CLI program called radicl.
2. By writing your own python script importing radicl to get the data you want.

Interactive CLI
---------------
To use the command line program called radicl, simple the following in a command prompt::

  radicl

There you will be asked a series of questions it will eventually navigate you
to a loop for data acquisition. Should you ever need help, you can always enter
help in the answer to get a description of what the options mean.

The best advantage to radicl is the ease to change settings, and quickly look
at data. This makes it a great way to test an experimental setup.

*The key limitation with using radicl interactively is that right now you can
only pull one dataset off at a time per measurement*. This means you will only
get time series measurements!

Using lyte_hi_res
------------------

To receive full functioning datasets from the probe for reconstructing a
profile of the snowpack use::
  lyte_hi_res

This script provides a simple daq interface for retrieving enough data to
reconstruct a profile of the snow. To do this this script will download the
following timeseries per measurement:

* Hardness
* Active NIR
* Passive NIR
* Depth from Barometer
* Acceleration in 3 Axes.

This script will auto-resize the data sets so they are the same size in the
number of samples. This is achieved using linear interpolation. All datsets are
sized to match the sensors in the probe tip which are the highest in sample rate
by default.

The script will also save the data to a CSV using a datetime filename.
Each file is stamped with a header containing

* Recording time to the second.
* radicl version
* Probe firmware, hardware, and model information.

The file will be saved in the same directory that the script was executed in.


Python Scripting
----------------

If you want to pull your own custom set(s) of data from the probe you are
going to want to write a script.

The following is a simple data acquisition script:

.. code-block:: python

    from radicl.interface import RADICL

    # Instantiate the CLI
    cli = RADICL()

    # Isolate the probe for ease of use
    probe = cli.probe

    # Confirm the probe clear of previous data
    probe.resetMeasurement()

    cli.take_a_reading()

    # Extract raw data as a dataframe
    data = cli.grab_data('rawsensor')

    # Save the data
    cli.write_probe_data(data)

The above script will allow a user to :

* Start and stop a measurement via the key board (pressing enter)
* Extract the data as a pandas dataframe
* Save the data with important headers to a simple csv

Please note that not all the datasets retrievable from the probe are measured
with the same sampling rate so some resampling methods may needed to merge
datasets if you want to save them to a single file.
