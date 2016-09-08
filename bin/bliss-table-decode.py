#!/usr/bin/env python


##
## usage: bin/bliss-table-decode.py --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin
##
## Decodes the given OCO-3 FSW binary table to text.
##
## Examples:
##
##   $ bin/bliss-table-decode.py --fswtabdict config/table.yaml --tabletype targets --binfile /Users/ays/targets.bin
##
## Authors: Ben Bornstein, Alice Stanboli
##


import os
import sys

import bliss


defaults = {
  "verbose": 0,
  "version": 0,
  "fswtabdict": None,
  "tabletype": "targets",
  "binfile": None
}

bliss.log.begin()
options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

# Set the verbosity
verbose  = options['verbose']
version  = options['version']
dictpath = options['fswtabdict']
tabletype = options['tabletype']
binfile = options['binfile']

# Grab default command dictionary
if dictpath is not None:
  dictCache = bliss.table.FSWTabDictCache(filename=dictpath)

  try:
    filename = dictCache.filename
  except IOError, e:
    msg = "Could not load default command dictionary '%s': %s'"
    bliss.log.error(msg, filename, str(e))

fswtabdict  = bliss.table.getDefaultFSWTabDict()

# Check if cmddict exists
if fswtabdict is not None:
  # Write out the table file using the command dictionary
  bliss.table.writeToText(fswtabdict,tabletype,binfile,verbose,version)

print
bliss.log.end()

