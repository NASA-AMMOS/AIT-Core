#!/usr/bin/env python

'''
Check out the AIT API Documentation for a more detailed look at the scripting API.

    https://ait-core.readthedocs.io/en/latest/api_intro.html
'''

from ait.core.api import Instrument


inst = Instrument()

# Send a command
inst.cmd.send('NO_OP')
