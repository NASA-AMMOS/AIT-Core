# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import io
from os import path
from setuptools import setup, find_packages
from setuptools.command.develop import develop

import os
import shutil

description = "Python-based software suite developed to handle Ground Data System (GDS), " \
              "Electronic Ground Support Equipment (EGSE), commanding, telemetry uplink/downlink, " \
              "and sequencing for JPL International Space Station and CubeSat Missions"

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with io.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name         = 'ait-core',
    version      = '2.3.5',
    description  = description,
    long_description = long_description,
    long_description_content_type = 'text/x-rst',
    url          = 'https://github.com/NASA-AMMOS/AIT-Core',
    packages     = find_packages(exclude=['tests']),
    author       = 'AMMOS Instrument Toolkit Development Team',
    author_email = 'ait-pmc@googlegroups.com',

    namespace_packages   = ['ait'],
    include_package_data = True,

    package_data = {
        'ait.core': ['data/*.json']
    },

    install_requires = [
        'bottle==0.12.17',
        'jsonschema==3.0.2',
        'pyyaml==5.1.2',
        'requests>=2.22.0',
        'greenlet==0.4.16',
        'gevent==1.4.0',
        'gevent-websocket==0.10.1',
        'pyzmq==18.1.0',
    ],

    extras_require = {
        'dev': [
            "black",
            "flake8",
            "flake8-bugbear",
            "pep8-naming",
            "mypy",
            "types-PyYAML",
            "types-requests",
            "types-setuptools",
            "pydocstyle",
            "coverage",
            "pytest",
            "pytest-cov",
            "pytest-watch",
            "pytest-xdist",
            "pre-commit",
            "sphinx",
            "sphinx-rtd-theme",
            'sphinxcontrib-httpdomain',
            "tox"
        ]
    },

    entry_points = {
        'console_scripts': [
            '{}=ait.core.bin.{}:main'.format(
                f.split('.')[0].replace('_', '-'),
                f.split('.')[0])
            for f in os.listdir('./ait/core/bin')
            if f.endswith('.py') and
            f != '__init__.py'
        ]
    },
)
