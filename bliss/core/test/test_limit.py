#!/usr/bin/env python

# Copyright 2017 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import os
import csv
import struct

import nose

import bliss
from bliss.core import limit

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
    ldict = limit.LimitDict(test_limit_range.__doc__)
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
    ldict = limit.LimitDict(test_limit_error_value.__doc__)
    assert 'Not Present' in ldict['CCSDS_HEADER.secondary_header_flag'].lower.error


def test_limit_source_fld():
    """
    # test_limit_source_fld

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: tbd
      lower:
        error:
          - 'TABLE_FOO'
          - 'TABLE_BAR'
        warn:
          - 'MEM_DUMP'
    """
    ldict = limit.LimitDict(test_limit_source_fld.__doc__)
    assert ldict['Ethernet_HS_Packet.product_type'].source_fld.name == 'product_type'


def test_example_limit_yaml():
    """
    # test_example_limit_yaml

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: tbd
      lower:
        error:
          - 'TABLE_FOO'
          - 'TABLE_BAR'
        warn:
          - 'MEM_DUMP'
    """
    ldict = limit.LimitDict()
    ldict.load(os.path.join(bliss.config._directory, 'limit', 'limit.yaml'))
    assert ldict['Ethernet_HS_Packet.product_type'].source_fld.name == 'product_type'  


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
    ldict = limit.LimitDict(test_check_upper_error.__doc__)
    assert ldict['1553_HS_Packet.Voltage_A'].error(46)


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
    ldict = limit.LimitDict(test_check_lower_warn.__doc__)
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
    ldict = limit.LimitDict(test_check_value_error.__doc__)
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
    ldict = limit.LimitDict(test_check_value_list_warn.__doc__)
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
    ldict = limit.LimitDict(test_check_value_list_warn2.__doc__)
    assert ldict['Ethernet_HS_Packet.product_type'].warn('BAR')
