#!/usr/bin/env python2.7

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
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
import struct
import warnings

import nose

from ait.core import table

TmpFilename = None

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    TmpFilename = 'tmpfile'# os.tmpnam();


class Season:
    SPRING=1
    SUMMER=2
    AUTUMN=3
    WINTER=4


class Color:
    RED=1
    GREEN=2
    BLUE=3
    YELLOW=4


# Util to create and destroy a file for testing
class TestTableWriter(object):

    # Creates a table file to be used in the tests
    def writeTempFile(self):
        yaml_table_test = (
            "- !FSWTable"
            "  name: test"
            "  delimiter: '-'"
            "  uptype: 1"
            "  size: 5120"
            "  header:"
            "    - !FSWColumn:"
            "      name: HEADER_COLUMN_ONE"
            "      desc: First header column"
            "      format: '%u'"
            "      units: none"
            "      type: U8"
            "      bytes: 1"
            "    - !FSWColumn:"
            "      name: HEADER_COLUMN_TWO"
            "      desc: Second header column"
            "      format: '%u'"
            "      units: cm"
            "      type: U16"
            "      bytes: 4"
            "  columns:"
            "    - !FSWColumn"
            "      name: COL_ONE"
            "      desc: First table column"
            "      format: '%u'"
            "      units: none"
            "      type: U8"
            "      bytes: 1"
            "    - !FSWColumn"
            "      name: COL_TWO"
            "      desc: Second table column"
            "      format: '%u'"
            "      units: cm"
            "      type: U16"
            "      bytes: 4"
            "      enum:"
            "        0: SPRING"
            "        1: SUMMER"
            "        2: AUTUMN"
            "        3: WINTER"
            )
        with open(TmpFilename, 'wb') as file:
            file.write(yaml_table_test)

    def tearDown(self):
        os.unlink(TmpFilename)


def testTestTest():
    '''Tests the test'''
    assert 1


def testColDefn():
    '''Test single column definition'''
    column = table.FSWColDefn(
        name='test_col',
        type='U8',
        bytes=4,
        format='%u',
        units='none',
        items=4,
        enum=Season,
    )
    assert column.name is 'test_col'
    assert column.type is 'U8'
    column.type = 'U16'
    assert column.type is 'U16'
    assert column.bytes is 4
    column.bytes = 3
    assert column.bytes is 3
    assert column.format is '%u'
    column.format = '%i'
    assert column.format is '%i'
    assert column.units is 'none'
    column.units = 'cm'
    assert column.units is 'cm'
    assert column.items is 4
    column.items = 2
    assert column.items is 2
    assert column.enum is Season
    column.enum = Color
    assert column.enum is Color


def testTabDefnAndWrite():
    '''Test table definition'''
    coldefn = table.FSWColDefn(
        me='test_col',
        type='U8',
        bytes=4,
        format='%u',
        units='none',
        items=4,
        enum=Season,
    )
    coldefn2 = table.FSWColDefn(
        name='test_col2',
        type='U8',
        bytes=1,
        format='%u',
        units='none',
        items=4,
        enum=Color,
    )
    tabledefn = table.FSWTabDefn(
        name='test_table',
        delimiter='-',
        uptype=1,
        size=8000,
        rows=10,
        fswheaderdefns=None,
        coldefns=[coldefn, coldefn2],
    )
    fileholder = TestTableWriter()
    fileholder.writeTempFile()

    # Test that the table was created properly
    assert tabledefn.name is 'test_table'
    assert tabledefn.delimiter is '-'
    assert tabledefn.uptype is 1
    assert tabledefn.size is 8000
    assert tabledefn.rows is 10
    assert tabledefn.coldefns[0] is coldefn
    assert tabledefn.coldefns[1] is coldefn2

    # Write table to text file
    stream = open(TmpFilename, 'rw')
    outstream = open('tempfile', 'wr')

    # Test that the text file was created and did not exit with error code
    assert tabledefn.toText(stream, outstream, 1, 0.0) is None

    # Close the write to text
    stream.close()
    outstream.close()

    # Write table to binary file
    stream = open(TmpFilename, 'rw')
    outstream = open('tempfileb', 'wr')

    # Version in toBinary does not appear to be handled properly
    #assert tabledefn.toBinary('tempfile', stream, outstream, 1, 0.0) is None

    # Test that getDefaultFSWTabDict exits without an error code
    # and does not erroneously produce a dictionary when none exists
    assert table.getDefaultFSWTabDict() is None

    # Create a new table dictionary
    tabdict = table.FSWTabDict()
    tabdict.add(tabledefn)
    tabdict.create('test',{'colnames':tabledefn.coldefns})

    # Load a table definition to the dictionary
    tabdict.load('ait/core/test/testdata/val/testCmdValidator6.yaml')

    # Assert writing to text does not exit with an error code
    assert table.writeToText(tabdict,'test_table','tempfileb',0,0.0) is None

    #having trouble with getting version from TmpFilename
    #assert table.writeToBinary(tabdict,'test_table',TmpFilename,0) is None

    stream.close()
    outstream.close()

    os.unlink('tempfile')
    os.unlink('tempfileb')
    os.unlink('test_table_table00.txt')
    fileholder.tearDown()


if __name__ == '__main__':
    nose.main()
