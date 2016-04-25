"""
BLISS Unit and Functional Tests

The bliss.test module provides functional and unit tests for bliss modules.
"""

"""
Authors: Ben Bornstein, Jordan Padams

Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import os
import warnings


class TestFile:
    """TestFile

    TestFile is a Python Context Manager for quickly creating test
    data files that delete when a test completes, either successfully
    or unsuccessfully.

    Example:

        with TestFile(data) as filename:
            # filename (likely something like '/var/tmp/tmp.1.uNqbVJ') now
            # contains data.
            assert load(filename)

    Whether the above assert passes or throws AssertionError, filename
    will be deleted.
    """

    def __init__ (self, data):
        """Creates a new TestFile and writes data to a temporary file."""
        self._filename = None

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._filename = os.tmpnam()

        with open(self._filename, 'wt') as output:
            output.write(data)


    def __enter__ (self):
        """Enter the runtime context and return filename."""
        return self._filename


    def __exit__ (self, exc_type, exc_value, traceback):
        """Exit the runtime context and delete filename."""
        os.remove(self._filename)
