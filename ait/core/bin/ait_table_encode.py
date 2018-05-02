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

'''
usage: ait-table-encode --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/ait-workspace/output/targets_table.txt

Encodes the given FSW text table to binary.

Examples:

  $ ait-table-encode --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/ait-workspace/output/targets_table.txt
'''

import os
import sys
import argparse

from ait.core import gds, log, table

def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add optional command line arguments
    parser.add_argument('--fswtabdict', default=None, required=True)
    parser.add_argument('--tabfile', default=None, required=True)
    parser.add_argument('--binfile', default=None, required=True)
    parser.add_argument('--tabletype', default=None, required=True)
    parser.add_argument('--verbose', action='store_true', default=False)

    # Get command line arguments
    args = parser.parse_args()
    dictpath      = args.fswtabdict
    tabfile       = args.tabfile
    tabletype     = args.tabletype
    verbose       = args.verbose

    # Grab default command dictionary
    if dictpath is not None:
        dictCache = table.FSWTabDictCache(filename=dictpath)

        try:
            filename = dictCache.filename
        except IOError, e:
            msg = 'Could not load default table dictionary "%s": %s'
            log.error(msg, filename, str(e))
        fswtabdict  = table.FSWTabDict(filename)
    else:
        fswtabdict  = table.getDefaultFSWTabDict()

    # Check if cmddict exists
    if fswtabdict is not None:
        # Write out the table file using the command dictionary
        table.writeToBinary(fswtabdict, tabletype, tabfile, verbose, outbin=args.binfile)

    log.end()


if __name__ == '__main__':
    main()
