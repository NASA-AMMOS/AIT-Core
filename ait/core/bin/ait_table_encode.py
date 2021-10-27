#!/usr/bin/env python
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
"""Encode AIT FSW tables for upload """
import argparse
import os.path
import sys

from ait.core import log
from ait.core import table


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "table_type",
        choices=list(table.getDefaultDict().keys()),
        help=(
            f"The type of table being encoded. One of {list(table.getDefaultDict().keys())}"
        ),
    )

    parser.add_argument("in_file", help="Input file path")
    parser.add_argument("--out_file", help="Output file path")

    args = parser.parse_args()

    fswtabdict = table.getDefaultFSWTabDict()
    tbldefn = fswtabdict[args.table_type]

    out_path = (
        args.out_file
        if args.out_file is not None
        else f"{os.path.splitext(args.in_file)[0]}.bin"
    )

    with open(args.in_file, "r") as in_file:
        encoded = tbldefn.encode(file_in=in_file)

    # Verify that the encoded table is the proper size. If it's too small we need
    # to pad it out. If it's too big then the user needs to remove some of the
    # entires.
    enc_len = len(encoded)
    if enc_len < tbldefn.size:
        encoded += bytearray(tbldefn.size - enc_len)
    elif enc_len > tbldefn.size:
        log.error(
            f"Encoded {tbldefn.name} table is too large. "
            f"Expected size: {tbldefn.size} bytes. Encoded size: {enc_len} bytes."
            "Please remove some entires from the table."
        )
        sys.exit(1)

    with open(out_path, "wb") as out_file:
        out_file.write(encoded)

    log.end()


if __name__ == "__main__":
    main()
