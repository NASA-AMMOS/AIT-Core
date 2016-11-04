#!/usr/bin/env python
'''
usage: bliss_zlib_upload.py filename

Uploads the given file to the ISS sim, compressing it with zlib first.

NOTE: This program is for FSW testing purposes, as such, it does
not issue an OCO3_CORE_XFER_XXX command after the upload is
complete.  Eventually, specific upload command-line tools
(e.g. bliss-seq-upload.py) will have a --compress option, possibly
enabled by default.

Options:

  --host=hostname  Send commands to ISS Sim on hostname  (default: localhost)
  --port=number    Send commands to ISS Sim on port      (default: 3075)
  --verbose=0|1    Hexdump data                          (default:    0)

Examples:

  $ bliss-zlib-upload.py filename

Authors: Ben Bornstein
'''

import os
import socket
import struct
import sys
import time

import bliss

defaults = {
  'host'   : '127.0.0.1',
  'port'   : 3075,
  'verbose': 0
}


def send (cmd, host, port):
  bliss.log.debug('Sending to %s:%d: %s', host, port, cmd.name)
  sock.sendto(cmd.encode(), (host, port))
  time.sleep(0.125)

def main():
    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
      bliss.gds.usage(exit=True)

    filename   = os.path.abspath(args[0])
    compressed = filename + '.bliss-zlib'
    cmddict    = bliss.cmd.getDefaultCmdDict()

    host       = options['host']
    port       = options['port']
    sock       = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose    = options['verbose']

    if bliss.gds.compress(filename, compressed, verbose=True):
      try:
        remaining = bliss.util.getFileSize(compressed)
        chunk     = 100
        argsize   = 4 
        maxargs   = chunk / argsize

        bliss.log.info("Beginning File Upload...")
        cmd = cmddict.create('OCO3_CORE_START_COMPRESSED_UPLOAD')
        send(cmd, host, port)

        with open(compressed, 'rb') as stream:
          while remaining > 0:
            nbytes = min(remaining, chunk)
            bytes  = stream.read(nbytes)
            pad    = (nbytes % argsize)

            if pad != 0:
              bytes += bytearray(4 - pad) 

            nargs = len(bytes) / argsize 
            args  = list( struct.unpack('>%dI' % nargs, bytes) )
            pad   = maxargs - len(args)

            if pad != 0:
              args += [0] * pad

            args.insert(0, nbytes)
            cmd = cmddict.create('OCO3_CORE_UPLOAD', *args)
            send(cmd, host, port)

            remaining -= nbytes

        cmd = cmddict.create('OCO3_CORE_END_UPLOAD')
        send(cmd, host, port)
        bliss.log.info("File Upload Complete.")

        # cmd = cmddict.create('OCO3_CORE_XFER_SEQUENCE')
        # send(cmd, host, port)

      except socket.error, err:
        bliss.log.error( str(err) )

    bliss.log.end()

if __name__ == '__main__':
    main()
