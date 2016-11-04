#!/usr/bin/env python
'''
usage: bliss_seq_encode.py oco3_seq_SSS_NNN_desc.txt 

Encodes the given relative time command sequence to binary.

Examples:

  $ bliss-seq-encode.py seq/oco3_seq_gps_001_reset.txt 

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

    if extension.lower() != '.txt':
      bliss.log.warn("Filename '%s' does not have a '.txt' extension", filename)

    sequence = bliss.seq.Seq(filename)

    if not sequence.validate():
      for msg in sequence.log.messages:
        bliss.log.error(msg)
    else:
      binpath = sequence.binpath
      seqid   = sequence.seqid

      bliss.log.info("Writing %s (seqid=0x%04x).", binpath, seqid)
      sequence.writeBinary()

    bliss.log.end()

if __name__ == '__main__':
    main()
