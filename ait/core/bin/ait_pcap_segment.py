#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
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
Segments one or more pcap files into multiple pcap files, according to
a threshold number of bytes, packets, and/or seconds.  New segment
filenames are determined based on a strftime(3) format string and
the timestamp of the first packet in the file.

When segmenting based on time (-s, --seconds), for file naming and
interval calculation purposes ONLY, the timestamp of the first packet
in the file is rounded down to nearest even multiple of the number of
seconds.  This yields nice round number timestamps for filenames.  For
example:

    ait-pcap-segment -s 3600 %Y%m%dT%H%M%S.pcap foo.pcap bar.pcap

If the first packet written to a file has a time of 2017-11-23
19:28:58, the file will be named:

    20171123T190000.pcap

And a new file will be started when a packet is written with a
timestamp that exceeds 2017-11-23 19:59:59.
"""


import argparse
import datetime
import os

from ait.core import log, pcap


def main():
    ap = argparse.ArgumentParser(
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    ap.add_argument('-n', '--dry-run',
        action = 'store_true',
        help   = 'Dry run; do not actually write files',
    )

    ap.add_argument('-b', '--bytes',
        help    = 'Segment evey B bytes',
        metavar = 'B',
        type    = int
    )

    ap.add_argument('-p', '--packets',
        help    = 'Segment evey P packets',
        metavar = 'P',
        type    = int
    )

    ap.add_argument('-s', '--seconds',
        help    = 'Segment when first and last pcap timestamps span S seconds',
        metavar = 'S',
        type    = int
    )

    ap.add_argument('format',
        help = 'Segment filename (should include strftime(3) time format)'
    )

    ap.add_argument('file',
        nargs = '+',
        help  = 'Packet Capture (.pcap) file(s)'
    )

    args = ap.parse_args()

    if args.bytes is None and args.packets is None and args.seconds is None:
        msg = 'At least one of -b, -p, or -s is required.'
        ap.error(msg)

    try:
        pcap.segment(filenames = args.file,
                     format    = args.format,
                     nbytes    = args.bytes,
                     npackets  = args.packets,
                     nseconds  = args.seconds,
                     dryrun    = args.dry_run)

    except KeyboardInterrupt:
        log.info('Received Ctrl-C.  Aborting pcap segmentation.')

    except IOError as e:
        log.error(str(e))

    log.end()

if __name__ == '__main__':
  main()
