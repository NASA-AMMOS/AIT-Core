#!/usr/bin/env python2.7

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2015, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import nose
import nose.tools

import ait
from ait.core import evr


def test_evr_load():
    evr_dicts = evr.getDefaultDict()
    assert len(evr_dicts.keys()) == 4

    assert evr_dicts.codes[1].name == "NO_ERROR"

def test_evr_message_format_single_formatter():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]
    example.message = "Unexpected length for %c command."
    exclamation = bytearray([0x21])

    expected = "Unexpected length for ! command."
    result = example.format_message(exclamation)

    assert result == expected

def test_evr_message_format_multiple_formatters():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]
    example.message = "Unexpected length for %c command %s and %d."
    input_data = bytearray([0x21, 0x46, 0x6f, 0x6f, 0x00, 0xff, 0x11, 0x33, 0x44])

    expected = "Unexpected length for ! command Foo and 4279317316."
    result = example.format_message(input_data)

    assert result == expected

def test_evr_no_formatters_found():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]
    input_data = bytearray([0x21])
    example.message = "%M this formatter doesn't exist"
    result = example.format_message(input_data)

    assert result == example.message

def test_bad_formatter_parsing():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]
    example.message = "Unexpected length for %c command %s and %d."
    input_data = bytearray([0x21])
    msg = "Unable to format EVR Message with data {}".format(input_data)

    try:
        result = example.format_message(input_data)
        assert False
    except ValueError as e:
        assert e.message == msg
        assert True
