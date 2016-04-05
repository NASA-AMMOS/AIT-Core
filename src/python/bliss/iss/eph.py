"""
ISS Ephemeris

The bliss.iss.eph module provides a method to parse HOSC Near Real
Time (NRT) queries of ISS BAD data containing the following ISS
Ephemeris fields:

    - LADP06MD2378W:       GPS Integer Seconds (since GPS Epoch)
    - LADP06MD2380W:       GPS Fraction of a second
    - LADP06MD2395H-2397H: GPS Position (m) (J2000)
    - LADP06MD2399R-2401R: GPS Velocity (m) (J2000)
    - LADP06MD2382U-2385U: J2000-to-Body Quaternions

The Program Unique Identifiers (PUIs) (i.e. LADP06MDXXXXX) are defined
in ISS SSP 50540: Software Interface Definition Document: Broadcast
Ancillary Data (BAD).
"""

"""
Authors: Ben Bornstein

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.   
"""


import datetime

from bliss     import coord
from bliss     import dmc
from bliss.iss import pointing


def toGroundPath (ephemerides):
    """Converts ISS ephemerides to an geodetic nadir GroundPath."""
    path = pointing.GroundPath()

    for eph in ephemerides:
        lat, lon, alt = coord.eci2geodetic(*eph.pos, gmst=dmc.toGMST(eph.time))
        point         = pointing.GroundPathPoint(eph.time, lat, lon)
        path.append(point)

    return path
    


class Ephemeris (object):
    """Ephemeris

    Holds coincident ISS time, position, velocity, and attitude data.
    """

    __slots__ = ('_att', '_pos', '_time', '_vel')


    def __init__ (self, time=None, pos=None, vel=None, att=None):
        self._time = time
        self._pos  = tuple(pos)
        self._vel  = tuple(vel)
        self._att  = tuple(att)


    def __repr__ (self):
        return '%s(time=%s, pos=%s, vel=%s, att=%s)' % (
            self.__class__.__name__, self.time, self.pos, self.vel, self.att)


    @property
    def att (self):
        """Ephemeris attidue (J2000-to-ISS Body quaternion)."""
        return self._att


    @property
    def pos (self):
        """Ephemeris position (x, y, z) (m) (J2000)."""
        return self._pos


    @property
    def time (self):
        """Time of this Ephemeris."""
        return self._time


    @property
    def vel (self):
        """Ephemeris velocity (dx, dy, dz)/dt (m/s) (J2000)."""
        return self._vel



class EphemeridesReport (object):
    """EphemeridesReport

    An EphemeridesReport represents a specific HOSC Near Real Time
    (NRT) query result containing a collection of ISS ephemeris data,
    telemetered at 1 HZ.
    """

    def __init__ (self, filename, start=None, stop=None):
        """Creates a new ISS Ephemeris Report and loads the given HOSC Near
        Real Time (NRT) query result filename (.sto file).

        If start and/or stop times are given, only ephemeris within
        the given time range are loaded.
        """
        self._ephemerides = [ ]
        self._load(filename, start, stop)


    def __iter__ (self):
        return self.ephemerides.__iter__()


    def __len__ (self):
        return len(self.ephemeris)


    def __repr__ (self):
        return '<%s: filename="%s", len(ephemerides)=%d>' % (
            self.__class__.__name__, self.filename, len(self.ephemerides))


    def _load (self, filename, start=None, stop=None):
        """Loads the EphemeridesReport contained in filename.

        If start and/or stop times are given, only ephemeris within
        the given time range are loaded.
        """
        self._filename = filename
        format         = '%Y:%j:%H:%M:%S %Z'

        with open(filename, 'rt') as stream:
            for line in stream.readlines():
                line = line.strip()
                if line.startswith('#Data\t'):
                    cols = [ s.strip() for s in line.split('\t') ]
                    time = datetime.datetime.strptime(cols[1] + ' UTC', format)
                
                    if start is not None and time < start:
                        continue

                    if stop is not None and time > stop:
                        break

                    self.ephemerides.append(
                        Ephemeris(
                            time,
                            pos = map(float, cols[ slice( 6, 11, 2) ]),
                            vel = map(float, cols[ slice(12, 17, 2) ]),
                            att = map(float, cols[ slice(18, 25, 2) ])
                        )
                    )


    @property
    def duration (self):
        """Duration of this EphemeridesReport as a Python timedelta."""
        if len(self.ephemerides) > 0:
            duration = self.last.time - self.first.time
        else:
            duration = datetime.timedelta(seconds=0)

        return duration


    @property
    def ephemerides (self):
        """A list of Ephemeris in this EphemeridesReport."""
        return self._ephemerides


    @property
    def filename (self):
        """The filename for this EphemeridesReport."""
        return self._filename


    @property
    def first (self):
        """First Ephemeris in this EphemeridesReport."""
        return self.ephemerides[0] if len(self.ephemerides) > 0 else None


    @property
    def last (self):
        """Last Ephemeris in this EphemeridesReport."""
        return self.ephemerides[-1] if len(self.ephemerides) > 0 else None
