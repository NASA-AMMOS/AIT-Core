#!/usr/bin/env python

'''
Usage: bliss-tlm-send [options] <pcap-filename>

Sends the telemetry contained in the given pcap file via UDP.

  --port=number    Port to which to send data  (default: 3076)
  --verbose=0|1    Report every packet sent    (default:    0)

Examples:

  $ bliss-tlm-send test/data/pcap/oco3fsw-iss1553-2015-04-22.pcap

'''


import sys
import socket
import time
import argparse

from bliss.core import gds, log, pcap


defaults = {
  'port'   : 3076,
  'verbose': 0
}


def main():
    try:
        if '--help' in sys.argv:
            stream = open(sys.argv[0])
            for line in stream.readlines():
                if line.startswith('##'): print line.replace('##',''),
            stream.close()
            sys.exit(2)

        log.begin()

        parser = argparse.ArgumentParser()
        parser.add_argument('filename',type=string)
        parser.add_argument('--port',default=3076,type=int)
        parser.add_argument('--verbose',type=int,default=0)
        args = vars(parser.parse_args())
        if len(args) == 0:
            stream = open(sys.argv[0])
            for line in stream.readlines():
                if line.startswith('##'): print line.replace('##',''),
            stream.close()
            sys.exit(2)
        else:
            filename = args['filename']

        host    = 'localhost'
        port    = args['port']
        sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        verbose = args['verbose']

        if not verbose:
            log.info('Will only report every 10 telemetry packets')
            log.info('Will only report long telemetry send delays')

        with pcap.open(filename, 'r') as stream:
            npackets = 0
            prev_ts  = None

            for header, packet in stream:
                if prev_ts is None:
                    prev_ts = header.ts

                delay = header.ts - prev_ts

                if delay >= 2:
                    log.info('Next telemetry in %1.2f seconds' % delay)

                time.sleep(delay)

                nbytes = len(packet)

                if npackets == 0:
                    log.info('Sent first telemetry packet (%d bytes)' % nbytes)
                elif verbose:
                    log.info('Sent telemetry (%d bytes)' % nbytes)
                elif npackets % 10 == 0:
                    log.info('Sent 10 telemetry packets')

                sock.sendto(packet, (host, port))

                npackets += 1
                prev_ts   = header.ts

    except KeyboardInterrupt:
      log.info('Received Ctrl-C.  Stopping telemetry stream.')

    except Exception as e:
      log.error('TLM send error: %s' % str(e))

    log.end()

if __name__ == '__main__':
    main()
