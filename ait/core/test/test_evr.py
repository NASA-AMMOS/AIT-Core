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
    example.message = "Unexpected length for %c command %s and %u."
    input_data = bytearray([0x21, 0x46, 0x6f, 0x6f, 0x00, 0xff, 0x11, 0x33, 0x44])

    expected = "Unexpected length for ! command Foo and 4279317316."
    result = example.format_message(input_data)

    assert result == expected

def test_evr_message_format_complex_formatters():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]
    example.message = "Unexpected length for %c command %s and %llu."
    input_data = bytearray([0x21, 0x46, 0x6f, 0x6f, 0x00, 0x80, 0x00, 0x00, 0x00, 0xff, 0x11, 0x33, 0x44])

    expected = "Unexpected length for ! command Foo and 9223372041134093124."
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

def test_standard_formatter_handling():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]

    example.message = '%c'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '\x01'

    example.message = '%d'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '16909060'

    example.message = '%u'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '16909060'

    example.message = '%i'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '16909060'

    example.message = '%x'
    result = example.format_message(bytearray([0x00, 0x00, 0x00, 0x0f]))
    assert result == 'f'

    example.message = '%X'
    result = example.format_message(bytearray([0x00, 0x00, 0x00, 0x0f]))
    assert result == 'F'

    example.message = '%f'
    result = example.format_message(bytearray([
        0x40, 0x5E, 0xDC, 0x14, 0x5D, 0x85, 0x16, 0x55
    ]))
    assert result == '123.438743'

    example.message = '%e'
    result = example.format_message(bytearray([
        0x40, 0x5E, 0xDC, 0x14, 0x5D, 0x85, 0x16, 0x55
    ]))
    assert result == '1.234387e+02'

    example.message = '%E'
    result = example.format_message(bytearray([
        0x40, 0x5E, 0xDC, 0x14, 0x5D, 0x85, 0x16, 0x55
    ]))
    assert result == '1.234387E+02'

    example.message = '%g'
    result = example.format_message(bytearray([
        0x40, 0x5E, 0xDC, 0x14, 0x5D, 0x85, 0x16, 0x55
    ]))
    assert result == '123.439'

def test_complex_formatter_handling():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts.codes[1]

    example.message = '%hhu'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '1'

    example.message = '%hu'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '258'

    example.message = '%lu'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '16909060'

    example.message = '%llu'
    result = example.format_message(
        bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    assert result == '72623859790382856'
