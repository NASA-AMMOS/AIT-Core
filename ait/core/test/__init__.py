# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2014, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
AIT Unit and Functional Tests

The ait.test module provides functional and unit tests for ait modules.
"""

import os
import warnings
import logging

import ait
import ait.core


ait.config.reload('data/config/config.yaml')

def setUp():
    """Set up tests.

    Turn logging level to CRITICAL: due to failure test cases, there
    are many verbose log messages that are useful in context.
    """
    logging.getLogger('ait').setLevel(logging.CRITICAL)

def tearDown():
    """Tear down tests.

    Turn logging level back to INFO.
    """
    logging.getLogger('ait').setLevel(logging.INFO)


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
