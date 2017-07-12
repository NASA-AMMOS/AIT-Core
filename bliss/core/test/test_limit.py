#!/usr/bin/env python

# Copyright 2017 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import os
import csv
import struct

import nose

import bliss
from bliss.core import limit

class TestLimitDefinition(object):
  test_yaml_test1 = '/tmp/test_test1.yaml'

  yaml_docs_test1 = (
    '- !Limit\n'
    '  source: 1553_HS_Packet.Voltage_A\n'
    '  desc: tbd\n'
    '  error:\n'
    '    min: 5.0\n'
    '    max: 45.0\n'
    '  warn:\n'
    '    min: 10.0\n'
    '    max: 40.0\n'
    '- !Limit\n'
    '  source: CCSDS_HEADER.secondary_header_flag\n'
    '  desc: tbd\n'
    '  error:\n'
    '    enum:\n'
    '      - Not Present\n'
    '- !Limit\n'
    '  source: CCSDS_HEADER.type\n'
    '  error:\n'
    '    enum:\n'
    '      - Core\n'
    '- !Limit\n'
    '  source: Ethernet_HS_Packet.product_type\n'
    '  error:\n'
    '    enum:\n'
    '    - TABLE_FOO\n'
    '    - TABLE_BAR\n'
  )

  def setUp(self):
    with open(self.test_yaml_test1, 'wb') as out:
      out.write(self.yaml_docs_test1)

  def tearDown(self):
    os.remove(self.test_yaml_test1)

  def test_limit_range(self):
    ldict = limit.LimitDict(self.test_yaml_test1)
    assert ldict['1553_HS_Packet.Voltage_A'].error.max == 45.0
    assert ldict['1553_HS_Packet.Voltage_A'].warn.min == 10.0

  def test_limit_error_enum(self):
    ldict = limit.LimitDict(self.test_yaml_test1)
    assert ldict['CCSDS_HEADER.type'].error.enum[0] == 'Core'

  def test_limit_error_enum_list(self):
    ldict = limit.LimitDict(self.test_yaml_test1)
    assert 'TABLE_FOO' in ldict['Ethernet_HS_Packet.product_type'].error.enum

  def test_limit_source(self):
    ldict = limit.LimitDict(self.test_yaml_test1)
    assert ldict['Ethernet_HS_Packet.product_type'].source_fld.name == 'product_type'

  def test_test_limit_yaml(self):
    ldict = limit.LimitDict()
    ldict.load(os.path.join(bliss.config._directory, 'limit', 'limit.yaml'))
    assert ldict['Ethernet_HS_Packet.product_type'].source_fld.name == 'product_type'  

