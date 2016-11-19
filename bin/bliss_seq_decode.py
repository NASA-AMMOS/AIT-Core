#!/usr/bin/env python
'''

usage: bliss_seq_decode.py oco3_seq_SSS_NNN_desc.bin

Decodes the given relative time command sequence to text.

Examples:

  $ bliss-seq-decode.py seq/oco3_seq_gps_001_reset.bin
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
    else:
      txtpath = sequence.txtpath
      seqid   = sequence.seqid
      version = sequence.version

      bliss.log.info("Writing %s (seqid=0x%04x, version=%u).", txtpath, seqid, version)
      sequence.writeText()

    bliss.log.end()

if __name__ == '__main__':
    main()
