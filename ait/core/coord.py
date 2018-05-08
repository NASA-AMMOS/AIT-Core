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

"""
AIT Coordinate Functions

The ait.core.coord module provides various coordinate manpulation
and transformation functions.
"""

import datetime
import math

from ait.core import dmc


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
