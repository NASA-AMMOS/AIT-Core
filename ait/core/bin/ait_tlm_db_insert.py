#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
Inserts telemetry into a database from one or more PCAP files.
"""


import argparse
import os
import sys
import socket
import struct
import time

import ait
from ait.core import db, log, tlm, pcap


def main():
    tlmdict = tlm.getDefaultDict()
    pnames  = tlmdict.keys()
    #print('test:', len(pnames))     #kkallas
    #print('test2:', pnames)         #kkallas
    #print('test3:', list(pnames.keys()))         #kkallas
    ap      = argparse.ArgumentParser(
        description     = __doc__,
        formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )

    arguments = {
        '--packet': {
            'type'    : str,
            'choices' : pnames,
            'default' : '1553_HS_Packet' if len(pnames) > 0 else None,
            #'default' : pnames[0] if len(pnames) > 0 else None,
            'help'    : 'Type of packets (!Packet name in tlm.yaml) in file',
            'required': len(pnames) > 1,
        },

        '--database': {
            'default' : ait.config.get('database.name'),
            'help'    : ('Name of database in which to insert packets (may '
                         'also be specified in config.yaml database.name)'),
            'required': ait.config.get('database.name') is None
        },

        '--backend': {
            'default': 'sqlite',
            'choices': ['sqlite', 'influx'],
            'action' : 'store',
            'help'   : ('Name of database in which to insert packets (may '
                         'also be specified in config.yaml database.name)')
        },

        '--use-current-time': {
            'action': 'store_true',
            'help'  : ('Use current time stamps when insert packets instead '
                       'of ground receipt time (or the time written in the '
                       'PCAP header).')
        },

        'file': {
            'nargs': '+',
            'help' : 'File(s) containing telemetry packets'
        }
    }

    for name, params in arguments.items():
        ap.add_argument(name, **params)

    args = ap.parse_args()

    log.begin()

    try:
        npackets = 0
        dbconn   = None
        defn     = tlm.getDefaultDict()[args.packet]
        nbytes   = defn.nbytes

        if args.backend == 'sqlite':
            dbconn = db.SQLiteBackend()
        elif args.backend == 'influx':
            dbconn = db.InfluxDBBackend()

        if args.backend == 'sqlite' and (args.database == ':memory:' or not os.path.exists(args.database)):
            dbconn.create(database=args.database)
        else:
            dbconn.connect(database=args.database)

        for filename in args.file:
            log.info('Processing %s' % filename)
            with pcap.open(filename) as stream:
                for header, pkt_data in stream:
                    try:
                        packet = tlm.Packet(defn, pkt_data)

                        time = header.timestamp
                        if args.use_current_time:
                            time = None

                        dbconn.insert(packet, time=time)
                        npackets += 1
                    except struct.error:
                        log.error("Unable to unpack data into packet. Skipping ...")

    except KeyboardInterrupt:
        log.info('Received Ctrl-C.  Stopping database insert.')

    except IOError as e:
        log.error(str(e))

    finally:
        dbconn.close()

    values = npackets, args.packet, args.database
    log.info('Inserted %d %s packets into database %s.' % values)

    log.end()


if __name__ == '__main__':
    main()
