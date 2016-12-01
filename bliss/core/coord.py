# Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Coordinate Functions

The bliss.core.coord module provides various coordinate manpulation
and transformation functions.
"""

import datetime
import math

from bliss.core import dmc


class Ellipsoid (object):
  """An ellipsoid is the three dimensional analogue of an ellipse, used
  here to approximate the geoid.  See WGS84.

  """
  def __init__ (self, a, b):
    """Creates a new Ellipsoid with the given semimajor and semiminor
    axes.
    """
    self.a   = a
    self.b   = b
    self.a2  = a ** 2
    self.b2  = b ** 2
    self.f   = (a - b) / a
    self.e2  = 1 - (self.b2 / self.a2)
    self.ep2 = (self.a2 - self.b2) / self.b2


WGS84 = Ellipsoid(a=6378137, b=6356752.3142)


def cbrt (x):
  """Returns the cube root of x."""
  if x >= 0: 
    return   math.pow(x     , 1.0 / 3.0)
  else:
    return - math.pow(abs(x), 1.0 / 3.0)


def ecef2geodetic (x, y, z, ellipsoid=None):
  """Convert ECEF coordinates to geodetic using the given ellipsoid
  (defaults to WGS84).

  J. Zhu, "Conversion of Earth-centered Earth-fixed coordinates to
  geodetic coordinates," IEEE Transactions on Aerospace and Electronic
  Systems, vol. 30, pp. 957-961, 1994.

  See https://code.google.com/p/pysatel/source/browse/trunk/coord.py

  """
  if ellipsoid is None:
    ellipsoid = WGS84

  a    = ellipsoid.a
  b    = ellipsoid.b
  a2   = ellipsoid.a2
  b2   = ellipsoid.b2
  f    = ellipsoid.f
  e2   = ellipsoid.e2
  ep2  = ellipsoid.ep2
  r    = math.sqrt(x * x + y * y)
  F    = 54 * b * b * z * z
  G    = r * r + (1 - e2) * z * z - e2 * (a2 - b2)
  C    = (e2 * e2 * F * r * r) / (math.pow(G, 3))
  S    = cbrt(1 + C + math.sqrt(C * C + 2 * C))
  P    = F / (3 * math.pow((S + 1 / S + 1), 2) * G * G)
  Q    = math.sqrt(1 + 2 * e2 * e2 * P)
  r_0  =  -(P * e2 * r) / (1 + Q) + math.sqrt(0.5 * a * a*(1 + 1.0 / Q) - \
            P * (1 - e2) * z * z / (Q * (1 + Q)) - 0.5 * P * r * r)
  U    = math.sqrt(math.pow((r - e2 * r_0), 2) + z * z)
  V    = math.sqrt(math.pow((r - e2 * r_0), 2) + (1 - e2) * z * z)
  Z_0  = b * b * z / (a * V)
  h    = U * (1 - b * b / (a * V))
  lat  = math.atan((z + ep2 * Z_0) / r)
  lon  = math.atan2(y, x)

  return lat, lon, h


def eci2ecef (x, y, z, gmst=None):
  """Converts the given ECI coordinates to ECEF at the given Greenwich
  Mean Sidereal Time (GMST) (defaults to now).
  
  This code was adapted from
  `shashwatak/satellite-js <https://github.com/shashwatak/satellite-js/blob/master/src/coordinate-transforms.js>`_
  and http://ccar.colorado.edu/ASEN5070/handouts/coordsys.doc

  """
  if gmst is None:
    gmst = dmc.toGMST()

  X = (x * math.cos(gmst))    + (y * math.sin(gmst))
  Y = (x * (-math.sin(gmst))) + (y * math.cos(gmst))
  Z = z

  return X, Y, Z


def eci2geodetic (x, y, z, gmst=None, ellipsoid=None):
  """Converts the given ECI coordinates to Geodetic coordinates at the
  given Greenwich Mean Sidereal Time (GMST) (defaults to now) and with
  the given ellipsoid (defaults to WGS84).

  This code was adapted from
  `shashwatak/satellite-js <https://github.com/shashwatak/satellite-js/blob/master/src/coordinate-transforms.js>`_
  and http://www.celestrak.com/columns/v02n03/

  """
  if gmst is None:
    gmst = dmc.toGMST()

  if ellipsoid is None:
    ellipsoid = WGS84

  a    = WGS84.a
  b    = WGS84.b
  f    = WGS84.f
  r    = math.sqrt((x * x) + (y * y))
  e2   = (2 * f) - (f * f)
  lon  = math.atan2(y, x) - gmst
  k    = 0
  kmax = 20
  lat  = math.atan2(z, r)

  while (k < kmax):
    slat = math.sin(lat)
    C    = 1 / math.sqrt( 1 - e2 * (slat * slat) )
    lat  = math.atan2(z + (a * C * e2 * slat), r)
    k   += 1

  z = (r / math.cos(lat)) - (a * C)

  return lat, lon, z
