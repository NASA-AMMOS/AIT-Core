#!/usr/bin/env python

import csv
import sys
from datetime import datetime

from bliss.core import log, tlm, pcap, gds, dmc

def main():
    log.begin()

    description     = """Parses 1553 telemetry into CSV file."""

    arguments = {
        '--all': {
            'action'  : 'store_true',
            'default' : False,
            'help'    : 'output all fields/values',
        },

        '--csv': {
            'type'    : str,
            'default' : 'output.csv',
            'metavar': '</path/to/output/csv>',
            'help'    : 'Output as CSV with filename'
        },

        '--fields': {
            'type'    : str,
            'metavar' : '</path/to/fields/file>',
            'required': True,
            'help'    : 'file containing all fields to query, separated by newline. Defaults to all fields.'
        },

        '--packet': {
            'type'    : str,
            'required': True,
            'help'    : 'field names to query, separated by space'
        },

        '--time_field': {
            'type'      : str,
            'default'   : 'time_coarse',
            'help'      : 'Time field name used for first column.'
        },

        '--stime': {
            'type'      : str,
            'help'      : 'Datetime in file to start collecting the data values. Defaults to beginning of pcap. Expected format: YYYY-MM-DDThh:mm:ssZ'
        },

        '--etime': {
            'type'      : str,
            'help'      : 'Datetime in file to end collecting the data values. Defaults to end of pcap. Expected format: YYYY-MM-DDThh:mm:ssZ'
        }
    }

    arguments['pcap'] = {
        'nargs': '*',
        'help' : 'PCAP file(s) containing telemetry packets'
    }

    args = gds.arg_parse(arguments, description)

    tlmdict = tlm.getDefaultDict()
    defn    = None

    try:
        if tlmdict is not None:
            defn = tlmdict[ args.packet ]
    except KeyError:
        log.error('Packet "%s" not defined in telemetry dictionary.' % args.packet)
        gds.exit(2)

    # Parse the fields file into a list
    with open(args.fields, 'rb') as stream:
        fields = [ fldname.strip() for fldname in stream.readlines() ]

    not_found = False

    for fldname in fields:
        if fldname not in defn.fieldmap:
            not_found = True
            log.error('No telemetry point named "%s"' % fldname)

    if not_found:
        gds.exit(2)

    if args.all:
        fields = [flddefn.name for flddefn in defn.fields]

    if args.stime:
        start = datetime.strptime(args.stime, dmc.ISO_8601_Format)
    else:
        start = dmc.GPS_Epoch

    if args.etime:
        stop = datetime.strptime(args.etime, dmc.ISO_8601_Format)
    else:
        stop = datetime.utcnow()

    # Append time to beginning of each row
    fields.insert(0, args.time_field)

    csv_file = None
    csv_writer = None
    npackets = 0
    if args.csv:
        csv_file = open(args.csv, 'wb')
        csv_writer = csv.writer(csv_file)

    output(csv_writer, fields)

    for filename in args.pcap:
        log.info('Processing %s' % filename)

        with pcap.open(filename, 'rb') as stream:
            header, data = stream.read()

            while data:
                packet = tlm.Packet(defn, data)

                if start < getattr(packet, args.time_field) < stop:
                    row = []
                    for field in fields:
                        try:
                            fieldVal = getattr(packet, field)

                            if hasattr(fieldVal, 'name'):
                                fieldVal = fieldVal.name
                            else:
                                fieldVal = str(fieldVal)

                        except KeyError:
                            log.warn('%s not found in Packet' % field)
                            fieldVal = None
                        except ValueError:
                            # enumeration not found. just get the raw value
                            fieldVal = packet._getattr(field, raw=True)

                        row.append(fieldVal)

                    output(csv_writer, row)

                npackets += 1
                header, data = stream.read()

    log.info('Parsed %s packets.' % npackets)
    log.end()

def output(csv_writer, row):
    if csv_writer:
        csv_writer.writerow(row)
    else:
        print ' '.join(row)

if __name__ == "__main__":
    main()
