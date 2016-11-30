#!/usr/bin/env python
'''
usage: bin/bliss_table_decode.py --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin

Decodes the given FSW binary table to text.

Examples:

  $ bin/bliss-table-decode.py --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin
'''

import os
import sys

from bliss.core import gds, log, table


defaults = {
    "binfile"   : None,
    "fswtabdict": None,
    "tabletype" : "targets",
    "verbose"   : 0,
    "version"   : 0
}


def main():
    log.begin()

    options, args = gds.parseArgs(sys.argv[1:], defaults)
    binfile       = options['binfile']
    dictpath      = options['fswtabdict']
    tabletype     = options['tabletype']
    verbose       = options['verbose']
    version       = options['version']

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
