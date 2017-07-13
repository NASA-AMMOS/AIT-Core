#!/usr/bin/env python2.7

# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import time
import datetime
import nose

from bliss.core import dmc


def test_getTimestampUTC():
    expected = time.strftime('%Y-%j', time.gmtime())

    actual = time.strftime('%Y-%j', time.gmtime(dmc.getTimestampUTC()[0]))

    assert actual == expected


def test_getUTCDatetimeDOY_w_days():
    days      = 1
    t         = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    timestamp = t.timetuple()
    exp_year  = timestamp.tm_year
    exp_day   = '%03d' % timestamp.tm_yday

    dtime     = dmc.getUTCDatetimeDOY(days=days).split('T')[0].split('-')
    assert str(exp_year) == dtime[0]
    assert str(exp_day)  == dtime[1]


if __name__ == '__main__':
    nose.main()
