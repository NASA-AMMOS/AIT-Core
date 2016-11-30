#!/usr/bin/env python
'''
usage: bliss_cmd_send.py [options] command arg1 ... argN

Sends the given command and its arguments to the ISS
simulator via UDP.

  --port=number    Port on which to send data  (default: 3075)
  --verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-cmd-send.py OCO3_CMD_START_SEQUENCE_NOW 1
'''


import sys
import socket
import time

import bliss

def main():
    defaults = {
      "port"   : 3075,
      "verbose": 0
    }


    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
      bliss.gds.usage(exit=True)

    host     = "127.0.0.1"
    port     = options['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose  = options['verbose']
    cmddict  = bliss.cmd.getDefaultCmdDict()

    if cmddict is not None:
      name     = args[0]
      args     = [ bliss.util.toNumber(t, t) for t in args[1:] ]
      cmd      = cmddict.create(name, *args)
      messages = [ ]

      if cmd is None:
        bliss.log.error("unrecognized command: %s" % name)
      elif not cmd.validate(messages):
        for msg in messages:
          bliss.log.error(msg)
      else:
        if verbose:
          size = len(cmd.name)
          pad = (size - len(cmd.name) + 1) * " "
          bliss.gds.hexdump( cmd.encode(), preamble=cmd.name + ":" + pad)

        try:
          bliss.log.info("Sending to %s:%d: %s", host, port, cmd.name)
          sock.sendto(cmd.encode(), (host, port))
        except socket.error, err:
          bliss.log.error( str(err) )

    bliss.log.end()

if __name__ == '__main__':
    main()
