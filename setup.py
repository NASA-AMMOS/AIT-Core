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

from setuptools import setup, find_packages

import os

setup(
    name         = 'bliss-core',
    version      = '0.28.0',
    packages     = find_packages(exclude=['tests']),
    author       = 'BLISS-Core Development Team',
    author_email = 'bliss@jpl.nasa.gov',

    namespace_packages   = ['bliss'],
    include_package_data = True,

    package_data = {
        'bliss.core': ['data/*.json']
    },

    install_requires = [
        'bottle==0.12.9',
        'jsonschema==2.5.1',
        'pyyaml==3.11',
        'requests==2.9.1',
        'gevent==1.1.2',
        'gevent-websocket==0.9.5',
    ],

    extras_require = {
        'docs':  [
            'Sphinx==1.4',
            'sphinx_rtd_theme',
            'sphinxcontrib-httpdomain'
        ],
        'tests': [
            'nose',
            'coverage',
            'mock',
            'pylint'
        ],
    },

    entry_points = {
        'console_scripts': [
            '{}=bliss.core.bin.{}:main'.format(
                f.split('.')[0].replace('_', '-'),
                f.split('.')[0])
            for f in os.listdir('./bliss/core/bin')
            if f.endswith('.py') and
            f != '__init__.py'
        ]
    }
)
