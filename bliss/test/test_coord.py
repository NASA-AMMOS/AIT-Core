# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

import datetime
import math

import bliss
import nose

def float_equality(a, b, rel_tol=1e-06, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def test_cbrt():
    assert float_equality(bliss.coord.cbrt(64), 4)
    assert float_equality(bliss.coord.cbrt(-64), -4)
    assert float_equality(bliss.coord.cbrt(10), 2.1544346)

def test_ecef2geodetic():
    rad_lat, rad_lon, altitude = bliss.coord.ecef2geodetic(4510731, 4510731, 0)
    assert float_equality(math.degrees(rad_lat), 0.0)
    assert float_equality(math.degrees(rad_lon), 45.0)
    assert float_equality(altitude, 999.9564)

    rad_lat, rad_lon, altitude = bliss.coord.ecef2geodetic(2297292.93, 1016894.95, -5843939.67)
    assert float_equality(math.degrees(rad_lat), -66.87654)
    assert float_equality(math.degrees(rad_lon), 23.87654)
    assert float_equality(altitude, 1000.1, rel_tol=1e-2)

def test_eci2ecef():
    eci = -6.0744*1e6, -1.8289*1e6, 0.6685*1e6
    t = datetime.datetime(2010, 1, 17, 10, 20, 36)
    gmst = bliss.dmc.toGMST(t)
    ecef = bliss.coord.eci2ecef(eci[0], eci[1], eci[2], gmst=gmst)
    assert float_equality(ecef[0], 1628340.306018)
    assert float_equality(ecef[1], -6131208.5609442)
    assert float_equality(ecef[2], 668500.0)

def test_eci2geodetic():
    eci = -6.0744*1e6, -1.8289*1e6, 0.6685*1e6
    t = datetime.datetime(2010, 1, 17, 10, 20, 36)
    gmst = bliss.dmc.toGMST(t)
    lla = list(bliss.coord.eci2geodetic(eci[0], eci[1], eci[2], gmst=gmst))
    lla[0] = math.fmod(lla[0], math.pi * 2)
    lla[1] = math.fmod(lla[1], math.pi * 2)
    assert float_equality(math.degrees(lla[0]), 6.0558200)
    assert float_equality(math.degrees(lla[1]), -75.1266047)
    assert float_equality(lla[2], 978.4703290)

def test_eci_conversion_equality():
    eci = -6.0744*1e6, -1.8289*1e6, 0.6685*1e6
    t = datetime.datetime(2010, 1, 17, 10, 20, 36)
    gmst = bliss.dmc.toGMST(t)
    ecef = bliss.coord.eci2ecef(eci[0], eci[1], eci[2], gmst=gmst)
    lla1 = list(bliss.coord.ecef2geodetic(ecef[0], ecef[1], ecef[2]))
    lla1[0] = math.fmod(lla1[0], math.pi * 2)
    lla1[1] = math.fmod(lla1[1], math.pi * 2)

    lla2 = list(bliss.coord.eci2geodetic(eci[0], eci[1], eci[2], gmst=gmst))
    lla2[0] = math.fmod(lla2[0], math.pi * 2)
    lla2[1] = math.fmod(lla2[1], math.pi * 2)

    assert float_equality(lla1[0], lla2[0])
    assert float_equality(lla1[1], lla2[1])
    assert float_equality(lla1[2], lla2[2])

if __name__ == '__main__':
  nose.main()
