#!/usr/bin/env python
'''
Usage:
        bliss-dict-writer [options] (--tlm | --cmd)

--tlm               Run dictionary processor for Telemetry dictionary.
--cmd               Run dictionary processor for Command dictionary.
--format=<format>   Specify output format. Possible values: csv
                    [Default: csv]
--path=<path>       Output file path.


Description:
        BLISS TLM and CMD Dictionary Definitions to Specified Output Format

        Outputs BLISS TLM and CMD Dictionary Definitions in Specific output format. Currently supports:
        * TLM -> CSV

        TODO
        * TLM -> TeX
        * CMD -> CSV
        * CMD -> TeX

        Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
        U.S. Government Sponsorship acknowledged.
'''

import sys
import argparse

from bliss.core import log, tlm

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--format',default='csv')
    parser.add_argument('--path',default='')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--tlm',action='store_true')
    group.add_argument('--cmd',action='store_true')
    args = vars(parser.parse_args())

    # output format for the file
    format = args['format']

    # output path
    path = args['path']

    # initialize telemetry dictionary writer
    if args['tlm']:
        writer = tlm.TlmDictWriter()

    # initialize command dictionary writer
    if args['cmd']:
        log.error("Not yet supported")
        sys.exit()

    # write to csv
    if format == 'csv':
        writer.writeToCSV(output_path=path)
    else:
        log.error("Invalid <format> specified.")

if __name__ == '__main__':
    main()
