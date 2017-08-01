#!/usr/bin/env python

'''
Usage:
   bliss-pcap-query [arguments]

Arguments:
   [arguments]

Description:
    Bliss PCap Query

    Provides a command line script for running PCap library functions.

    pcap.query:
        Creates a new file containing the data from one or more given PCap files
        in a given time range. If no output file name is given, the new file name
        will be the name of the first file with the time frame appended to the name.

    pcap.stats:
        Displays the time ranges available in a given PCap file.


Author: Emily Winner
'''

import argparse

from bliss.core import pcap

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # create subparser for different commands
    cmdparsers = parser.add_subparsers(dest='command',help='Arguments for stats or query')

    # Add arguments for query
    qParser = cmdparsers.add_parser('query', help='Arguments for query')
    qParser.add_argument('stime')
    qParser.add_argument('etime')
    qParser.add_argument('--output',default=None)
    qParser.add_argument('fname',action='append')

    # Add optional command line arguments
    sParser = cmdparsers.add_parser('stats',help='Arguments for stats')
    sParser.add_argument('fname')
    sParser.add_argument('tol',default=2,type=int)

    # Get command line arguments
    args = vars(parser.parse_args())
    cmd = vars['command']

    # if using pcap.query
    if cmd is "query":
        stime = vars['stime']
        etime = vars['etime']
        output = vars['output']
        filenames = vars['fname']

        try:
            # Convert start time to datetime object
            starttime = datetime.datetime.strptime(stime,'%Y-%m-%dT%H:%M:%S')

            # Convert end time to datetime object
            endtime = datetime.datetime.strptime(etime,'%Y-%m-%dT%H:%M:%S')

        except ValueError:
            print "ValueError: Start and end time must be formatted as %Y-%m=%DT%H:%M:%S"
            exit(2)

        pcap.query(starttime, endtime, output, filenames)

    # if using pcap.stats
    else:
        filename = vars['fname']
        tolerance = vars['tol']
        pcap.stats(filename, tolerance)

if __name__ == '__main__':
  main()
