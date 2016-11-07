#!/usr/bin/env python
'''
usage: bliss_seq_upload.py oco3_seq_SSS_NNN_desc.bin

Uploads the given binary relative time command sequence.

Options:

  --port=number    Port on which to send data  (default: 3075)
  --verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-seq-upload.py seq/oco3_seq_gps_001_reset.bin

Authors: Ben Bornstein
'''

import os
import socket
import struct
import sys
import time

import bliss
import oco3

defaults = {
  "port"   : 3075,
  "verbose": 0
}


def send (cmd, host, port):
  bliss.log.info("Sending to %s:%d: %s", host, port, cmd.name)
  sock.sendto(cmd.encode(), (host, port))
  time.sleep(1)


def main():
    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
      bliss.gds.usage(exit=True)

    filename  = os.path.abspath(args[0])
    extension = os.path.splitext(filename)[1]
    cmddict   = bliss.cmd.getDefaultCmdDict()

    host      = "127.0.0.1"
    port      = options['port']
    sock      = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose   = options['verbose']

    if extension.lower() != '.bin':
      bliss.log.warn("Filename '%s' does not have a '.bin' extension", filename)

    sequence = bliss.seq.Seq(filename)

    if not sequence.validate():
      for msg in sequence.messages:
        bliss.log.error(msg)
    else:
      try:
        remaining = bliss.util.getFileSize(filename) 
        chunk     = 100
        argsize   = 4 
        maxargs   = chunk / argsize

        cmd = cmddict.create("OCO3_CORE_START_UPLOAD")
        send(cmd, host, port)

        with open(filename, "rb") as stream:
          while remaining > 0:
            nbytes = min(remaining, chunk)
            bytes  = stream.read(nbytes)
            pad    = nbytes % argsize 
            bytes += bytearray(pad) 

            nargs = (nbytes + pad) / argsize 
            args  = list( struct.unpack(">%dI" % nargs, bytes) )
            pad   = maxargs - len(args)

            if pad != 0:
              args += [0] * pad

            args.insert(0, nbytes)
            cmd = cmddict.create("OCO3_CORE_UPLOAD", *args)
            send(cmd, host, port)

            remaining -= nbytes

        cmd = cmddict.create("OCO3_CORE_END_UPLOAD")
        send(cmd, host, port)

        cmd = cmddict.create("OCO3_CORE_XFER_SEQUENCE")
        send(cmd, host, port)

      except socket.error, err:
        bliss.log.error( str(err) )

    bliss.log.end()

if __name__ == '__main__':
    main()
