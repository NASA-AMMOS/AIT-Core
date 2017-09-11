#!/usr/bin/env python
'''
usage: bliss-table-encode --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 

Encodes the given FSW text table to binary.

Examples:

  $ bliss-table-encode --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 
'''

import os
import sys
import argparse

from bliss.core import gds, log, table

def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add optional command line arguments
    parser.add_argument('--fswtabdict', default=None, required=True)
    parser.add_argument('--tabfile', default=None, required=True)
    parser.add_argument('--tabletype', default=None, required=True)
    parser.add_argument('--verbose', action='store_true', default=False)

    # Get command line arguments
    args = vars(parser.parse_args())
    dictpath      = args['fswtabdict']
    tabfile       = args['tabfile']
    tabletype     = args['tabletyle']
    verbose       = args['verbose']

    # Grab default command dictionary
    if dictpath is not None:
        dictCache = table.FSWTabDictCache(filename=dictpath)

        try:
            filename = dictCache.filename
        except IOError, e:
            msg = 'Could not load default table dictionary "%s": %s'
            log.error(msg, filename, str(e))

    fswtabdict  = table.getDefaultFSWTabDict()

    # Check if cmddict exists
    if fswtabdict is not None:
        # Write out the table file using the command dictionary
        table.writeToBinary(fswtabdict, tabletype, tabfile, verbose)

    log.end()


if __name__ == '__main__':
    main()
