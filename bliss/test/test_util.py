#!/usr/bin/env python
#
# Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Utilities Tests

The bliss.tests.test_util module provides unit and functional
tests for the bliss.util module
"""

import unittest
import bliss.util
import os

"""Specify some test file info"""
TEST_FILE_PATH = os.path.dirname(__file__) + "/testdata/util/test_util.txt"
TEST_FILE_SIZE = 117
TEST_FILE_CRC = 3099955026
TEST_FILE_CRC_SKIP_BYTE = 651256842

class Crc32FileTest(unittest.TestCase):
    """Unit test of the CRC-32 generator for files"""
    
    def testCrc32WithTestFile(self):
        """Test the CRC for a basic test file"""
        crc = bliss.util.crc32File(TEST_FILE_PATH)
        self.assertEqual(crc, TEST_FILE_CRC)

    def testCrc32WithTestFileAndSkip(self):
    	"""Test the CRC-32 with a skip specified"""
        crc = bliss.util.crc32File(TEST_FILE_PATH, 1)
        self.assertEqual(crc, TEST_FILE_CRC_SKIP_BYTE)

class EndianSwapU16Test(unittest.TestCase):
    """Unit test of the endianSwap method"""
    
    def testEndianSwap(self):
        """Test endian swap"""
        input_array = bytearray([0x13, 0x00, 0x01, 0x00, 0x08, 0x00])
        expected_output = bytearray([0x00, 0x13, 0x00, 0x01, 0x00, 0x08])
        output_array = bliss.util.endianSwapU16(input_array)
        self.assertEqual(output_array, expected_output)

class GetFileSizeTest(unittest.TestCase):
    """Unit test for finding size of file"""
    
    def testGetFileSize(self):
        """Test the method can properly calculate file size
        for known test data file
        """
        size = bliss.util.getFileSize(TEST_FILE_PATH)
        self.assertEqual(size, TEST_FILE_SIZE)

class ToBCDTest(unittest.TestCase):
    """Unit test for converting from a number to a Binary Coded
    Decimal
    """

    def testToBCDWithInt(self):
        """Test toBCD with integer"""
        bcd = bliss.util.toBCD(25)
        self.assertEqual("{0:b}".format(bcd), '100101')

class ToFloatTest(unittest.TestCase):
    """Unit test for toFloat method"""
    
    def testToFloat(self):
        """Test toFloat with float string"""
        f = bliss.util.toFloat("4.2")
        self.assertIsInstance(f, float)
        self.assertEqual(f, 4.2)

    def testToFloatWithDefaultSpecified(self):
        """Test toFloat with new default"""
        f = bliss.util.toFloat("UNDEFINED", 999.9)
        self.assertIsInstance(f, float)
        self.assertEqual(f, 999.9)

    def testToFloatWithDefaultReturnNone(self):
        """Test toFloat with return none"""
        f = bliss.util.toFloat("Foo")
        self.assertIsNone(f)

class ToNumberTest(unittest.TestCase):
    """Unit test for toNumber method"""
    
    def testToNumberWithHex(self):
        """Test toNumber with Hex specified"""
        n = bliss.util.toNumber("0x2A")
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithInt(self):
        """Test toNumber with int specified"""
        n = bliss.util.toNumber("42")
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithFloat(self):
        """Test toNumber with float specified"""
        n = bliss.util.toNumber("42.0")
        self.assertIsInstance(n, float)
        self.assertEqual(n, 42.0)

    def testToNumberWithStringAndDefaultSpecified(self):
        """Test toNumber with String and new default specified"""
        n = bliss.util.toNumber("Foo", 42)
        self.assertIsInstance(n, int)
        self.assertEqual(n, 42)

    def testToNumberWithDefaultReturnNone(self):
        """Test toNumber with String and None return"""
        n = bliss.util.toNumber("Foo")
        self.assertIsNone(n);

class ToReprTest(unittest.TestCase):
    """Unit test for converting Python object to 
    string representation
    """
    
    def testToReprWithString(self):
        """TODO"""
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)
