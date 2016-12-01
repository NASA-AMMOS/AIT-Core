#!/usr/bin/env python
'''
usage: bliss_seq_print.py oco3_seq_SSS_NNN_desc.bin

Prints the given binary relative time command sequence to standard
output as text.

Examples:

  $ bliss-seq-print.py seq/oco3_seq_gps_001_reset.bin
'''

import os
import sys

from bliss.core import gds, log, seq


def main():
    log.begin()

    defaults      = { }
    options, args = gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
        gds.usage(exit=True)

    filename  = os.path.abspath(args[0])
    extension = os.path.splitext(filename)[1]

    if extension.lower() != '.bin':
        log.warn("Filename '%s' does not have a '.bin' extension", filename)

    sequence = seq.Seq(filename)

    if not sequence.validate():
        for msg in sequence.messages:
            log.error(msg)

    sequence.printText()

    log.end()


if __name__ == '__main__':
    main()
