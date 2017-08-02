#!/usr/bin/env python

'''
Usage:
  bliss-orbits predicts <filename> <start-time> [<stop-time>] [options]
  bliss-orbits actuals  <filename> <start-time> [<stop-time>] [options]

Arguments:
  filename     An JSC ISS Attitude and Pointing Nadir report (predicts), or
               An ISS Ephemeris from BAD data (HOSC NRT .sto file) (actuals)
  start-time   Restrict output to the date/time range
  stop-time    Restrict output to the date/time range

Options:
  -o output    Output filename
  -h --help    Show this screen
  --version    Show version

Description:

  predicts filename (e.g. JSC_Pointing_Report_Nadir_2015-296-299.txt)

    Processes a JSC ISS Attitude and Pointing Nadir report and
    produces a predicted set of ISS orbit times and orbit numbers (see
    NOTE below).  Orbits are defined from one ascending node equator
    crossing to the next.

    NOTE: JSC ISS Attitude and Pointing reports have a time resolution
    of 15 seconds.  One consequence of this is reported time intervals
    should not be considered completely inclusive, instead use either
    (start, stop] or [start, stop).

  actuals filename (e.g. ISS_BAD_Eph_2015-295-299.sto)

    Processes ISS ephemeris and produces a set of as-flown ISS orbit
    times and orbit numbers.  Orbits are defined from one ascending
    node equator crossing to the next.

  By default, output is sent to standard output.  Use -o output to
  write to a file instead.

  Date and time resrictions may be "today" only, by day of year (DOY),
  date, or time range (with start and stop times formatted as
  YYYY-MM-DDTHH:MM:SS).

  If only start-time is given, it may be either the word "today", a 1-3
  digit Day Of Year (DOY) number, or a YYYY-MM-DD formatted date.

Example:

  $ bliss-orbits predicts JSC_Pointing_Report_World_2015_300_321.txt 320
  2015-11-15T22:13:18.005 | COMMAND  | ./bliss-orbits ...
  2015-11-15T22:13:18.005 | INFO     | Reading JSC Pointing nadir report ...
  2015-11-15T22:13:18.966 | INFO     | Found    324 total orbits.
  2015-11-15T22:13:18.969 | INFO     | Found     15 total orbits for today.

  2015-11-16T01:01:00    2015-11-16T02:33:30    000294
  2015-11-16T02:33:30    2015-11-16T04:06:00    000295
  2015-11-16T04:06:00    2015-11-16T05:38:45    000296
  2015-11-16T05:38:45    2015-11-16T07:11:15    000297
  2015-11-16T07:11:15    2015-11-16T08:43:45    000298
  2015-11-16T08:43:45    2015-11-16T10:16:15    000299
  2015-11-16T10:16:15    2015-11-16T11:48:45    000300
  2015-11-16T11:48:45    2015-11-16T13:21:15    000301
  2015-11-16T13:21:15    2015-11-16T14:53:45    000302
  2015-11-16T14:53:45    2015-11-16T16:26:15    000303
  2015-11-16T16:26:15    2015-11-16T17:59:00    000304
  2015-11-16T17:59:00    2015-11-16T19:31:30    000305
  2015-11-16T19:31:30    2015-11-16T21:04:00    000306
  2015-11-16T21:04:00    2015-11-16T22:36:30    000307
  2015-11-16T22:36:30    2015-11-17T00:09:00    000308

  2015-11-15T22:13:18.969 | COMMAND  | done.
'''


import datetime
import re
import sys

import argparse

import bliss

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Add optional command line arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--predicts', type=str, choices=['predicts'])
    group.add_argument('--actuals', type=str, choices=['actuals'])

    parser.add_argument('--filename', type=str, default=None)
    parser.add_argument('--start', type=str, default=None)
    parser.add_argument('--stop', type=str, default=None)
    parser.add_argument('-o', '--output', type=str, default=None)

    # Get command line arguments
    args = vars(parser.parse_args())
    predicts  = args['predicts']
    actuals   = args['actuals']
    filename  = args['filename']
    outname   = args['output']
    start     = args['start']
    stop      = args['stop']
    today     = start.lower() == 'today'
    date      = None
    doy       = None

    if re.match('\d{4}-\d{2}-\d{2}$', start):
        date = start

    if re.match('\d{1,3}$', start):
        doy = start

    now = datetime.datetime.utcnow()
    day = True


    # Parse and determine start and stop filter times.
    try:
        if start and stop:
            field  = 'Start time'
            format = 'YYYY-MM-DDTHH:MM:SS'
            value  = start
            start  = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S')

            field  = 'Stop time'
            value  = stop
            stop   = datetime.datetime.strptime(stop , '%Y-%m-%dT%H:%M:%S')

            day    = False

        elif today:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        elif doy:
            field = 'DOY'
            start = datetime.datetime.strptime(doy, '%j').replace(year=now.year)

        elif date:
            format = 'YYYY-MM-DD'
            field  = 'Date'
            value  = date
            start  = datetime.datetime.strptime(date, '%Y-%m-%d')

        else:
            start = None
            stop  = None
            day   = False

        if day:
            stop = start.replace(hour=23, minute=59, second=59, microsecond=999999)

    except ValueError, e:
        if field == 'DOY':
            bliss.core.log.error('DOY "%s" is not a number or in range [0 366].', doy)
        else:
            msg = '%s "%s" does not match format %s.'
            bliss.core.log.error(msg, field, value, format)
        bliss.core.log.end()

    # Ensure output file can be opened for writing.
    if outname:
        try:
            output = open(outname, 'wt')
            stdout = False
        except IOError, e:
            bliss.core.log.error('Could not open "%s" for writing.', outname)
            bliss.core.log.end()
            sys.exit(1)
    else:
        output = sys.stdout
        stdout = True

    # Generate and filter orbits.
    bliss.core.log.begin()

    if predicts:
        bliss.core.log.info('Reading JSC Pointing World report "%s".', filename)
        report    = bliss.iss.pointing.WorldReport(filename)
        path      = report.path
    elif actuals:
        bliss.core.log.info('Reading ISS Ephemeris "%s".', filename)
        report    = bliss.iss.eph.EphemeridesReport(filename)
        path      = bliss.iss.eph.toGroundPath(report.ephemerides)

    crossings = list( path.crossings() )

    bliss.core.log.info('Found %6d total orbits.', len(crossings))

    if start is None and stop is None:
        filtered = enumerate(crossings)
    else:
        filtered = [ (orbit, c) for (orbit, c) in enumerate(crossings)
                         if c.first.time >= start and c.first.time < stop ]
        msg      = 'Found %6d total orbits for ' % len(filtered)

        if today:
            msg += 'today.'
            bliss.core.log.info(msg)
        elif doy:
            msg += 'DOY %03d.'
            bliss.core.log.info(msg, int(doy))
        elif date:
            msg += 'for date %s.'
            bliss.core.log.info(msg, start.strftime('%Y-%m-%d'))
        elif start and stop:
            msg += 'for date/time range [%s, %s)'
            bliss.core.log.info(msg, start.isoformat(), stop.isoformat())

    if stdout:
        print
    else:
        bliss.core.log.info('Writing orbits to "%s".' % outname)

    for (orbit, c) in filtered:
        begin = c.first.time + datetime.timedelta(seconds=1)
        begin = begin.strftime('%Y-%m-%dT%H:%M:%S')
        end   = c.last.time.strftime('%Y-%m-%dT%H:%M:%S')
        delta = (c.last.time - c.first.time).seconds / 60.
        output.write('%s\t%s\t%f\t%06d\n' % (begin, end, delta, orbit))

    if stdout:
        print

    if output != sys.stdout:
        output.close()

    bliss.core.log.end()

if __name__ == '__main__':
    main()
