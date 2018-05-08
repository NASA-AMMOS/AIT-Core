#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2013, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

'''
Usage: ait-tlm-send [options] <pcap-filename>

Sends the telemetry contained in the given pcap file via UDP.

  --port=number    Port to which to send data  (default: 3076)
  --verbose        Report every packet sent    (default:False)

Examples:

  $ ait-tlm-send test/data/pcap/oco3fsw-iss1553-2015-04-22.pcap

'''


import sys
import socket
import time
import argparse

from ait.core import gds, log, pcap


def main():
    try:

        log.begin()


        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        # Add required command line arguments
        parser.add_argument('filename')

        # Add optional command line arguments
        parser.add_argument('--port', default=3076, type=int)
        parser.add_argument('--verbose', action='store_true', default=False)

        # Get command line arguments
        args = vars(parser.parse_args())

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
