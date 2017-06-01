from setuptools import setup, find_packages

import os

setup(
    name         = 'bliss-core',
    version      = '0.16.1',
    packages     = ['bliss.core', 'bin'],
    author       = 'BLISS-Core Development Team',
    author_email = 'bliss@jpl.nasa.gov',

    namespace_packages   = ['bliss'],
    include_package_data = True,

    package_data = {
        'bliss.core': ['data/*.json']
    },

    install_requires = [
        'bottle==0.12.9',
        'docopt==0.6.2',
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
            '{}=bin.{}:main'.format(
                f.split('.')[0].replace('_', '-'),
                f.split('.')[0])
            for f in os.listdir('./bin') if f.endswith('.py')
        ]
    }
)
