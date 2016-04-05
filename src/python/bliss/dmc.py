"""BLISS DeLorean Motor Company (DMC)

The bliss.dmc module provides functions to represent, translate, and
manipulate time, building upon Python's datetime and timedelta data
types.  Originally, this module was named bliss.time, but time.py
conflicts with Python's builtin module of the same name, which causes
all sorts of subtle import issues and conflicts.

Many functions assume the GPS (and ISS) epoch: January 6, 1980 at
midnight.

"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import calendar
import datetime
import math
import time



GPS_Epoch = datetime.datetime(1980, 1, 6, 0, 0, 0)
TICs      = [ ]
TwoPi     = 2 * math.pi


def getTimestampUTC ():
  """getTimestampUTC() -> (ts_sec, ts_usec)

  Returns the current UTC time in seconds and microseconds.
  """
  utc     = datetime.datetime.utcnow()
  ts_sec  = calendar.timegm( utc.timetuple() )
  ts_usec = utc.microsecond
  return ts_sec, ts_usec


def tic ():
  """tic()

  Records the current time for benchmarking purposes.  See also toc().
  """
  global TICs
  begin = datetime.datetime.now()
  TICs.append(begin)


def toc ():
  """toc() -> float | None

  Returns the total elapsed seconds since the most recent tic(), or
  None if tic() was not called.

  Examples:

  >>> import time

  >>> tic()
  >>> time.sleep(1.2)
  >>> elapsed = toc()

  >>> assert abs(elapsed - 1.2) <= 1e-2

  NOTE: The tic() and toc() functions are simplistic and may introduce
  significant overhead, especially in tight loops.  Their use should
  be limited to one-off experiments and rough numbers.  The Python
  profile package (i.e. 'import profile') should be used for serious
  and detailed profiling.
  """
  end = datetime.datetime.now()
  return totalSeconds( end - TICs.pop() ) if len(TICs) else None


def toGPSWeekAndSecs (timestamp=None, leap=16):
  """Converts the given UTC timestamp (defaults to the current time) to
  a two-tuple, (GPS week number, GPS seconds within the week).
  """
  if timestamp is None:
    timestamp = datetime.datetime.utcnow()

  secsInWeek = 604800
  delta      = totalSeconds(timestamp - GPS_Epoch) + leap
  seconds    = delta % secsInWeek
  week       = int( math.floor(delta / secsInWeek) ) 

  return (week, seconds)


def toGPSSeconds (timestamp):
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


def toGMST (dt=None):
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


def toJulian (dt=None):
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


def toLocalTime (seconds, microseconds=0):
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


def totalSeconds (td):
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
