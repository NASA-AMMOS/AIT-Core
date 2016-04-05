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
