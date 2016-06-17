#!/usr/bin/env python

"""
BLISS EVR Parser Tests

Provides unit and functional tests for the bliss.evr module.
"""

"""
Authors: Jordan Padams

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import nose
import bliss


EVRs = { }
with open(bliss.config.evrdict.filename) as stream:
    for line in stream.readlines():
        code, desc           = line.split(':')
        EVRs[ int(code, 0) ] = desc.strip()


def testReaderIds():
    reader = bliss.evr.EVRReader()

    for code in EVRs.keys():
        assert reader.evrs[code] == EVRs[code]


def testGetDefaultEVRs():
    evrs = bliss.evr.getDefaultDict()

    for code in EVRs.keys():
        assert evrs[code] == EVRs[code]


if __name__ == '__main__':
    nose.main()
