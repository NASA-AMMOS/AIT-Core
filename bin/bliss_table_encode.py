#!/usr/bin/env python
'''
usage: bin/bliss_table_encode.py --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 

Encodes the given FSW text table to binary.

Examples:

  $ bin/bliss-table-encode.py --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 
'''

import os
import sys

from bliss.core import gds, log, table


defaults = {
    "fswtabdict": None,
    "tabfile"   : None,
    "tabletype" : "targets",
    "verbose"   : 0
}


def main():
    log.begin()

    options, args = gds.parseArgs(sys.argv[1:], defaults)
    dictpath      = options['fswtabdict']
    tabfile       = options['tabfile']
    tabletype     = options['tabletype']
    verbose       = options['verbose']

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
