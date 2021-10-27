#!/usr/bin/env python
#
# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2021, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""Decode AIT FSW table binaries"""

import argparse
import os.path
import sys

from ait.core import log, table


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("in_file", help="Input file path")
    parser.add_argument("--out_file", default=None, help="Output file path")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Decode columns into raw values without enumerations",
    )

    args = parser.parse_args()

    file_in = open(args.in_file, "rb")
    out_path = (
        args.out_file
        if args.out_file is not None
        else f"{os.path.splitext(args.in_file)[0]}_decoded.txt"
    )

    # Extract the table upload type (byte 0) from the binary so we can
    # locate the table definition that we need.
    uptype = int.from_bytes(file_in.read(1), byteorder="big")
    file_in.seek(0)
    fswtabdict = table.getDefaultFSWTabDict()
    pos_defn = [map[0] for map in fswtabdict.items() if map[1].uptype == uptype]

    if len(pos_defn) != 1:
        log.error(
            f"Table upload type {uptype} not found in table dictionary. Stopping ..."
        )
        sys.exit(1)

    tbldefn = fswtabdict[pos_defn[0]]
    decoded = tbldefn.decode(file_in=file_in, raw=args.raw)

    out_file = open(out_path, "w")

    # Output our header values in comments so the table can be re-encoded easily
    hdr_row = decoded[0]
    for defn, val in zip(tbldefn.fswheaderdefns, hdr_row):
        print(f"# {defn.name}={val}", file=out_file)

    for row in decoded[1:]:
        print(tbldefn.delimiter.join(map(str, row)), file=out_file)

    out_file.close()

    log.end()


if __name__ == "__main__":
    main()
