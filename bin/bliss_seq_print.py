#!/usr/bin/env python
'''
usage: bliss_seq_print.py oco3_seq_SSS_NNN_desc.bin

Prints the given binary relative time command sequence to standard
output as text.

Examples:

  $ bliss-seq-print.py seq/oco3_seq_gps_001_reset.bin

Authors: Ben Bornstein
'''

import os
import sys

import bliss

def main():
    defaults = { }


    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
      bliss.gds.usage(exit=True)

    filename  = os.path.abspath(args[0])
    extension = os.path.splitext(filename)[1]

    if extension.lower() != '.bin':
      bliss.log.warn("Filename '%s' does not have a '.bin' extension", filename)

    sequence = bliss.seq.Seq(filename)

    if not sequence.validate():
      for msg in sequence.messages:
        bliss.log.error(msg)

    sequence.printText()

    bliss.log.end()

if __name__ == '__main__':
    main()
