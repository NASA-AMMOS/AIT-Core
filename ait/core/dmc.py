# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2013, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""AIT DeLorean Motor Company (DMC)

The ait.dmc module provides utilities to represent, translate, and
manipulate time, building upon Python's datetime and timedelta data
types.

Many functions assume the GPS (and ISS) epoch: January 6, 1980 at
midnight.

"""

import calendar
import datetime
import math
import os.path
import pickle
import time

import requests

import ait.core
from ait.core import log

GPS_Epoch = datetime.datetime(1980, 1, 6, 0, 0, 0)
TICs      = [ ]
TwoPi     = 2 * math.pi

DOY_Format = '%Y-%jT%H:%M:%SZ'
ISO_8601_Format = '%Y-%m-%dT%H:%M:%SZ'

_DEFAULT_FILE_NAME = 'leapseconds.dat'
LeapSeconds = None

def getTimestampUTC():
    """getTimestampUTC() -> (ts_sec, ts_usec)

    Returns the current UTC time in seconds and microseconds.
    """
    utc     = datetime.datetime.utcnow()
    ts_sec  = calendar.timegm( utc.timetuple() )
    ts_usec = utc.microsecond
    return ts_sec, ts_usec


def getUTCDatetimeDOY(days=0, hours=0, minutes=0, seconds=0):
    """getUTCDatetimeDOY -> datetime

    Returns the UTC current datetime with the input timedelta arguments (days, hours, minutes, seconds)
    added to current date. Returns ISO-8601 datetime format for day of year:

        YYYY-DDDTHH:mm:ssZ

    """
    return (datetime.datetime.utcnow() + 
        datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)).strftime(DOY_Format)


def tic():
    """tic()

    Records the current time for benchmarking purposes.  See also toc().
    """
    global TICs
    begin = datetime.datetime.now()
    TICs.append(begin)


def toc():
    """toc() -> float | None

    Returns the total elapsed seconds since the most recent tic(), or
    None if tic() was not called.

    Examples:

    >>> import time

    >>> tic()
    >>> time.sleep(1.2)
    >>> elapsed = toc()

    >>> assert abs(elapsed - 1.2) <= 1e-2

    .. note:: The tic() and toc() functions are simplistic and may introduce
            significant overhead, especially in tight loops.  Their use should
            be limited to one-off experiments and rough numbers.  The Python
            profile package (i.e. 'import profile') should be used for serious
            and detailed profiling.
    """
    end = datetime.datetime.now()
    return totalSeconds( end - TICs.pop() ) if len(TICs) else None


def toGPSWeekAndSecs(timestamp=None):
    """Converts the given UTC timestamp (defaults to the current time) to
    a two-tuple, (GPS week number, GPS seconds within the week).
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    leap = LeapSeconds.get_GPS_offset_for_date(timestamp)

    secsInWeek = 604800
    delta      = totalSeconds(timestamp - GPS_Epoch) + leap
    seconds    = delta % secsInWeek
    week       = int( math.floor(delta / secsInWeek) )

    return (week, seconds)


def toGPSSeconds(timestamp):
    """toGPSSeconds(timestamp) -> integer

    Converts the given Python datetime object to the number of seconds
    since the GPS Epoch (midnight on January 6th, 1980).

    Examples:

    >>> import datetime

    >>> toGPSSeconds( datetime.datetime(1980, 1, 6) )
    0

    >>> toGPSSeconds( datetime.datetime(1980, 1, 7) )
    86400
    """
    delta = timestamp - GPS_Epoch
    return (delta.days * 24 * 3600) + delta.seconds


def toGMST(dt=None):
    """Converts the given Python datetime or Julian date (float) to
    Greenwich Mean Sidereal Time (GMST) (in radians) using the formula
    from D.A. Vallado (2004).

    See:

        D.A. Vallado, Fundamentals of Astrodynamics and Applications, p. 192
        http://books.google.com/books?id=PJLlWzMBKjkC&lpg=PA956&vq=192&pg=PA192
    """
    if dt is None or type(dt) is datetime.datetime:
        jd = toJulian(dt)
    else:
        jd = dt

    tUT1  = (jd - 2451545.0) / 36525.0
    gmst  = 67310.54841 + (876600 * 3600 + 8640184.812866) * tUT1
    gmst += 0.093104 * tUT1**2
    gmst -= 6.2e-6   * tUT1**3

    # Convert from seconds to degrees, i.e.
    # 86400 seconds / 360 degrees = 240 seconds / degree
    gmst /= 240.

    # Convert to radians
    gmst  = math.radians(gmst) % TwoPi

    if gmst < 0:
        gmst += TwoPi

    return gmst


def toJulian(dt=None):
    """Converts a Python datetime to a Julian date, using the formula from
    Meesus (1991).  This formula is reproduced in D.A. Vallado (2004).

    See:

        D.A. Vallado, Fundamentals of Astrodynamics and Applications, p. 187
        http://books.google.com/books?id=PJLlWzMBKjkC&lpg=PA956&vq=187&pg=PA187
    """
    if dt is None:
        dt = datetime.datetime.utcnow()

    if dt.month < 3:
        year  = dt.year  -  1
        month = dt.month + 12
    else:
        year  = dt.year
        month = dt.month

    A   = int(year / 100.0)
    B   = 2 - A + int(A / 4.0)
    C   = ( (dt.second / 60.0 + dt.minute) / 60.0 + dt.hour ) / 24.0
    jd  = int(365.25  * (year + 4716))
    jd += int(30.6001 * (month + 1)) + dt.day + B - 1524.5 + C

    return jd


def toLocalTime(seconds, microseconds=0):
    """toLocalTime(seconds, microseconds=0) -> datetime

    Converts the given number of seconds since the GPS Epoch (midnight
    on January 6th, 1980) to this computer's local time.  Returns a
    Python datetime object.

    Examples:

    >>> toLocalTime(0)
    datetime.datetime(1980, 1, 6, 0, 0)

    >>> toLocalTime(25 * 86400)
    datetime.datetime(1980, 1, 31, 0, 0)
    """
    delta = datetime.timedelta(seconds=seconds, microseconds=microseconds)
    return GPS_Epoch + delta


def totalSeconds(td):
    """totalSeconds(td) -> float

    Return the total number of seconds contained in the given Python
    datetime.timedelta object.  Python 2.6 and earlier do not have
    timedelta.total_seconds().

    Examples:

    >>> totalSeconds( toLocalTime(86400.123) - toLocalTime(0.003) )
    86400.12
    """
    if hasattr(td, "total_seconds"):
        ts = td.total_seconds()
    else:
        ts = (td.microseconds + (td.seconds + td.days * 24 * 3600.0) * 1e6) / 1e6

    return ts


class UTCLeapSeconds(object):
    def __init__(self):
        self._data = None
        self._load_leap_second_data()

    @property
    def leapseconds(self):
        return self._data['leapseconds']

    @property
    def valid_date(self):
        return self._data['valid']

    def is_valid(self):
        return datetime.datetime.now() < self._data['valid']

    def get_current_GPS_offset(self):
        return self._data['leapseconds'][-1][-1]

    def get_GPS_offset_for_date(self, timestamp):
        if timestamp is None:
                timestamp = datetime.datetime.utcnow()

        if timestamp < GPS_Epoch:
                e = "The timestamp date is before the GPS epoch"
                raise ValueError(e)

        for offset in reversed(self._data['leapseconds']):
            # Offsets are stored as a tuple (date, offset)
            # indicating the `date` when `offset` took effect.
            if timestamp >= offset[0]:
                return offset[1]
        else:
            return 0

    def _load_leap_second_data(self):
        ls_file = ait.config.get(
            'leapseconds.filename',
            os.path.join(ait.config._directory, _DEFAULT_FILE_NAME)
        )

        try:
            with open(ls_file, 'r') as outfile:
                self._data = pickle.load(outfile)
        except IOError:
            log.info('Unable to locate leapseconds config file')

        if not (self._data and self.is_valid()):
            try:
                self._update_leap_second_data()
            except ValueError:
                msg = (
                    'Leapsecond data update failed. '
                    'This may cause problems with some functionality'
                )
                log.warn(msg)

                if self._data:
                    log.warn('Continuing with out of date leap second data')
                else:
                    raise ValueError('Could not load leap second data')

    def _update_leap_second_data(self):
        """ Updates the systems leap second information

        Pulls the latest leap second information from
        https://www.ietf.org/timezones/data/leap-seconds.list
        and updates the leapsecond config file.

        Raises:
            ValueError: If the connection to IETF does not return 200
            IOError: If the path to the leap seconds file is not valid
        """

        log.info('Attempting to acquire latest leapsecond data')

        ls_file = ait.config.get(
            'leapseconds.filename',
            os.path.join(ait.config._directory, _DEFAULT_FILE_NAME)
        )

        url = 'https://www.ietf.org/timezones/data/leap-seconds.list'
        r = requests.get(url)

        if r.status_code != 200:
            msg = 'Unable to locate latest timezone data. Connection to IETF failed'
            log.error(msg)
            raise ValueError(msg)

        text = r.text.split('\n')
        lines = [l for l in text if l.startswith('#@') or not l.startswith('#')]

        data = {'valid': None, 'leapseconds': []}
        data['valid'] = datetime.datetime(1900, 1, 1) + datetime.timedelta(seconds=int(lines[0].split('\t')[1]))

        leap = 1
        for l in lines[1:-1]:
            t = datetime.datetime(1900, 1, 1) + datetime.timedelta(seconds=int(l.split('\t')[0]))
            if t < GPS_Epoch:
                continue

            data['leapseconds'].append((t, leap))
            leap += 1

        self._data = data
        with open(ls_file, 'w') as outfile:
            pickle.dump(data, outfile)

if not LeapSeconds: LeapSeconds = UTCLeapSeconds()
