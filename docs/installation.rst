.. highlight:: shell

============
Installation
============

Windows Prerequisites
---------------------

You will need to install python 3.6+ and the RAD Drivers for your probe to
work on Windows 10.

Python installation
~~~~~~~~~~~~~~~~~~~

It is preferable to use your Windows Store to install your python. You can
search by python.

1. Go to you Windows App Store and search `python`, pick the version you want.
2. Run the installer, making sure to enable the `Add Python 3.X to path`
   this option shows up when you first start the installer see below:

   .. image:: images/windows_python_installer.png
        :width: 400px
        :align: center
        :alt: Enable python path on windows

  **Warning:** If you don't enable this option the radicl cli tool will not be available.
  If you miss enabling it you can always rerun the install and select repair to
  get the option to enable it again.

3. Check the install by opening up powershell and running:

   .. code-block:: powershell

    python --version

   Which should print out some thing like:

   .. code-block:: powershell

      >> Python 3.8.10

4. Check that you have the correct `pip` associated by running:

   If this is version number is 3.6+ Then you are set to continue on to the
   driver install portion of this guide.

   .. code-block:: powershell

     pip --version

   This should also print which python version it is using. This should exactly
   match the version installed above. If it does not, you will have to use `pip3.X`
   to install the python packages later.

5. If everything works as expected, continue on to the drivers installation guide


RAD Drivers Install
~~~~~~~~~~~~~~~~~~~

**Windows will not automatically find drivers for the Lyte probe**. Follow the
instructions below to install them.

1. Download Drivers from `RAD Drivers`_

.. _RAD Drivers: https://drive.google.com/file/d/18t1XQvWoSRbmwd9GQrSo6ij6BaIVpXsY/view?usp=sharing

2. Unzip the folder
3. Run the VCP_V1.4.0_Setup.exe in the folder
4. Navigate to C:\Program Files (x86)\STMicroelectronics\Software\Virtual comport driver/Win8
5. Run dpinst_amd64.exe (for 64 bit machines)
6. Confirm the install by opening the device manager. Expand the
   `Ports (COM & LPT)`, if you installed the drivers correct you should see a
   device labeled `STMicroeletronics Virtual Com Port` with out any error
   symbols. If it failed, you will see two associated devices one labeled with interface.

If you have correctly installed the drivers move on to the radicl installation
below.


Linux -Ubuntu Prerequisites
---------------------------

* Python 3.6+
* TKinter

Installing TKinter on Ubuntu:

.. code-block:: console

  sudo apt-get install python3-tk


If you get permission denied in the
error when first using radicl you may need to add:

.. code-block:: console

  groups ${USER}
  sudo gpasswd --add ${USER} dialout

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


Install radicl
--------------

Installing radicl depends on your end use:
  1. Installing to only take measurements, Follow instruction to :ref:`Install radicl for Users Only`.
  2. Installing to develop radicl source code, Follow instructions to :ref:`Install radicl for Developers`.

.. _Install radicl for Users Only:
Install radicl for Users Only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install the latest stable release of radicl by running this command in your terminal:

.. code-block:: console

    pip install radicl

2. Test the installation by, plugging in your probe to the computer, open a
   terminal/powershell and run:

   .. code-block:: console

      radicl

   This should show some logging statements saying that your probe was found and
   present you with a question that says:

   .. code-block:: console

      What do you want to do with the probe? (daq, settings, update, help, exit)


**Once you have completed the setup, head over to** :ref:`Usage` **to see what
tools are available to you!**

.. _Install radicl for Developers:
Install radicl for Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sources for radicl can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/AdventureData/radicl

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/AdventureData/radicl/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/AdventureData/radicl
.. _tarball: https://github.com/AdventureData/radicl/tarball/master
