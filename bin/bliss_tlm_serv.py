#!/usr/bin/env python

'''
Usage:
    bliss_tlm_serve.py [options] <pcap-filename>

Arguments:
    -p, --port=<number>     Port to serve up telemetry data [default: 3076]
    -v, --verbose           Report every packet sent

Description:
    Sends the telemetry contained in the given pcap file via TCP server
    connections.

    NOTE: This telemetry server should be started BEFORE the GUI because
    the GUI client does not attempt to reconnect to servers after startup.


Examples:

    $ bliss-tlm-serve.py test/data/pcap/oco3fsw-iss1553-2015-04-22.pcap
'''

from docopt import docopt
import gevent

from bliss.core import log, pcap


Clients = { }


def send(data):
    """Sends data to all registered clients.  Deregisters clients on I/O
    error.
    """
    for address, socket in Clients.items():
        try:
            socket.sendall(data)
            failed = 0
        except IOError:
            del Clients[address]
            failed = failed + 1


def on_connect(socket, address):
    """Registers newly connected clients to receive data via send()."""
    global Clients
    Clients[address] = socket


def main(options=None):
    args = docopt(__doc__)

    try:
        log.begin()

        filename = args.pop('<pcap-filename>')
        port     = int(args.pop('--port'))
        verbose  = args.pop('--verbose')
        host     = 'localhost'

        if not verbose:
            log.info('Will only report every 10 telemetry packets')
            log.info('Will only report long telemetry send delays')

        server = gevent.server.StreamServer((host, port), on_connect)
        server.start()

        with pcap.open(filename, 'r') as stream:
            npackets = 0
            prev_ts  = None

            for header, packet in stream:
                if prev_ts is None:
                    prev_ts = header.ts

                delay = header.ts - prev_ts

                if delay >= 2:
                    log.info('Next telemetry in %1.2f seconds' % delay)

                gevent.sleep(delay)

                nbytes = len(packet)

                if npackets == 0:
                    log.info('Sent first telemetry packet (%d bytes)' % nbytes)
                elif verbose:
                    log.info('Sent telemetry (%d bytes)' % nbytes)
                elif npackets % 10 == 0:
                    log.info('Sent 10 telemetry packets')

                send(packet)

                npackets += 1
                prev_ts   = header.ts

    except KeyboardInterrupt:
        log.info('Received Ctrl-C.  Stopping telemetry stream.')

    except Exception as e:
        log.error('TLM send error: %s' % str(e))

    log.end()


if __name__ == '__main__':
    main()
