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
Provides a command line script for running pcap library functions.
"""

import argparse
import datetime
import os

from ait.core import dmc, log, pcap, util


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    arguments = {
        "--query": {
            "action": "store_true",
            "help": (
                "Creates a new file containing the data from one or "
                "more given pcap files in a given time range. If no "
                "output file name is given, the new file name will "
                "be the name of the first file with the time frame "
                "appended to the name."
            ),
        },
        "--times": {
            "action": "store_true",
            "help": "Lists time ranges available in pcap file(s)",
        },
        "--stime": {
            "default": dmc.GPS_Epoch.strftime(dmc.ISO_8601_Format),
            "help": (
                "Starting time for desired telemetry range in "
                'ISO 8601 Format "YYYY-MM-DDThh:mm:ssZ" (default: '
                "1980-01-06T00:00:00Z)"
            ),
        },
        "--etime": {
            "default": datetime.datetime.now().strftime(dmc.ISO_8601_Format),
            "help": (
                "Ending time for desired telemetry range in "
                'ISO 8601 Format "YYYY-MM-DDThh:mm:ssZ" (default: '
                "the current time; example: 2018-05-23T18:54:31Z)"
            ),
        },
        "--output": {
            "default": None,
            "help": "The name of the output file to be generated",
        },
        "--tol": {
            "type": int,
            "default": 2,
            "help": "Number of seconds allowed between time ranges",
        },
        "file": {
            "nargs": "+",
            "metavar": "</path/to/pcap>",
            "help": "File or directory path containing .pcap file(s)",
        },
    }

    for name, params in arguments.items():
        ap.add_argument(name, **params)

    args = ap.parse_args()

    pcapfiles = []
    for p in args.file:
        if os.path.isdir(p):
            pcapfiles.extend(util.listAllFiles(p, "pcap", True))
        elif os.path.isfile(p):
            pcapfiles.append(p)
        else:
            ap.print_help()
            raise IOError("Invalid pcapfile. Check path and try again: %s" % p)

    log.begin()

    # if using pcap.query
    if args.query:
        stime = args.stime
        etime = args.etime
        output = args.output

        try:
            # Convert start time to datetime object
            starttime = datetime.datetime.strptime(stime, dmc.ISO_8601_Format)

            # Convert end time to datetime object
            endtime = datetime.datetime.strptime(etime, dmc.ISO_8601_Format)

        except ValueError:
            ap.print_help()
            print()
            print()
            raise ValueError(
                "Start and end time must be formatted as YYYY-MM-DDThh:mm:ssZ"
            )

        pcap.query(starttime, endtime, output, *pcapfiles)

    # if using pcap.times
    elif args.times:
        times = pcap.times(pcapfiles, args.tol)

        if len(times) == 1:
            for start, stop in list(times.values())[0]:
                print("%s - %s" % (start, stop))
        else:
            for filename in sorted(times.keys()):
                for start, stop in times[filename]:
                    print("%s: %s - %s" % (filename, start, stop))
    else:
        ap.print_help()

    log.end()


if __name__ == "__main__":
    main()
