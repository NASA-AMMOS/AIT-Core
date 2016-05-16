from setuptools import setup, find_packages

import os

setup(
    name         = 'bliss-core',
    version      = '0.1',
    packages     = [ 'bliss' ],
    author       = 'BLISS-Core Development Team',
    author_email = 'bliss@jpl.nasa.gov',

    include_package_data = True,

    scripts = [
        os.path.join('./bin', f) for f in os.listdir('./bin')
    ],

    install_requires = [
        'bottle==0.12.9',
        'docopt==0.6.2',
        'jsonschema==2.5.1',
        'pyyaml==3.11',
        'requests==2.9.1',
    ],

    extras_require = {
        'docs':  ['Sphinx==1.4', 'sphinx_rtd_theme'],
        'tests': ['nose', 'coverage', 'mock'],
    }
)
