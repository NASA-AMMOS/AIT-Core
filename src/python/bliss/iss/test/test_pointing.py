#!/usr/bin/env python

"""
BLISS ISS Pointing Unit Tests

The bliss.iss.test.test_pointing module provides unit and functional
tests for the bliss.iss.pointing module.

Assumes these tests will be run in POSIX environment
"""

"""
Authors: Ben Bornstein

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import nose
import bliss


def pathTo (filename):
    import os
    return os.path.join(bliss.Config.ROOT_DIR, './data', filename)


def toDatetime (s):
    import datetime
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S %Z')


def testLoadAreasReport ():
    pathname = pathTo('JSC_Pointing_Report_Areas_2015_300_321_Partial.txt')
    report   = bliss.iss.pointing.AreasReport(pathname)
    names    = ('ARM TWP - Darwin, Au', 'Bialystok, Poland', 'Lauder, NZ',
                'Park Falls, WI', 'SGP ARM Site, Lamont')

    assert report.filename   == pathname
    assert len(report.areas) == 212

    for area in report.areas:
        assert area.name in names


def testLoadWorldReport ():
    pathname = pathTo('JSC_Pointing_Report_World_2015_300_321.txt')
    report   = bliss.iss.pointing.WorldReport(pathname)
    
    assert report.filename        == pathname
    print report.path.first.time.isoformat()
    assert report.path.first.time == toDatetime('2015-10-27T00:00:00 UTC')
    assert report.path.last.time  == toDatetime('2015-11-17T00:00:00 UTC')
    assert len(report.path)       == 120961


def testLoadSZAReport ():
    pathname = pathTo('JSC_Pointing_Report_SZA85_2015_300_321.txt')
    report   = bliss.iss.pointing.SZAReport(pathname)

    assert report.filename      == pathname
    assert len(report.eclipses) == 326
    assert len(report.szangles) == 327



if __name__ == '__main__':
    nose.main()
