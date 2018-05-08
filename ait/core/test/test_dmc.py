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
import mock
import os
import os.path
import nose
import nose.tools

import ait.core
from ait.core import dmc

LEAPSECOND_DATA_RESPONSE = '''#
#    Updated through IERS Bulletin C55
#    File expires on:  28 December 2018
#
#@	3754944000
#
2272060800	10	# 1 Jan 1972
2287785600	11	# 1 Jul 1972
2303683200	12	# 1 Jan 1973
2335219200	13	# 1 Jan 1974
2366755200	14	# 1 Jan 1975
2398291200	15	# 1 Jan 1976
2429913600	16	# 1 Jan 1977
2461449600	17	# 1 Jan 1978
2492985600	18	# 1 Jan 1979
2524521600	19	# 1 Jan 1980
2571782400	20	# 1 Jul 1981
2603318400	21	# 1 Jul 1982
2634854400	22	# 1 Jul 1983
2698012800	23	# 1 Jul 1985
2776982400	24	# 1 Jan 1988
2840140800	25	# 1 Jan 1990
2871676800	26	# 1 Jan 1991
2918937600	27	# 1 Jul 1992
2950473600	28	# 1 Jul 1993
2982009600	29	# 1 Jul 1994
3029443200	30	# 1 Jan 1996
3076704000	31	# 1 Jul 1997
'''

class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

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

def test_leap_second_attrs():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "leapseconds.dat"
    )

    ls = dmc.LeapSeconds
    ls._load_leap_second_data()
    assert ls.leapseconds == ls._data['leapseconds']
    assert ls.valid_date == ls._data['valid']
    assert ls.get_current_GPS_offset() == ls.leapseconds[-1][-1]

@nose.tools.raises(ValueError)
def test_leap_second_by_date_invalid_gps_date():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "leapseconds.dat"
    )

    dmc.LeapSeconds._load_leap_second_data()
    dmc.LeapSeconds.get_GPS_offset_for_date(datetime.datetime(1980, 1, 1))

def test_leap_second_by_date():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "leapseconds.dat"
    )

    ls = dmc.LeapSeconds
    ls._load_leap_second_data()
    assert ls.get_GPS_offset_for_date(datetime.datetime(1981, 1, 1)) == 0
    assert ls.get_GPS_offset_for_date(datetime.datetime(1981, 7, 1)) == 1
    assert ls.get_GPS_offset_for_date(datetime.datetime(1982, 7, 1)) == 2
    assert ls.get_GPS_offset_for_date(datetime.datetime(1983, 7, 1)) == 3
    assert ls.get_GPS_offset_for_date(datetime.datetime(1985, 7, 1)) == 4
    assert ls.get_GPS_offset_for_date(datetime.datetime(1988, 1, 1)) == 5
    assert ls.get_GPS_offset_for_date(datetime.datetime(1990, 1, 1)) == 6
    assert ls.get_GPS_offset_for_date(datetime.datetime(1991, 1, 1)) == 7
    assert ls.get_GPS_offset_for_date(datetime.datetime(1992, 7, 1)) == 8
    assert ls.get_GPS_offset_for_date(datetime.datetime(1993, 7, 1)) == 9
    assert ls.get_GPS_offset_for_date(datetime.datetime(1994, 7, 1)) == 10
    assert ls.get_GPS_offset_for_date(datetime.datetime(1996, 1, 1)) == 11
    assert ls.get_GPS_offset_for_date(datetime.datetime(1997, 7, 1)) == 12
    assert ls.get_GPS_offset_for_date(datetime.datetime(1999, 1, 1)) == 13
    assert ls.get_GPS_offset_for_date(datetime.datetime(2006, 1, 1)) == 14
    assert ls.get_GPS_offset_for_date(datetime.datetime(2009, 1, 1)) == 15
    assert ls.get_GPS_offset_for_date(datetime.datetime(2012, 7, 1)) == 16
    assert ls.get_GPS_offset_for_date(datetime.datetime(2015, 7, 1)) == 17
    assert ls.get_GPS_offset_for_date(datetime.datetime(2017, 1, 1)) == 18

def test_leap_second_data_load():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "leapseconds.dat"
    )

    assert type(dmc.LeapSeconds.leapseconds) == type([])
    assert dmc.LeapSeconds.leapseconds[0] == (datetime.datetime(1981, 7, 1), 1)
    assert type(dmc.LeapSeconds.valid_date) == type(datetime.datetime.now())

@nose.tools.raises(ValueError)
@mock.patch('requests.get', mock.MagicMock(return_value=MockResponse(LEAPSECOND_DATA_RESPONSE, 400)))
def test_failed_leapsecond_load_and_update():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "invalidpath", "leapseconds.dat"
    )

    dmc.LeapSeconds._data = None
    dmc.LeapSeconds._load_leap_second_data()

@mock.patch('requests.get', mock.MagicMock(return_value=MockResponse(LEAPSECOND_DATA_RESPONSE, 200)))
def test_update_leap_second_data():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "tmp_leapseconds.out"
    )

    dmc.LeapSeconds._data = None
    dmc.LeapSeconds._update_leap_second_data()

    assert type(dmc.LeapSeconds.leapseconds) == type([])
    assert dmc.LeapSeconds.leapseconds[0] == (datetime.datetime(1981, 7, 1), 1)
    assert type(dmc.LeapSeconds.valid_date) == type(datetime.datetime.now())

    assert os.path.isfile(ait.config.leapseconds.filename)
    os.remove(ait.config.leapseconds.filename)

@nose.tools.raises(ValueError)
@mock.patch('requests.get', mock.MagicMock(return_value=MockResponse(LEAPSECOND_DATA_RESPONSE, 400)))
def test_unable_to_pull_leapsecond_data():
    ait.config.leapseconds._config['filename'] = os.path.join(
        os.path.dirname(__file__), "testdata", "dmc", "tmp_leapseconds.out"
    )

    dmc.LeapSeconds._data = None
    dmc.LeapSeconds._update_leap_second_data()

if __name__ == '__main__':
    nose.main()
