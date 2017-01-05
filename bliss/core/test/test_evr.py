#!/usr/bin/env python2.7

# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

import nose
import nose.tools

import bliss
from bliss.core import evr


class TestEVRReader(object):
    def test_filename(self):
        reader = evr.EVRReader(filename=evr.getDefaultDictFilename())
        assert reader.filename == evr.getDefaultDictFilename()

    def test_default_filename(self):
        reader = evr.EVRReader()
        assert reader.filename == evr.getDefaultDictFilename()

def test_evr_load():
    evr_dicts = evr.getDefaultDict()
    assert len(evr_dicts) == 4

    count = 1
    for e in evr_dicts:
        assert e.code == count
        count += 1

    assert evr_dicts[0].name == "NO_ERROR"

def test_evr_message_format_single_formatter():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts[0]
    example.message = "Unexpected length for %c command."
    exclamation = bytearray([0x21])

    expected = "Unexpected length for ! command."
    result = example.format_message(exclamation)

    assert result == expected

def test_evr_message_format_multiple_formatters():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts[0]
    example.message = "Unexpected length for %c command %s and %d."
    input_data = bytearray([0x21, 0x46, 0x6f, 0x6f, 0x00, 0xff, 0x11, 0x33, 0x44])

    expected = "Unexpected length for ! command Foo and 4279317316."
    result = example.format_message(input_data)

    assert result == expected

def test_evr_no_formatters_found():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts[0]
    input_data = bytearray([0x21])
    example.message = "%M this formatter doesn't exist"
    result = example.format_message(input_data)

    assert result == example.message

def test_bad_formatter_parsing():
    evr_dicts = evr.getDefaultDict()
    example = evr_dicts[0]
    example.message = "Unexpected length for %c command %s and %d."
    input_data = bytearray([0x21])
    msg = "Unable to format EVR Message with data {}".format(input_data)

    try:
        result = example.format_message(input_data)
        assert False
    except ValueError as e:
        assert e.message == msg
        assert True
