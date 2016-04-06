from setuptools import setup, find_packages

import os

PROJECT_BIN_PATH = "./bin"
SRC_PATH = "src/python"
with open("./requirements.txt") as in_file:
    REQUIREMENTS_LIST = in_file.read().splitlines()

setup(
    name = "bliss-core",
    version = "0.1",
    packages = find_packages(where=SRC_PATH),

    scripts = [
        os.path.join(PROJECT_BIN_PATH, f)
        for f in os.listdir(PROJECT_BIN_PATH)
    ],

    install_requires = REQUIREMENTS_LIST,

    package_dir = {"": SRC_PATH},

    author = "BLISS-Core Development Team",
    author_email = "Benjamin.J.Bornstein@jpl.nasa.gov",
)
