#!/usr/bin/python
import socket
import struct
import time
from ait.core import log, tlm

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
hs_packet = struct.Struct('>hhhh')
buf = hs_packet.pack(743,16384, 1, 1)

while True:
    s.sendto(buf, ('localhost', 3076))
    log.info('Sent telemetry (%d bytes) to %s:%d' 
                % (hs_packet.nbytes, host, port))
    time.sleep(1)
