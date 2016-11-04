#!/usr/bin/env python
'''
usage: bliss-seq-send.py [options] filename.rts

Sends the given relative timed sequence via UDP.

  --port=number    Port on which to send data  (default: 3075)
  --verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-seq-send.py test.rts

Authors: Ben Bornstein

'''

import os
import sys
import socket
import time

import bliss

defaults = {
  'port'   : 3075,
  'verbose': 0
}

def system (cmd):
  bliss.log.info('Executing: %s' % cmd)
  os.system(cmd)

def main():
    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
      bliss.gds.usage(exit=True)

    host     = '127.0.0.1'
    port     = options['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data     = ' '.join(args)
    verbose  = options['verbose']

    cmddict  = bliss.cmd.getDefaultCmdDict()
    filename = args[0]

    try:
      with open(filename, 'r') as stream:
        for line in stream.readlines():
          line = line.strip()

          # Skip blank lines and comments
          if len(line) == 0 or line.startswith('#'):
            continue

          # Meta-command
          elif line.startswith('%'):
            cmd = line[1:].strip()
            system(cmd)

          # Sequence command
          else:
            tokens   = line.split()
            delay    = float(tokens[0])
            name     = tokens[1]
            args     = [ bliss.util.toNumber(t, t) for t in tokens[2:] ]
            cmd      = cmddict.create(name, *args)
            messages = [ ]

            time.sleep(delay)
            bliss.log.info(line)
            if cmd is None:
              bliss.log.error("unrecognized command: %s" % name)
            elif cmd.validate(messages):
              sock.sendto(cmd.encode(), (host, port))
            else:
              bliss.log.error('Command validation error: %s' % ' '.join(messages))

    except socket.error, err:
      bliss.log.error( str(err) )

    except IOError:
      bliss.log.error("Could not open '%s' for reading." % filename)

    bliss.log.end()

if __name__ == '__main__':
    main()
