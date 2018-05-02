#!/usr/bin/env python2.7

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import datetime
import math
import nose

from ait.core import dmc, coord


def float_equality(a, b, rel_tol=1e-06, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def test_cbrt():
    assert float_equality(coord.cbrt(64), 4)
    assert float_equality(coord.cbrt(-64), -4)
    assert float_equality(coord.cbrt(10), 2.1544346)

def test_eci2ecef():
    eci = -6.0744*1e6, -1.8289*1e6, 0.6685*1e6
    t = datetime.datetime(2010, 1, 17, 10, 20, 36)
    gmst = dmc.toGMST(t)
    ecef = coord.eci2ecef(eci[0], eci[1], eci[2], gmst=gmst)
    assert float_equality(ecef[0], 1628340.306018)
    assert float_equality(ecef[1], -6131208.5609442)
    assert float_equality(ecef[2], 668500.0)

def test_eci2geodetic():
    eci = -6.0744*1e6, -1.8289*1e6, 0.6685*1e6
    t = datetime.datetime(2010, 1, 17, 10, 20, 36)
    gmst = dmc.toGMST(t)
    lla = list(coord.eci2geodetic(eci[0], eci[1], eci[2], gmst=gmst))
    lla[0] = math.fmod(lla[0], math.pi * 2)
    lla[1] = math.fmod(lla[1], math.pi * 2)
    assert float_equality(math.degrees(lla[0]), 6.0558200)
    assert float_equality(math.degrees(lla[1]), -75.1266047)
    assert float_equality(lla[2], 978.4703290)

if __name__ == '__main__':
  nose.main()
