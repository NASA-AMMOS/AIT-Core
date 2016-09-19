#!/usr/bin/env python


##
## usage: bin/bliss-table-encode.py --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 
##
## Decodes the given FSW binary table to text.
##
## Examples:
##
##   $ bin/bliss-table-encode.py --fswtabdict config/table.yaml --tabletype targets --tabfile /Users/ays/Documents/workspace/bliss-workspace/output/targets_table.txt 
##
## Authors: Ben Bornstein, Alice Stanboli
##


import os
import sys

import bliss


defaults = {
  "verbose": 0,
  "fswtabdict": None,
  "tabletype": "targets",
  "tabfile": None
}

bliss.log.begin()
options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

# Set the verbosity
verbose  = options['verbose']
dictpath = options['fswtabdict']
tabletype = options['tabletype']
tabfile = options['tabfile']

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
  bliss.table.writeToBinary(fswtabdict,tabletype,tabfile,verbose)

print
bliss.log.end()

