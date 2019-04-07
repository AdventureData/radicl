.. highlight:: shell

============
Installation
============

Prerequisites
--------------

* Python 3.5+
* TKinter
* Lyte probe

Installing TKinter on Ubuntu:

.. code block:: console

  sudo apt-get install python3-tk


If on Ubuntu you get permission denied in the
error when first using radicl you may need to add:

.. code block:: console

  groups ${USER}
  sudo gpasswd --add ${USER} dialout

Stable release
--------------

To install radicl, run this command in your terminal:

.. code-block:: console

    $ pip install radicl

This is the preferred method to install radicl, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

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
