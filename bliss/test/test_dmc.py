# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS DMC Tests

The bliss.tests.test_dmc module provides unit and functional
tests for the bliss.dmc module
"""

import nose
import bliss
import datetime


def test_getUTCDatetimeDOY():
    timestamp = datetime.datetime.utcnow().timetuple()

    exp_year = timestamp.tm_year
    exp_day = timestamp.tm_yday

    dtime = bliss.dmc.getUTCDatetimeDOY().split(':')

    assert str(exp_year) == dtime[0]
    assert str(exp_day) == dtime[1]


def test_getUTCDatetimeDOY_w_slack():
    slack = 864000
    t = datetime.datetime.utcnow() + datetime.timedelta(seconds=slack)
    timestamp = t.timetuple()
    exp_year = timestamp.tm_year
    exp_day = timestamp.tm_yday

    dtime = bliss.dmc.getUTCDatetimeDOY(slack).split(':')

    assert str(exp_year) == dtime[0]
    assert str(exp_day) == dtime[1]

if __name__ == '__main__':
    nose.main()
