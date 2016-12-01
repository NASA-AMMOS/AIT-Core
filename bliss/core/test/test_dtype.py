#!/usr/bin/env python2.7

# Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import base64
import binascii
import datetime
import struct

import nose

from bliss.core import dtype


def testEVR16():
    """Test EVR16 complex data type"""
    dt   = dtype.EVRType()
    code = 0x0000
    name = "NO_ERROR"

    rawdata = bytearray(struct.pack('>H', code))

    assert dt.decode(rawdata) == name
    assert dt.encode(name)    == rawdata


def testTIME8():
    """Test TIME8 complex data type"""
    dt      = dtype.Time8Type()
    fine    = 17
    rawdata = bytearray(struct.pack('B', fine))

    expected = fine/256.0

    assert dt.decode(rawdata)  == expected
    assert dt.encode(expected) == rawdata


def testTIME32():
    """Test TIME32 complex data type"""
    dt  = dtype.Time32Type()
    sec = 1113733097

    rawdata = bytearray(struct.pack('>I', sec))
    date    = datetime.datetime(2015, 4, 22, 10, 18, 17)

    assert dt.decode(rawdata) == date
    assert dt.encode(date)    == rawdata


def testTIME40():
    """Test TIME40 complex data type"""
    dt   = dtype.Time40Type()
    sec  = 1113733097
    fine = 8

    # get raw data ready
    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('B', fine))

    # get the expected date
    date = datetime.datetime(2015, 4, 22, 10, 18, 17)

    # get expected fine string
    fine_exp = fine / 256.0
    fine_str = ('%f' % fine_exp).lstrip('0')

    # concatenate the expcted datetime value
    expected = ('%s%s' % (date, fine_str))

    assert dt.decode(rawdata)  == expected
    assert dt.encode(expected) == rawdata


def testTIME64():
    """Test TIME64 complex data type"""
    dt     = dtype.Time64Type()
    sec    = 1113733097
    subsec = 10
    
    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('>I', subsec))

    date = datetime.datetime(2015, 4, 22, 10, 18, 17)
    date = '%s.%010d' % (date, subsec)

    assert dt.decode(rawdata) == date
    assert dt.encode(date)    == rawdata


def testgetdtype():
    dt = dtype.get("TIME32")
    assert isinstance(dt, dtype.Time32Type)
    assert dt.name == "TIME32"
    assert dt.pdt  == "MSB_U32"
    assert dt.max  == 4294967295


def testget():
    assert isinstance( dtype.get("U8")    , dtype.PrimitiveType )
    assert isinstance( dtype.get("S40")   , dtype.PrimitiveType )
    assert isinstance( dtype.get("TIME32"), dtype.Time32Type    )


if __name__ == '__main__':
    nose.main()
