#!/usr/bin/env python2.7

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

import base64
import binascii
import datetime
import struct

import nose
import nose.tools

from ait.core import dtype


def fpeq (p, q, eps=1e-6):
    return abs(p - q) < eps


def testLSB_D64():
    val     = 1.2
    bytes   = struct.pack('<d', val)
    LSB_D64 = dtype.get('LSB_D64')

    assert fpeq(LSB_D64.decode(bytes), val)
    assert fpeq(LSB_D64.decode(bytes, raw=True), val)


def testMSB_D64():
    val     = 3.4
    bytes   = struct.pack('>d', val)
    MSB_D64 = dtype.get('MSB_D64')

    assert fpeq(MSB_D64.decode(bytes), val)
    assert fpeq(MSB_D64.decode(bytes, raw=True), val)


def testLSB_F32():
    val     = 5.6
    bytes   = struct.pack('<f', val)
    LSB_F32 = dtype.get('LSB_F32')

    assert fpeq(LSB_F32.decode(bytes), val)
    assert fpeq(LSB_F32.decode(bytes, raw=True), val)


def testMSB_F32():
    val     = 7.8
    bytes   = struct.pack('>f', val)
    MSB_F32 = dtype.get('MSB_F32')

    assert fpeq(MSB_F32.decode(bytes), val)
    assert fpeq(MSB_F32.decode(bytes, raw=True), val)


def testArrayType():
    array  = dtype.ArrayType('MSB_U16', 3)
    bin123 = '\x00\x01\x00\x02\x00\x03'
    bin456 = '\x00\x04\x00\x05\x00\x06'

    assert array.name   == 'MSB_U16[3]'
    assert array.nbits  == 3 * 16
    assert array.nbytes == 3 *  2
    assert array.nelems == 3
    assert array.type   == dtype.PrimitiveType('MSB_U16')

    assert array.encode(1, 2, 3)   == bin123
    assert array.decode(bin456)    == [4, 5, 6]
    assert array.decode(bin456, 0) == 4
    assert array.decode(bin456, 1) == 5
    assert array.decode(bin456, 2) == 6
    assert array.decode(bin456, slice(1, 3)) == [5, 6]

    with nose.tools.assert_raises(ValueError):
        array.encode(1, 2)

    with nose.tools.assert_raises(IndexError):
        array.decode(bin456[1:5])

    with nose.tools.assert_raises(IndexError):
        array.decode(bin456, 3)

    with nose.tools.assert_raises(TypeError):
        array.decode(bin456, 'foo')

    with nose.tools.assert_raises(TypeError):
        dtype.ArrayType('U8', '4')


def testArrayTime8():
    array = dtype.ArrayType('TIME8', 3)
    bytes = '\x40\x80\xC0'

    assert array.decode(bytes)           == [0.25, 0.50, 0.75]
    assert array.decode(bytes, raw=True) == [  64,  128,  192]


def testCMD16():
    dt   = dtype.CmdType()
    code = 0x0001
    name = 'NO_OP'

    rawdata = bytearray(struct.pack('>H', code))

    assert dt.decode(rawdata).name      == name
    assert dt.decode(rawdata, raw=True) == code
    assert dt.encode(name)              == rawdata


def testEVR16():
    dt   = dtype.EVRType()
    code = 0x0001
    name = 'NO_ERROR'

    rawdata = bytearray(struct.pack('>H', code))

    assert dt.decode(rawdata).name      == name
    assert dt.decode(rawdata, raw=True) == code
    assert dt.encode(name)              == rawdata


def testTIME8():
    dt      = dtype.Time8Type()
    fine    = 17
    rawdata = bytearray(struct.pack('B', fine))

    expected = fine / 256.0

    assert dt.decode(rawdata)            == expected
    assert dt.decode(rawdata, raw=True)  == fine
    assert dt.encode(expected)           == rawdata


def testTIME32():
    dt  = dtype.Time32Type()
    sec = 1113733097

    rawdata = bytearray(struct.pack('>I', sec))
    date    = datetime.datetime(2015, 4, 22, 10, 18, 17)

    assert dt.decode(rawdata)           == date
    assert dt.decode(rawdata, raw=True) == sec
    assert dt.encode(date)              == rawdata


def testTIME40():
    dt   = dtype.Time40Type()
    sec  = 1113733097
    fine = 8

    # get raw data ready
    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('B', fine))

    # get the expected date
    expected = datetime.datetime(2015, 4, 22, 10, 18, 17, 31250)

    assert dt.decode(rawdata)            == expected
    assert dt.decode(rawdata, raw=True)  == sec + (fine / 256.0)
    assert dt.encode(expected)           == rawdata


def testTIME64():
    dt   = dtype.Time64Type()
    sec  = 1113733097
    nsec = 31250000

    rawdata = bytearray(struct.pack('>I', sec))
    rawdata.extend(struct.pack('>I', nsec))

    date = datetime.datetime(2015, 4, 22, 10, 18, 17, 31250)

    assert dt.decode(rawdata)           == date
    assert dt.decode(rawdata, raw=True) == sec + (nsec / 1e9)
    assert dt.encode(date)              == rawdata


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

    assert dtype.get('LSB_U32[10]') == dtype.ArrayType('LSB_U32', 10)

    with nose.tools.assert_raises(ValueError):
        dtype.get('U8["foo"]')

    with nose.tools.assert_raises(ValueError):
        dtype.get('U8[-42]')


if __name__ == '__main__':
    nose.main()
