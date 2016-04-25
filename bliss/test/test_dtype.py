#!/usr/bin/env python

"""
OCO-3 Data Type Unit Tests

Provides unit and functional tests for the bliss.dtype module.
Assumes these tests will be run in POSIX environment.
"""

"""
Authors: Jordan Padams

Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""

import base64
import binascii
import datetime
import struct

import nose
import bliss


def testEVR32():
    """Test EVR32 complex data type"""
    dtype = bliss.dtype.EVRType()
    code = 0
    name = "NO_ERROR"

    rawdata = bytearray(struct.pack('>I', code))

    assert dtype.decode(rawdata) == name
    assert dtype.encode(name) == rawdata


def testTIME8():
    """Test TIME8 complex data type"""
    dtype = bliss.dtype.Time8Type()
    fine = 17
    rawdata = bytearray(struct.pack('B', fine))

    expected = fine/256.0
    #print expected

    assert dtype.decode(rawdata) == expected
    assert dtype.encode(expected) == rawdata


def testTIME32():
    """Test TIME32 complex data type"""
    dtype = bliss.dtype.Time32Type()
    sec = 1113733097

    rawdata = bytearray(struct.pack('>I', sec))
    date = datetime.datetime(2015, 4, 22, 10, 18, 17)

    assert dtype.decode(rawdata) == date
    assert dtype.encode(date) == rawdata


def testTIME40():
    """Test TIME40 complex data type"""
    dtype = bliss.dtype.Time40Type()
    sec = 1113733097
    fine = 8

    # get raw data ready
    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('B', fine))

    # get the expected date
    date = datetime.datetime(2015, 4, 22, 10, 18, 17)

    # get expected fine string
    fine_exp = fine/256.0
    fine_str = ('%f' % fine_exp).lstrip('0')

    # concatenate the expcted datetime value
    expected = ('%s%s' % (date, fine_str))

    #print dtype.decode(rawdata)
    assert dtype.decode(rawdata) == expected
    assert dtype.encode(expected) == rawdata


def testTIME64():
    """Test TIME64 complex data type"""
    dtype = bliss.dtype.Time64Type()
    sec = 1113733097
    subsec = 10
    
    #print (sec << 32) | subsec
    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('>I', subsec))

    date = datetime.datetime(2015, 4, 22, 10, 18, 17)
    date = '%s.%010d' % (date, subsec)

    assert dtype.decode(rawdata) == date
    assert dtype.encode(date) == rawdata


def testgetdtype():
    dtype = bliss.dtype.get("TIME32")
    assert isinstance(dtype, bliss.dtype.Time32Type)
    assert dtype.name == "TIME32"
    assert dtype.pdt == "MSB_U32"
    assert dtype.max == 4294967295


def testget():
    dtype = bliss.dtype.get("U8")
    assert isinstance(dtype, bliss.dtype.PrimitiveType)

    dtype = bliss.dtype.get("S40")
    assert isinstance(dtype, bliss.dtype.PrimitiveType)

    dtype = bliss.dtype.get("TIME32")
    assert isinstance(dtype, bliss.dtype.Time32Type)


if __name__ == '__main__':
    nose.main()
