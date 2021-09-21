#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
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
Usage:
        ait-dict-writer [options] (--tlm | --cmd)

--tlm               Run dictionary processor for Telemetry dictionary.
--cmd               Run dictionary processor for Command dictionary.
--format=<format>   Specify output format. Possible values: csv
                    [Default: csv]
--path=<path>       Output file path.


Description:
        AIT TLM and CMD Dictionary Definitions to Specified Output Format

        Outputs AIT TLM and CMD Dictionary Definitions in Specific output format. Currently supports:
        * TLM -> CSV

        TODO
        * TLM -> TeX
        * CMD -> CSV
        * CMD -> TeX

        Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
        U.S. Government Sponsorship acknowledged.
"""

import sys
import argparse

from ait.core import log, tlm


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add optional command line arguments
    parser.add_argument("--format", default="csv")
    parser.add_argument("--path", default="")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tlm", action="store_true", default=False)
    group.add_argument("--cmd", action="store_true", default=False)

    # Get command line arguments
    args = vars(parser.parse_args())

    # output format for the file
    format = args["format"]

    # output path
    path = args["path"]

    # initialize telemetry dictionary writer
    if args["tlm"]:
        writer = tlm.TlmDictWriter()

    # initialize command dictionary writer
    if args["cmd"]:
        log.error("Not yet supported")
        sys.exit()

    # write to csv
    if format == "csv":
        writer.writeToCSV(output_path=path)
    else:
        log.error("Invalid <format> specified.")


if __name__ == "__main__":
    main()
