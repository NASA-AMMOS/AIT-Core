#!/usr/bin/env python

"""
Inserts telemetry into a database from one or more files.
"""


import argparse
import os
import sys
import socket
import time

from bliss.core import db, log, tlm


def main():
    tlmdict = tlm.getDefaultDict()
    pnames  = tlmdict.keys()
    preq    = len(pnames) > 1
    ap      = argparse.ArgumentParser(description=__doc__)

    ap.add_argument('--packet',
                    type=str,
                    choices=pnames,
                    default=pnames[0],
                    required=preq)
    ap.add_argument('dbname')
    ap.add_argument('file', nargs='+')
    args = ap.parse_args()

    log.begin()

    try:
        npackets = 0
        defn     = tlm.getDefaultDict()[args.packet]
        nbytes   = defn.nbytes

        if args.dbname == ':memory:' or not os.path.exists(args.dbname):
            dbconn = db.create(args.dbname)
        else:
            dbconn = db.connect(args.dbname)

        for filename in args.file:
            log.info('Processing %s' % filename)
            with dbconn:
                with open(filename, 'rb') as stream:
                    data = stream.read(nbytes)

                    while len(data) > 0:
                        packet = tlm.Packet(defn, data)
                        db.insert(dbconn, packet)
                        data      = stream.read(nbytes)
                        npackets += 1

    except KeyboardInterrupt:
        log.info('Received Ctrl-C.  Stopping database insert.')

    except IOError as e:
        log.error(str(e))

    finally:
        dbconn.close()

    values = npackets, args.packet, args.dbname
    log.info('Inserted %d %s packets into database %s.' % values)

    log.end()


if __name__ == '__main__':
    main()
