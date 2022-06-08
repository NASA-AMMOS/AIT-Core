# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2022, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""AIT Unit and Functional Tests"""
import logging


def setUp():
    """
    Set up tests:
        Turn logging level to CRITICAL: due to failure test cases, there
        are many verbose log messages that are useful in context.
    """
    logging.getLogger("ait").setLevel(logging.CRITICAL)


def tearDown():
    """
    Tear down tests:
        Turn logging level back to INFO.
    """
    logging.getLogger("ait").setLevel(logging.INFO)
