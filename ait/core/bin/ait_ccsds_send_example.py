#!/usr/bin/env python

import socket
import struct
import time
from ait.core import log, tlm

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
hs_packet = struct.Struct('>BBBBBBBBBBBBBBBB')
data = bytearray(b'\x02\xE7\x40\x00\x00\x0B\x00\x00\x00\x01\x01\x71\x0C\x41\x00\x01')

'''
## CCSDS Packet ##
version:                        000
type:                           0
secondary header flag:          0
apid:                           01011100111 #743#
sequence flag:                  01
sequence count:                 00000000 000000
packet length:                  00000000 00001011
time_coars                      00000000 00000000 00000000 00000001
time_fine                       0000 0001
time_id                         01
checkword_indicator             1
zoe                             1
packet_type                     0001
<spare>                         0
element_id                      0001
data_packet                     1               
version_id                      0001 
format_id                       000001
<unknown>                       00000000
frame_id                        00000001
'''

buf = hs_packet.pack(*data)

host = 'localhost'
port = 3076

while True:
    s.sendto(buf, (host, port))
    log.info('Sent telemetry (%d bytes) to %s:%d' 
                % (hs_packet.size, host, port))
    time.sleep(1)
