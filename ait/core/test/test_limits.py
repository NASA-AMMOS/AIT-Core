#!/usr/bin/env python

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
import csv
import struct

import nose

import ait
from ait.core import limits, tlm

def test_limit_range():
    """
    # test_limit_range

    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
        warn: 10.0
      upper:
        error: 45.0
        warn: 40.0
    """
    ldict = limits.LimitsDict(test_limit_range.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].upper.error == 45.0
    assert ldict['1553_HS_Packet.Voltage_A'].lower.warn == 10.0


def test_limit_error_value():
    """
    # test_limit_error_value

    - !Limit
      source: CCSDS_HEADER.secondary_header_flag
      desc: tbd
      lower:
        error: Not Present
    """
    ldict = limits.LimitsDict(test_limit_error_value.__doc__)
    assert 'Not Present' in ldict['CCSDS_HEADER.secondary_header_flag'].lower.error


def test_check_upper_error():
    """
    # test_check_upper_error

    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
        warn: 10.0
      upper:
        error: 45.0
        warn: 40.0
    """
    ldict = limits.LimitsDict(test_check_upper_error.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].error(46)


def test_check_missing_value_warn():
    """
    # test_check_missing_value_warn

    - !Limit
      source: CCSDS_HEADER.secondary_header_flag
      desc: tbd
      lower:
        error: Not Present
    """
    ldict = limits.LimitsDict(test_check_missing_value_warn.__doc__)
    assert ldict['CCSDS_HEADER.secondary_header_flag'].warn('Foo') == False


def test_check_missing_value_error():
    """
    # test_check_missing_value_error

    - !Limit
      source: CCSDS_HEADER.secondary_header_flag
      desc: tbd
      lower:
        warn: Not Present
    """
    ldict = limits.LimitsDict(test_check_missing_value_error.__doc__)
    assert ldict['CCSDS_HEADER.secondary_header_flag'].error('Foo') == False


def test_check_missing_lower_warn():
    """
    # test_check_missing_lower_warn
    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
      upper:
        error: 45.0
        warn: 40.0
    """
    ldict = limits.LimitsDict(test_check_missing_lower_warn.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].warn(6) == False


def test_check_missing_upper_warn():
    """
    # test_check_missing_upper_warn
    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
        warn: 10.0
      upper:
        error: 45.0
    """
    ldict = limits.LimitsDict(test_check_missing_upper_warn.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].warn(15) == False


def test_check_missing_lower_error():
    """
    # test_check_missing_lower_error
    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        warn: 10.0
      upper:
        error: 45.0
        warn: 40.0
    """
    ldict = limits.LimitsDict(test_check_missing_lower_error.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].error(15) == False


def test_check_missing_upper_error():
    """
    # test_check_missing_upper_error
    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
        warn: 10.0
      upper:
        warn: 45.0
    """
    ldict = limits.LimitsDict(test_check_missing_upper_error.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].error(15) == False


def test_check_lower_warn():
    """
    # test_check_lower_warn
    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: tbd
      lower:
        error: 5.0
        warn: 10.0
      upper:
        error: 45.0
        warn: 40.0
    """
    ldict = limits.LimitsDict(test_check_lower_warn.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].warn(6)

def test_check_value_error():
    """
    # test_check_value_error

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: tbd
      value:
        error: TABLE_BAR
        warn: TABLE_FOO
    """
    ldict = limits.LimitsDict(test_check_value_error.__doc__)
    assert ldict['Ethernet_HS_Packet.product_type'].error('TABLE_BAR')
    assert ldict['Ethernet_HS_Packet.product_type'].warn('TABLE_FOO')

def test_check_value_list_warn():
    """
    # test_check_value_error

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: tbd
      value:
        error: FOOBAR
        warn: [ FOO, BAR ]
    """
    ldict = limits.LimitsDict(test_check_value_list_warn.__doc__)
    assert ldict['Ethernet_HS_Packet.product_type'].error('FOOBAR')
    assert ldict['Ethernet_HS_Packet.product_type'].warn('BAR')

def test_check_value_list_warn2():
    """
    # test_check_value_error

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: tbd
      value:
        error: FOOBAR
        warn:
          - FOO
          - BAR
    """
    ldict = limits.LimitsDict(test_check_value_list_warn2.__doc__)
    assert ldict['Ethernet_HS_Packet.product_type'].warn('BAR')

