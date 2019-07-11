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
usage:  ait-cltuf-read cltuf_sequence.txt

Translates the cltuf txt sequence to an ait sequence

Examples:

  $ ait-cltuf-read seq/cltuf.txt
  $ ait-cltuf-read seq/cltuf.txt --output ait-format-cltuf.txt


'''

import os
import sys
import argparse
from ait.core import log


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description = __doc__,
        formatter_class = argparse.RawDescriptionHelpFormatter)

    # Add required command line arguments
    parser.add_argument('filename',
        metavar='</path/to/seq>',
        help='File or collection of sequence file(s) to translate')

    # Add required command line arguments
    parser.add_argument('--output',
        metavar='</path/to/desired/output.txt>',
        help='Destination file where you wish the output ait sequence to be placed.')

    # Add optional command line arguments
    args = parser.parse_args()
 
    if not args.filename:
        raise Exception('File not found: %s ' % fn)

    #Make sure file exists
    fn = os.path.abspath(args.filename)
    if not os.path.isfile(fn):
        raise Exception('File not found: %s ' % fn)
 
    # Open the file and construct ait commands for each CLTU found in the file 
    with open(fn, 'r') as stream:
        ait_cltuf = []
        cmd = ['','']
        pkt_start = False
        data_start = False
        for line in stream:
            b = line.strip('\n').split()
            #Skip blank lines
            if len(b) == 0:
                continue
 
            #Read through the file untill we see a PKT followed by 1 command
            if b[0] == '$PKT':
                pkt_start = True
            
            # If we reach the End Of Packet header, finalize the command, output it and get ready for next command
            if b[0] == '$EOP' and pkt_start:
                pkt_start = False
                data_start = False
                ait_cltuf.append(" ".join(cmd))
                cmd = ['','']
 
            #If we reach a part that contains a command packet, lets start to construct an ait command
            if pkt_start:
 
                #If we see the Spacecraft Delay header, lets grab the delay and put it into the ait command sequence
                #Delay is in milliseconds, so convert to ait time format.
                if b[0] == 'SCDELAY':
                    ait_delay = round(float(b[1]) * 0.001, 2)
                    if ait_delay > 65535:
                      raise Exception('Max delay time of 65535 exceeded')
                    cmd[0] = str(ait_delay)
 
                #If we have reached the Data, lets join it into one linear string
                if data_start:
                    row = "".join(b[:])
                    for i in range(0,len(row),4):
                        cmd[1] = cmd[1] + "0x"+"".join(row[i:i+4]) + " "
 
                # If we see the DATA header, then what follows is the cmd data 
                #until we reach the end of the packet
                if b[0] == 'DATA':
                    data_start = True

        #Once we reach the end of the file, lets convert the first 


    #Output the ait form of the cltuf 
    if args.output:
        with open(args.output, 'w') as out:
            for k in ait_cltuf:
                out.write(k+"\n")
    else:
        for k in ait_cltuf:
            #print to STD out
            print k
    log.end()


if __name__ == '__main__':
    main()
