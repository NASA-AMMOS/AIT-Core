#!/usr/bin/env python
'''
usage: bliss-table-decode --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin

Decodes the given FSW binary table to text.

Examples:

  $ bliss-table-decode --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin
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
    parser.add_argument('--binfile', default=None, required=True)
    parser.add_argument('--fswtabdict', default=None, required=True)
    parser.add_argument('--tabletype', default=None, required=True)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--version', default=0, type=int)

    # Get command line arguments
    args = vars(parser.parse_args())
    binfile       = args['binfile']
    dictpath      = args['fswtabdict']
    tabletype     = args['tabletype']
    verbose       = args['verbose']
    version       = args['version']

    # Grab default table dictionary
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
        table.writeToText(fswtabdict, tabletype, binfile, verbose, version)

    log.end()


if __name__ == '__main__':
    main()
