#!/usr/bin/env python

import collections
import datetime
import json
import time

import intervaltree


def parseDOYHMS (s, year):
    """Parses GMT timestamps of the form DOY/HH:MM:SS and returns a Python
    datetime object.
    """
    format = '%Y-%j/%H:%M:%S %Z'
    return datetime.datetime.strptime('%d-%s UTC' % (year, s), format)


def toUnixEpoch (dt):
    return int( time.mktime( dt.timetuple() ) )


def toInterval (ti):
    begin = toUnixEpoch(ti.start)
    end   = toUnixEpoch(ti.stop) + 1
    return intervaltree.Interval(begin, end, ti)


class TimeInterval:
    """TimeInterval

    A TimeInterval represents an interval of time beginning with a
    start date and time and ending with a stop date and time, both
    inclusive.  Start and stop times are Python datetime objects.

    Subclasses are used to represent specific types of intervals, e.g.
    EclipseIntervals, AreaIntervals, SZAIntervals, etc.
    """

    def __init__ (self, start, stop):
        """Creates a new TimeInterval with the given start / stop times."""
        self._start = start
        self._stop  = stop

    def __lt__ (self, other):
        return self._start.__lt__(other._start)

    def __le__ (self, other):
        return self._start.__le__(other._start)

    def __eq__ (self, other):
        return self._start.__eq__(other._start)

    def __ne__ (self, other):
        return self._start.__ne__(other._start)

    def __gt__ (self, other):
        return self._start.__gt__(other._start)

    def __ge__ (self, other):
        return self._start.__ge__(other._start)

    def __contains__ (self, obj):
        if isinstance(obj, datetime.datetime):
            return obj >= self.start and obj <= self.stop
        elif isinstance(obj, TimeInterval):
            return not (obj.stop < self.start or obj.start > self.stop)
        else:
            return False

    def __repr__ (self):
        return '%s<start=%s, stop=%s, duration=%s>' % (
            self.__class__.__name__, self.start.isoformat(),
            self.stop.isoformat(), self.duration)

    @property
    def duration (self):
        """Duration of this interval as a Python timedelta."""
        return self.stop - self.start

    @property
    def start (self):
        """Start of this interval as a Python datetime."""
        return self._start

    @property
    def stop (self):
        """End of this interval as a Python datetime."""
        return self._stop



class TimeIntervalTree:

    def __init__ (self):
        self._tree = intervaltree.IntervalTree()

    def __contains__ (self, obj):
        if isinstance(obj, datetime.datetime):
            return self._tree.overlaps( toUnixEpoch(obj) )
        elif isinstance(obj, TimeInterval):
            return toInterval(obj) in self._tree
        else:
            return False

    def __iter__ (self):
        for iv in self._tree:
            yield iv.data

    def __len__ (self):
        return len(self._tree)

    def add (self, ti):
        self._tree.add( toInterval(ti) )

    def search (self, obj, end=None, envelop=False):
        if isinstance(obj, datetime.datetime) and end is None:
            begin = toUnixEpoch(obj)
            end   = end
        elif isinstance(obj, datetime.datetime) and \
             isinstance(end, datetime.datetime):
            begin = toUnixEpoch(obj)
            end   = toUnixEpoch(end)
        elif isinstance(obj, TimeInterval):
            begin = toUnixEpoch(obj.start)
            end   = toUnixEpoch(obj.stop)
        else:
            return [ ]

        intervals = self._tree.search(begin, end, strict=envelop)
        return sorted(iv.data for iv in intervals)


class AreaTargetInterval (TimeInterval):
    """AreaTargetInterval

    AreaTarget Intervals are TimeIntervals which include the area
    mapping / target name.
    """

    def __init__ (self, start, stop, name):
        """Creates a new AreaTargetInterval with the given start / stop times
        and area mapping / target name.
        """
        TimeInterval.__init__(self, start, stop)
        self._name = name

    def __repr__ (self):
        return '%s<start=%s, stop=%s, duration=%s, name="%s">' % (
            self.__class__.__name__, self.start.isoformat(),
            self.stop.isoformat(), self.duration, self.name)

    @property
    def name (self):
        """Area mapping / target name observed in this interval."""
        return self._name


class EclipseInterval (TimeInterval):
    pass


class SZA75Interval (TimeInterval):
    pass


class SZA85Interval (TimeInterval):
    pass


class GroundPathPoint:
    """GroundPathPoint

    GroundPathPoints are the core constituents of a GroundPath.  Each
    GroundPathPoint contains a location (latitude, longitude), the
    date and time (Python datetime) at which the point is nadir with
    respect to the ISS instrument boresight, and whether the point is
    on land or water.
    """

    def __init__ (self, time, lat, lon, land=False, mode=None):
        """Creates a new GroundPathPoint."""
        self._time = time
        self._lat  = lat
        self._lon  = lon
        self._land = land
        self._mode = mode

    def __repr__ (self):
        return '%s(time=%s, lat=%f, lon=%f, land=%s, mode=%s)' % (
            self.__class__.__name__, self.time.isoformat(), self.lat,
            self.lon, self.land, self._mode)

    @property
    def land (self):
        """Indicates whether this point is on land."""
        return self._land

    @property
    def lat (self):
        """Latitude of this point."""
        return self._lat

    @property
    def lon (self):
        """Longitude of this point."""
        return self._lon

    @property
    def mode (self):
        return self._mode

    @mode.setter
    def mode (self, mode):
        self._mode = mode

    @property
    def time (self):
        """Date and time at which this opint is nadir with respect to the ISS
        instrument boresight.
        """
        return self._time

    @property
    def water (self):
        """Indicates whether this point is on water."""
        return not self.land


class GroundPath:
    """GroundPath

    A GroundPath is a collection of nadir GroundPathPoints which are
    iterable, indexable, and may be subsetted.  Subsetting is
    efficient and simply references the parent GroundPath, rather than
    duplicating its GroundPathPoints.
    """

    def __init__ (self, parent=None, sliceObj=None):
        """Creates a new GroundPath.  To subset an existing GroundPath, pass
        it as the first argument (the so-called parent GroundPath),
        followed by the subset start and stop indices as a Python
        slice.
        """
        self._parent = parent
        self._points = [ ]
        self._slice  = sliceObj

    def __getitem__ (self, obj):
        if isinstance(obj, int):
            return self.points[obj]
        elif isinstance(obj, slice):
            return GroundPath(self, obj)

    def __iter__ (self):
        return self.points.__iter__()

    def __len__ (self):
        return len(self.points)

    def __repr__ (self):
        return '<%s: len(points)=%d, first=%s, last=%s, duration=%s>' % (
            self.__class__.__name__, len(self), self.first, self.last,
            self.duration)

    @property
    def duration (self):
        """Duration of this GroundPath as a Python timedelta."""
        if len(self.points) > 0:
            duration = self.last.time - self.first.time
        else:
            duration = datetime.timedelta(seconds=0)

        return duration

    @property
    def points (self):
        """Points along this GroundPath."""
        if self._parent is not None:
            return self._parent.points[self._slice]
        else:
            return self._points

    @property
    def first (self):
        """First point in this GroundPath."""
        return self.points[0] if len(self.points) > 0 else None

    @property
    def last (self):
        """Last point in this GroundPath."""
        return self.points[-1] if len(self.points) > 0 else None

    def append (self, p):
        """Appends the given GroundPathPoint to this GroundPath."""
        self._points.append(p)

    def crossings (self):
        """Returns a list of GroundPaths, each one running from one equator
        crossing to the next.
        """
        start = 0
        index = 1
        prev  = self[start]
        next  = self[index]

        while index < len(self.points) - 1:
            if prev.lat < 0 and next.lat >= 0:
                yield self[start:index + 1]
                start = index
            index = index + 1
            prev  = next
            next  = self[index]

        yield self[start:index]



class PointingReport:
    """PointingReport

    A PoiningReport parses and represents various aspects of JSC
    Attitude and Pointing reports.  This parent class provides parsing
    functions common to all reports.
    """
    Separator = '=' * 75

    def __init__ (self, filename):
        """Creates a new PointingReport and loads the given filename."""
        self._load(filename)

    def _load (self, filename):
        """Loads the PointingReport contained in filename

        Subclasses should override.
        """
        self._filename = filename

    def _parseHeader (self, stream):
        """Parses a JSC Attitude and Pointing Report header (or subheader)
        from the given file object (stream) and returns a dictionary
        with the following keys (and corresponding values):

            * START_GMT
            * STOP_GMT
            * NAME
            * ELEVATION
        """
        header = { }
        name   = None
        value  = None

        for line in stream:
            line = line.strip()
            if line.startswith(PointingReport.Separator):
                break
            elif (line.find('START GMT:') != -1 or
                  line.find('STOP  GMT:') != -1):
                tokens = line.split()
                name   = '_'.join(tokens[2:4]).replace(':', '')
                value  = parseDOYHMS( tokens[5], year=int(tokens[4]) )
            elif line.find('NAME:') != -1:
                start = line.find('NAME:') + 5
                stop  = line.find('ELEVATION:')
                name  = 'NAME'
                value = line[start:stop].strip()
            if name is not None:
                header[name] = value
                name  = None
                value = None

        return header

    def _skipPastNextSep (self, stream):
        """Skips past the next PointingReport.Separator in the given file
        object (stream).
        """
        for line in stream:
            if line == '':
                return False
            elif line.startswith(PointingReport.Separator):
                return True

    @property
    def filename (self):
        """The filename for this PointingReport."""
        return self._filename


class AreasReport (PointingReport):
    """AreasReport

    Once loaded, an AreasReport provides access to its
    AreaTargetIntervals.
    """

    def __init__ (self, filename):
        """Creates a new AreasReport and loads the given filename."""
        self._areas = TimeIntervalTree()
        PointingReport.__init__(self, filename)

    def __repr__ (self):
        return '<%s: filename="%s", len(areas)=%d>' % (
            self.__class__.__name__, self.filename, len(self.areas))

    def _load (self, filename):
        """Loads the AreasReport contained in filename."""
        PointingReport._load(self, filename)
        
        with open(filename) as stream:
            while self._skipPastNextSep(stream):
                self._header = self._parseHeader(stream)
                year         = self._header['START_GMT'].year
                name         = self._header['NAME']

                for line in stream:
                    line   = line.strip()
                    tokens = line.split()

                    if line.startswith('W/IN 50DEG'):
                        aos  = parseDOYHMS(tokens[2], year)
                        los  = parseDOYHMS(tokens[3], year)
                        area = AreaTargetInterval(aos, los, name)
                        self._areas.add(area)
                    elif line.startswith(PointingReport.Separator):
                        break

    @property
    def areas (self):
        """AreaTargetIntervals described in this AreasReport."""
        return self._areas


class WorldReport (PointingReport):
    """WorldReport

    Once loaded, a WorldReport provides access to its GroundPath.
    """

    def __init__ (self, filename):
        """Creates a new WorldReport and loads the given filename."""
        PointingReport.__init__(self, filename)

    def __repr__ (self):
        return '<%s: filename="%s", path=%s>' % (
            self.__class__.__name__, self.filename, self.path)

    def _load (self, filename):
        """Loads the WorldReport contained in filename."""
        PointingReport._load(self, filename)
        self._path = GroundPath()

        with open(filename) as stream:
            self._skipPastNextSep(stream)
            self._header = self._parseHeader(stream)
            year         = self._header['START_GMT'].year

            for line in stream:
                line = line.strip()

                if line.startswith('GMT'):
                    continue
                
                tokens = line.split()
                time   = parseDOYHMS( tokens[0], year )
                lat    = float( tokens[1] )
                lon    = float( tokens[2] )
                land   = False

                if len(tokens) > 3:
                    land = (tokens[3] == 'INSIDE')            

                self._path.append( GroundPathPoint(time, lat, lon, land) )

    @property
    def path (self):
        """GroundPath described in this WorldReport."""
        return self._path


class SZAReport (PointingReport):
    """SZAReport

    Once loaded, an SZAReport provides access to its EclipseIntervals
    and SZAIntervals.
    """

    def __init__ (self, filename):
        """Creates a new SZAReport and loads the given filename."""
        self._eclipses = TimeIntervalTree()
        self._szangles = TimeIntervalTree()
        PointingReport.__init__(self, filename)

    def __repr__ (self):
        return '<%s: filename="%s", len(eclipses)=%d, len(szangles)=%d>' % (
            self.__class__.__name__, self.filename, len(self.eclipses),
            len(self.szangles))

    def _load (self, filename):
        """Loads the SZAReport contained in filename."""
        PointingReport._load(self, filename)
        prevLOS = None
        
        with open(filename) as stream:
            self._skipPastNextSep(stream)
            self._header = self._parseHeader(stream)
            year         = self._header['START_GMT'].year

            for line in stream:
                line   = line.strip()
                tokens = line.split()

                if line.startswith('View'):
                    aos = parseDOYHMS(tokens[4], year)
                    los = parseDOYHMS(tokens[5], year)
                    if prevLOS is not None:
                        self._eclipses.add( EclipseInterval(prevLOS, aos) )
                    prevLOS = los
                elif line.startswith('85DEG'):
                    aos = parseDOYHMS(tokens[2], year)
                    los = parseDOYHMS(tokens[3], year)
                    self._szangles.add( SZA85Interval(aos, los) )

    @property
    def eclipses (self):
        """EclipseIntervals described in this SZAReport."""
        return self._eclipses

    @property
    def szangles (self):
        """SZAIntervals described in this SZAReport."""
        return self._szangles
