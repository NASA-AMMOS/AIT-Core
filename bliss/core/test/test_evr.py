#!/usr/bin/env python2.7

# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import nose

import bliss
from bliss.core import evr


EVRs = { }

with open(bliss.config.evrdict.filename) as stream:
    for line in stream.readlines():
        code, desc           = line.split(':')
        EVRs[ int(code, 0) ] = desc.strip()


def testReaderIds():
    reader = evr.EVRReader()

    for code in EVRs.keys():
        assert reader.evrs[code] == EVRs[code]


def testGetDefaultEVRs():
    evrs = evr.getDefaultDict()

    for code in EVRs.keys():
        assert evrs[code] == EVRs[code]


if __name__ == '__main__':
    nose.main()
