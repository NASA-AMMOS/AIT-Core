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
from typing import Tuple

import requests

import ait.core
from ait.core import log

GPS_Epoch = datetime.datetime(1980, 1, 6, 0, 0, 0)
TICs = []
TwoPi = 2 * math.pi

DOY_Format = "%Y-%jT%H:%M:%SZ"
ISO_8601_Format = "%Y-%m-%dT%H:%M:%SZ"
RFC3339_Format = "%Y-%m-%dT%H:%M:%S.%fZ"

_DEFAULT_FILE_NAME = "leapseconds.dat"
LeapSeconds = None


def get_timestamp_utc():
    """Returns the current UTC time in seconds and microseconds."""
    utc = datetime.datetime.utcnow()
    ts_sec = calendar.timegm(utc.timetuple())
    ts_usec = utc.microsecond
    return ts_sec, ts_usec


def get_utc_datetime_doy(days=0, hours=0, minutes=0, seconds=0) -> str:
    """Convert current UTC, plus some optional offset, to ISO 8601 DOY format

    Arguments:
        days (int): Optional days offset from current UTC time
        hours (int): Optional hours offset from current UTC time
        minutes (int): Optional minutes offset from current UTC time
        seconds (int): Optional seconds offset from current UTC time

    Returns:
        String formatted datetime of the form "%Y-%jT%H:%M:%SZ"
    """
    return (
        datetime.datetime.utcnow()
        + datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    ).strftime(DOY_Format)


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
    return (end - TICs.pop()).total_seconds() if len(TICs) else None


def to_gps_week_and_secs(timestamp=None) -> Tuple[int, int]:
    """Convert a timestamp (default current UTC) to GPS weeks / seconds

    Arguments:
        timestamp (optional): An optional datetimme value to convert. Current
            UTC time is used if nothing is provided.

    Returns:
        A tuple of the form (GPS weeks, GPS seconds within week) for the timestamp
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    leap = LeapSeconds.get_GPS_offset_for_date(timestamp)  # type: ignore

    secs_in_week = 604800
    delta = (timestamp - GPS_Epoch).total_seconds() + leap
    seconds = delta % secs_in_week
    week = int(math.floor(delta / secs_in_week))

    return (week, seconds)


def to_gps_seconds(timestamp) -> int:
    """Convert datetime object into number of second since GPS epoch.

    Arguments:
        timestamp (datetime.datetime): The datetime object to convert.

    Return:
        Number of seconds since the GPS epoch which the timestamp represents.

    Examples:

    >>> import datetime
    >>> to_gps_seconds(datetime.datetime(1980, 1, 6))
    0
    >>> to_gps_seconds(datetime.datetime(1980, 1, 7))
    86400
    """
    delta = timestamp - GPS_Epoch
    return (delta.days * 24 * 3600) + delta.seconds


def to_gmst(dt=None) -> float:
    """Convert datetime / Julian date to GMST.

    Converts the given Python datetime or Julian date (float) to
    Greenwich Mean Sidereal Time (GMST) (in radians) using the formula
    from D.A. Vallado (2004).

    See:
        D.A. Vallado, Fundamentals of Astrodynamics and Applications, p. 192
        http://books.google.com/books?id=PJLlWzMBKjkC&lpg=PA956&vq=192&pg=PA192

    Arguments:
        dt (datetime.datetime or float): The datetime or Julian date (as a float)
        to convert to radians.
    """
    if dt is None or type(dt) is datetime.datetime:
        jd = to_julian(dt)
    else:
        jd = dt

    t_ut1 = (jd - 2451545.0) / 36525.0
    gmst = 67310.54841 + (876600 * 3600 + 8640184.812866) * t_ut1
    gmst += 0.093104 * t_ut1 ** 2
    gmst -= 6.2e-6 * t_ut1 ** 3

    # Convert from seconds to degrees, i.e.
    # 86400 seconds / 360 degrees = 240 seconds / degree
    gmst /= 240.0

    # Convert to radians
    gmst = math.radians(gmst) % TwoPi

    if gmst < 0:
        gmst += TwoPi

    return gmst


def to_julian(dt=None):
    """Convert datetime to a Julian date.

    Converts a Python datetime to a Julian date, using the formula from
    Meesus (1991).  This formula is reproduced in D.A. Vallado (2004).

    See:
        D.A. Vallado, Fundamentals of Astrodynamics and Applications, p. 187
        http://books.google.com/books?id=PJLlWzMBKjkC&lpg=PA956&vq=187&pg=PA187

    Arguments:
        dt (datetime.datetime): The datetime to convert.

    Returns:
        The converted Julian date.
    """
    if dt is None:
        dt = datetime.datetime.utcnow()

    if dt.month < 3:
        year = dt.year - 1
        month = dt.month + 12
    else:
        year = dt.year
        month = dt.month

    A = int(year / 100.0)  # noqa
    B = 2 - A + int(A / 4.0)  # noqa
    C = ((dt.second / 60.0 + dt.minute) / 60.0 + dt.hour) / 24.0  # noqa
    jd = int(365.25 * (year + 4716))
    jd += int(30.6001 * (month + 1)) + dt.day + B - 1524.5 + C

    return jd


def to_local_time(seconds: int, microseconds: int = 0) -> datetime.datetime:
    """Convert seconds / microseconds since GPS epoch to local time.

    Converts the given number of seconds since the GPS Epoch (midnight
    on January 6th, 1980) to this computer's local time.

    Arguments:
        seconds: The number of seconds since the GPS epoch.

        microseconds (optional): The number of microseconds of the seconds
            since the GPS epoch.

    Returns:
        The datetime object defined as the GPS epoch + the supplied seconds
            and microseconds.

    Examples:

    >>> to_local_time(0)
    datetime.datetime(1980, 1, 6, 0, 0)

    >>> to_local_time(25 * 86400)
    datetime.datetime(1980, 1, 31, 0, 0)
    """
    delta = datetime.timedelta(seconds=seconds, microseconds=microseconds)
    return GPS_Epoch + delta


def rfc3339_str_to_datetime(datestr: str) -> datetime.datetime:
    """Convert RFC3339 string to datetime.

    Convert a RFC3339-formated date string into a datetime object whil
    attempting to preserve timezone information.

    Arguments:
        datestr: The RFC3339-formated date string to convert to a datetime.

    Returns:
        The datetime object with preserved timezone information for the RFC3339
            formatted string or None if no datestr is None.
    """
    if datestr is None:
        return None
    return datetime.datetime.strptime(datestr, RFC3339_Format).replace(
        tzinfo=datetime.timezone.utc
    )


class UTCLeapSeconds(object):
    def __init__(self):
        self._data = None
        self._load_leap_second_data()

    @property
    def leapseconds(self):
        return self._data["leapseconds"]

    @property
    def valid_date(self):
        return self._data["valid"]

    def is_valid(self):
        return datetime.datetime.now() < self._data["valid"]

    def get_current_gps_offset(self):
        return self._data["leapseconds"][-1][-1]

    def get_gps_offset_for_date(self, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()

        if timestamp < GPS_Epoch:
            e = "The timestamp date is before the GPS epoch"
            raise ValueError(e)

        for offset in reversed(self._data["leapseconds"]):
            # Offsets are stored as a tuple (date, offset)
            # indicating the `date` when `offset` took effect.
            if timestamp >= offset[0]:
                return offset[1]
        else:
            return 0

    def _load_leap_second_data(self):
        ls_file = ait.config.get(
            "leapseconds.filename",
            os.path.join(ait.config._directory, _DEFAULT_FILE_NAME),
        )

        try:
            log.info("Attempting to load leapseconds.dat")
            with open(ls_file, "rb") as outfile:
                self._data = pickle.load(outfile)
            log.info("Loaded leapseconds config file successfully")
        except IOError:
            log.info("Unable to locate leapseconds config file")

        if not (self._data and self.is_valid()):
            try:
                self._update_leap_second_data()
            except ValueError:
                msg = (
                    "Leapsecond data update failed. "
                    "This may cause problems with some functionality"
                )
                log.warn(msg)

                if self._data:
                    log.warn("Continuing with out of date leap second data")
                else:
                    raise ValueError("Could not load leap second data")
        else:
            t = self._data["valid"]
            log_t = t.strftime("%m/%d/%Y")
            log.info("Leapseconds data valid until %s", log_t)

    def _update_leap_second_data(self):
        """Updates the systems leap second information

        Pulls the latest leap second information from
        https://www.ietf.org/timezones/data/leap-seconds.list
        and updates the leapsecond config file.

        Raises:
            ValueError: If the connection to IETF does not return 200
            IOError: If the path to the leap seconds file is not valid
        """

        log.info("Attempting to acquire latest leapsecond data")

        ls_file = ait.config.get(
            "leapseconds.filename",
            os.path.join(ait.config._directory, _DEFAULT_FILE_NAME),
        )

        url = "https://www.ietf.org/timezones/data/leap-seconds.list"
        r = requests.get(url)

        if r.status_code != 200:
            msg = "Unable to locate latest timezone data. Connection to IETF failed"
            log.error(msg)
            raise ValueError(msg)

        text = r.text.split("\n")
        lines = [line for line in text if line.startswith("#@") or not line.startswith("#")]

        data = {"valid": None, "leapseconds": []}
        data["valid"] = datetime.datetime(1900, 1, 1) + datetime.timedelta(
            seconds=int(lines[0].split("\t")[1])
        )

        leap = 1
        for line in lines[1:-1]:
            t = datetime.datetime(1900, 1, 1) + datetime.timedelta(
                seconds=int(line.split("\t")[0])
            )
            if t < GPS_Epoch:
                continue

            data["leapseconds"].append((t, leap))
            leap += 1

        log.info("Leapsecond data processed")

        self._data = data
        with open(ls_file, "wb") as outfile:
            pickle.dump(data, outfile)

        log.info("Successfully generated leapseconds config file")


if not LeapSeconds:
    LeapSeconds = UTCLeapSeconds()
