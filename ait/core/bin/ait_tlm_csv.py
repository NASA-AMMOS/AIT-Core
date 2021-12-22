#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
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
Usage: ait-tlm-csv [options] <pcap-filename>

Reads the telemetry contained in the given pcap file and writes it in a csv file.

  -h, --help            show this help message and exit
  --all                 output all fields/values
  --csv </path/to/output/csv>
                        Output as CSV with filename
  --fields </path/to/fields/file>
                        path to the file containing all fields to query, separated by newline.
  --packet PACKET       field names to query, separated by space
  --time_field TIME_FIELD
                        Time field to use for time range comparisons. Ground receipt time will be used if nothing is
                        specified.
  --stime STIME         Datetime in file to start collecting the data values. Defaults to beginning of pcap. Expected
                        format: YYYY-MM-DDThh:mm:ssZ
  --etime ETIME         Datetime in file to end collecting the data values. Defaults to end of pcap. Expected format:
                        YYYY-MM-DDThh:mm:ssZ

Examples:

  $ ait-tlm-csv --packet 1553_HS_Packet --all --csv './ait-tlm-csv-output.csv' \
                ./ait-tlm-csv-input.pcap
"""


import argparse
import csv
import sys
import os
from datetime import datetime

from ait.core import log, tlm, pcap, dmc


"""Parses 1553 telemetry into CSV file."""


def main():
    log.begin()

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--all", action="store_true", help="output all fields/values")

    parser.add_argument(
        "--csv",
        default="output.csv",
        metavar="</path/to/output/csv>",
        help="Output as CSV with filename",
    )

    parser.add_argument(
        "--fields",
        metavar="</path/to/fields/file>",
        help="path to the file containing all fields to query, separated by newline.",
    )

    parser.add_argument(
        "--packet", required=True, help="Packet name from telemetry dictionary specified in config file."
    )

    parser.add_argument(
        "--time_field",
        help=(
            "Time field to use for time range comparisons. Ground receipt time "
            "will be used if nothing is specified."
        ),
    )

    parser.add_argument(
        "--stime",
        help=(
            "Datetime in file to start collecting the data values. Defaults to "
            "beginning of pcap. Expected format: YYYY-MM-DDThh:mm:ssZ"
        ),
    )

    parser.add_argument(
        "--etime",
        help=(
            "Datetime in file to end collecting the data values. Defaults to end "
            "of pcap. Expected format: YYYY-MM-DDThh:mm:ssZ"
        ),
    )

    parser.add_argument(
        "pcap", nargs="*", help=("PCAP file(s) containing telemetry packets")
    )

    args = parser.parse_args()

    args.ground_time = True
    if args.time_field is not None:
        args.ground_time = False

    tlmdict = tlm.getDefaultDict()
    defn = None

    try:
        if tlmdict is not None:
            defn = tlmdict[args.packet]
    except KeyError:
        log.error('Packet "%s" not defined in telemetry dictionary.' % args.packet)
        log.end()
        sys.exit(2)

    if not args.all and args.fields is None:
        log.error(
            "Must provide fields file with --fields or specify that all fields should be queried with --all"
        )
        log.end()
        sys.exit(2)

    if args.all:
        fields = [flddefn.name for flddefn in defn.fields]
    else:
        # Parse the fields file into a list
        with open(args.fields, "r") as stream:
            fields = [fldname.strip() for fldname in stream.readlines()]

    not_found = False

    # TODO Rework this into the CSV generation. Not here.
    # Duplicating effort
    for fldname in fields:
        raw = fldname.split(".")
        if fldname not in defn.fieldmap and (
            len(raw) == 2 and raw[0] != "raw" or raw[1] not in defn.fieldmap
        ):
            not_found = True
            log.error('No telemetry point named "%s"' % fldname)

    if not_found:
        log.end()
        sys.exit(2)

    if args.stime:
        start = datetime.strptime(args.stime, dmc.ISO_8601_Format)
    else:
        start = dmc.GPS_Epoch

    if args.etime:
        stop = datetime.strptime(args.etime, dmc.ISO_8601_Format)
    else:
        stop = datetime.utcnow()

    # Append time to beginning of each row
    if not args.ground_time:
        fields.insert(0, args.time_field)
    else:
        fields.insert(0, "Ground Receipt Time")

    csv_file = None
    csv_writer = None
    npackets = 0
    if args.csv:
        csv_file = open(args.csv, "w")
        csv_writer = csv.writer(csv_file)

    output(csv_writer, fields)

    # If we're comparing off ground receipt time we need to drop the header label to avoid
    # indexing errors when processing the fields.
    if args.ground_time:
        fields = fields[1:]

    rowcnt = 0

    for filename in args.pcap:
        log.debug("Processing %s" % filename)

        with pcap.open(filename, "rb") as stream:
            header, data = stream.read()

            while data:
                packet = tlm.Packet(defn, data)

                comp_time = (
                    header.timestamp
                    if args.ground_time
                    else getattr(packet, args.time_field)
                )
                if start < comp_time < stop:
                    row = []
                    for field in fields:
                        try:
                            # check if raw value requested
                            _raw = False
                            names = field.split(".")
                            if len(names) == 2 and names[0] == "raw":
                                field = names[1]
                                _raw = True

                            field_val = packet._getattr(field, raw=_raw)

                            if hasattr(field_val, "name"):
                                field_val = field_val.name
                            else:
                                field_val = str(field_val)

                        except KeyError:
                            log.debug("%s not found in Packet" % field)
                            field_val = None
                        except ValueError:
                            # enumeration not found. just get the raw value
                            field_val = packet._getattr(field, raw=True)

                        row.append(field_val)

                    if args.ground_time:
                        row = [comp_time] + row

                    rowcnt += 1
                    output(csv_writer, row)

                npackets += 1
                header, data = stream.read()

    log.debug("Parsed %s packets." % npackets)

    csv_file.close()

    if rowcnt == 0:
        os.remove(args.csv)

    log.end()


def output(csv_writer, row):
    if csv_writer:
        csv_writer.writerow(row)
    else:
        print(" ".join(row))


if __name__ == "__main__":
    main()
