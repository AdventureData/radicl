#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('docs/history.rst', encoding='utf-8') as history_file:
    history = history_file.read()

with open('./requirements.txt', encoding='utf-8') as req_file:
    requirements = req_file.read()

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Micah Johnson",
    author_email='info@adventuredata.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description="Command line interface to the Realtime Adventure Data Lyte probe for measuring avalanche conditions",
    install_requires=requirements,
    license="BSD license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='radicl',
    name='radicl',
    packages=find_packages(include=['radicl', 'radicl.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/adventuredata/radicl',
    version='0.7.0',
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'radicl = radicl.cli:main',
            'plotlyte = radicl.plotting:main',
            'lyte_hi_res = radicl.high_resolution:main',
            'plot_hi_res = radicl.plotting:plot_hi_res_cli',
        ],
    },
)
