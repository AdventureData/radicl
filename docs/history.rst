=======
History
=======

Initial Development (2016-12-14)
--------------------------------

* Parse incoming strings from the command prompt including data
* Only plotted data

Overhaul (2017-10-17)
---------------------

* Made into a package
* Made into a nice CLI
* Expanded data acquisition
* Plots and saves data

0.1.0 (2019-01-18)
------------------

* First release on PyPI.
* Opensourced!

0.2.0 (2019-01-19)
------------------

* Full daq system
* Complete API
* Documentation
* Complete access to the Lyte probe

0.3.0 (2020-01-22)
------------------

* Improvements to the firmware updating process
* General API fixes
* Starting unittests


0.4.0 (2020-02-29)
------------------
* Fix for issue 6_
* Added in a high resolution daq script.
* Added linting with autopep8 and isort
* Resilience improvements to grabbing data
* Added back in the listening function for measurements via buttons

.. _6: https://github.com/AdventureData/radicl/issues/6

0.5.0 (2021-11-30)
------------------
* Fixes for issues 4_, 8_, 9_, 15_, 16_, 18_, 19_
* Migrated towards Github Actions
* Added broader build tests
* Improved data downloading/logging and integrity checks
* Improved tools for high resolution measurements
* Improved documentation on setup, install, and usage

.. _4: https://github.com/AdventureData/radicl/issues/4
.. _8: https://github.com/AdventureData/radicl/issues/8
.. _9: https://github.com/AdventureData/radicl/issues/9
.. _15: https://github.com/AdventureData/radicl/issues/15
.. _16: https://github.com/AdventureData/radicl/issues/16
.. _18: https://github.com/AdventureData/radicl/issues/18
.. _19: https://github.com/AdventureData/radicl/issues/19

0.6.0 (2022-04-25)
------------------
* Fixes for issue 26_
* Working toward most of 25_
* Loosen requirements for packages
* Incorporating Study Lyte package
* Improved plotting interface for hi res measurement
* Fixed major bug in interpolation scheme in high res
* Added tests mocking high res ops

.. _25: https://github.com/AdventureData/radicl/issues/25
.. _26: https://github.com/AdventureData/radicl/issues/26


0.7.0 (2023-01-28)
------------------
* Fixes for issue 31_
* Added auto closing of plots 25_
* Added more tests and python 3.11
* Rearranged project structure to be more editor friendly
* Added plot time and repeat measurements to hi res script
* Updated installation docs

.. _25: https://github.com/AdventureData/radicl/issues/25
.. _31: https://github.com/AdventureData/radicl/issues/31
