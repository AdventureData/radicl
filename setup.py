#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('docs/history.rst', encoding='utf-8') as history_file:
    history = history_file.read()

with open('./requirements_dev.txt', encoding='utf-8') as req_file:
    requirements = req_file.read()

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Micah Johnson",
    author_email='micah@adventuredata.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Command line interface to the Realtime Adventure Data Lyte probe for measuring avalanche conditions",
    install_requires=requirements,
    license="BSD license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='radicl',
    name='radicl',
    packages=find_packages(include=['radicl']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/adventuredata/radicl',
    version='0.2.5',
    zip_safe=False,
    scripts = ['scripts/plotlyte',],
     entry_points = {
          'console_scripts': [
              'radicl = radicl.cli:main',
          ],
      },
)
