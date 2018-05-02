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

import os
import unittest
import mock
import shutil

from ait.core import util


"""Specify some test file info"""
TEST_FILE_PATH = os.path.dirname(__file__) + "/testdata/util/test_util.txt"
TEST_FILE_SIZE = 117
TEST_FILE_CRC = 3099955026
TEST_FILE_CRC_SKIP_BYTE = 651256842

class Crc32FileTest(unittest.TestCase):
    """Unit test of the CRC-32 generator for files"""

    def testCrc32WithTestFile(self):
        """Test the CRC for a basic test file"""
        crc = util.crc32File(TEST_FILE_PATH)
        self.assertEqual(crc, TEST_FILE_CRC)

    def testCrc32WithTestFileAndSkip(self):
    	"""Test the CRC-32 with a skip specified"""
        crc = util.crc32File(TEST_FILE_PATH, 1)
        self.assertEqual(crc, TEST_FILE_CRC_SKIP_BYTE)

class EndianSwapU16Test(unittest.TestCase):
    """Unit test of the endianSwap method"""

    def testEndianSwap(self):
        """Test endian swap"""
        input_array = bytearray([0x13, 0x00, 0x01, 0x00, 0x08, 0x00])
        expected_output = bytearray([0x00, 0x13, 0x00, 0x01, 0x00, 0x08])
        output_array = util.endianSwapU16(input_array)
        self.assertEqual(output_array, expected_output)

class GetFileSizeTest(unittest.TestCase):
    """Unit test for finding size of file"""

    def testGetFileSize(self):
        """Test the method can properly calculate file size
        for known test data file
        """
        size = util.getFileSize(TEST_FILE_PATH)
        self.assertEqual(size, TEST_FILE_SIZE)

class ToBCDTest(unittest.TestCase):
    """Unit test for converting from a number to a Binary Coded
    Decimal
    """

    def testToBCDWithInt(self):
        """Test toBCD with integer"""
        bcd = util.toBCD(25)
        self.assertEqual("{0:b}".format(bcd), '100101')

class ToFloatTest(unittest.TestCase):
    """Unit test for toFloat method"""

    def testToFloat(self):
        """Test toFloat with float string"""
        f = util.toFloat("4.2")
        self.assertIsInstance(f, float)
        self.assertEqual(f, 4.2)

    def testToFloatWithDefaultSpecified(self):
        """Test toFloat with new default"""
        f = util.toFloat("UNDEFINED", 999.9)
        self.assertIsInstance(f, float)
        self.assertEqual(f, 999.9)

    def testToFloatWithDefaultReturnNone(self):
        """Test toFloat with return none"""
        f = util.toFloat("Foo")
        self.assertIsNone(f)

class ToNumberTest(unittest.TestCase):
    """Unit test for toNumber method"""

    def testToNumberWithHex(self):
        """Test toNumber with Hex specified"""
        n = util.toNumber("0x2A")
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithInt(self):
        """Test toNumber with int specified"""
        n = util.toNumber("42")
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithFloat(self):
        """Test toNumber with float specified"""
        n = util.toNumber("42.0")
        self.assertIsInstance(n, float)
        self.assertEqual(n, 42.0)

    def testToNumberWithStringAndDefaultSpecified(self):
        """Test toNumber with String and new default specified"""
        n = util.toNumber("Foo", 42)
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithDefaultReturnNone(self):
        """Test toNumber with String and None return"""
        n = util.toNumber("Foo")
        self.assertIsNone(n);

class ToReprTest(unittest.TestCase):
    """Unit test for converting Python object to
    string representation
    """

    def testToReprWithString(self):
        """TODO"""
        pass


def test_expandPath ():
    pathname = os.path.join('~', 'bin', 'ait-orbits')
    assert util.expandPath(pathname) == os.path.expanduser(pathname)

    pathname = os.path.join('/', 'bin', 'ait-orbits')
    assert util.expandPath(pathname) == pathname

    pathname = os.path.join('' , 'bin', 'ait-orbits')
    assert util.expandPath(pathname) == os.path.abspath(pathname)

    pathname = os.path.join('' , 'bin', 'ait-orbits')
    prefix   = os.path.join('/', 'ait')
    expected = os.path.join(prefix, pathname)
    assert util.expandPath(pathname, prefix) == expected


def test_listAllFiles():
    pathname = os.path.join('~','foo','bar')
    directory = os.path.expanduser(pathname)
    try:
        os.makedirs(os.path.expanduser(directory))
        files = [ os.path.join(directory, 'test_1.txt'), os.path.join(directory, 'test_2.txt') ]
        for fname in files:
            with open(fname, 'wb') as file:
                os.utime(fname, None)

        # test relative path
        filelist = util.listAllFiles(pathname, ".txt")
        assert os.path.relpath(files[0], start=directory) in filelist
        
        # test absolute path
        filelist = util.listAllFiles(pathname, ".txt", True)
        assert files[0] in filelist
    finally:
        shutil.rmtree(os.path.expanduser(os.path.join('~','foo')))


@mock.patch('ait.core.log.error')
def test_YAMLValidationError_exception(log_mock):
    message = 'foo'
    e = util.YAMLValidationError(message)
    assert message == e.message
    log_mock.assert_called_with(message)

@mock.patch('ait.core.log.error')
def test_YAMLError_exception(log_mock):
    message = 'foo'
    e = util.YAMLError(message)
    assert message == e.message
    log_mock.assert_called_with(message)

if __name__ == '__main__':
    unittest.main(verbosity=2)
    nose.main()
