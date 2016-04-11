from setuptools import setup, find_packages

import os

PROJECT_BIN_PATH = "./bin"
SRC_PATH = "src/python"

setup(
    name = "bliss-core",
    version = "0.1",
    packages = find_packages(where=SRC_PATH),

    scripts = [
        os.path.join(PROJECT_BIN_PATH, f)
        for f in os.listdir(PROJECT_BIN_PATH)
    ],

    install_requires = [
        'nose==1.3.7',
        'bottle==0.12.9',
        'coverage',
        'docopt==0.6.2',
        'gevent-websocket==0.9.5',
        'gevent==1.0.2',
        'greenlet==0.4.9',
        'jsonschema==2.5.1',
        'pyyaml==3.11',
        'requests==2.9.1',
        'Sphinx==1.4',
    ],

    package_dir = {"": SRC_PATH},

    author = "BLISS-Core Development Team",
    author_email = "Benjamin.J.Bornstein@jpl.nasa.gov",
)
