#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
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
Usage: ait-tlm-simulate [options] 

Sends simulated telemetry.

  --port=number       Port to which to send data       (default:3076)
  --host=string       Host to which to send data       (default:'127.0.0.1')
  --packetName=str    String name of packetDefn        (default:None)
  --packetFill        Byte to fill packet with         (default:None)

If no packetName specified, will choose the first available packetDefn.
If no packetFill specified, will fill packet using range. 

Examples:

  $ ait-tlm-simulate 

'''


import socket
import time
import argparse

from ait.core import cfg, util, log, tlm


def main():
    try:
        log.begin()

        parser = argparse.ArgumentParser(
                    description=__doc__,
                    formatter_class=argparse.RawDescriptionHelpFormatter)

        # Add optional command line arguments
        parser.add_argument('--port', default=3076, type=int)
        parser.add_argument('--host', default='127.0.0.1', type=str)
        parser.add_argument('--packetName', default=None)
        parser.add_argument('--packetFill', default=None)

        # Get command line arguments
        args = vars(parser.parse_args())

        port = args['port']
        host = args['host']
        fill = args['packetFill']
        name = args['packetName']

        if name:
            defn = tlm.getDefaultDict()[name] 
        else:
            defn = list(tlm.getDefaultDict().values())[0]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        packet = defn.simulate(fill=fill)

        while True:
            sock.sendto(packet._data, (host, port))

            log.info('Sent telemetry (%d bytes) to %s:%d' 
                        % (packet.nbytes, host, port))

            time.sleep(1)

    except KeyboardInterrupt:
      log.info('Received Ctrl-C. Stopping telemetry stream.')

    except Exception as e:
      log.error('TLM send error: %s' % str(e))

    log.end()

if __name__ == '__main__':
    main()
