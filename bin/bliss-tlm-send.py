#!/usr/bin/env python
##
## usage: bliss-tlm-send.py [options] <pcap-filename>
##
## Sends the telemetry contained in the given pcap file via UDP.
##
##   --port=number    Port to which to send data  (default: 3076)
##   --verbose=0|1    Report every packet sent    (default:    0)
##
## Examples:
##
##   $ bliss-tlm-send.py test/data/pcap/oco3fsw-iss1553-2015-04-22.pcap
##
## Authors: Ben Bornstein
##


import sys
import socket
import time

import bliss


defaults = {
  'port'   : 3076,
  'verbose': 0
}


try:
    if '--help' in sys.argv:
        bliss.gds.usage(exit=True)

    bliss.log.begin()
    options, args = bliss.gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
        bliss.gds.usage(exit=True)
    else:
        filename = args[0]

    host    = 'localhost'
    port    = options['port']
    sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose = options['verbose']

    if not verbose:
        bliss.log.info('Will only report every 10 telemetry packets')
        bliss.log.info('Will only report long telemetry send delays')

    with bliss.pcap.open(filename, 'r') as stream:
        npackets = 0
        prev_ts  = None

        for header, packet in stream:
            if prev_ts is None:
                prev_ts = header.ts

            delay = header.ts - prev_ts

            if delay >= 2:
                bliss.log.info('Next telemetry in %1.2f seconds' % delay)

            time.sleep(delay)

            nbytes = len(packet)

            if npackets == 0:
                bliss.log.info('Sent first telemetry packet (%d bytes)' % nbytes)
            elif verbose:
                bliss.log.info('Sent telemetry (%d bytes)' % nbytes)
            elif npackets % 10 == 0:
                bliss.log.info('Sent 10 telemetry packets')

            sock.sendto(packet, (host, port))

            npackets += 1
            prev_ts   = header.ts

except KeyboardInterrupt:
  bliss.log.info('Received Ctrl-C.  Stopping telemetry stream.')

except Exception as e:
  bliss.log.error('TLM send error: %s' % str(e))

bliss.log.end()
