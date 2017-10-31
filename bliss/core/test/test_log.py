#!/usr/bin/env python2.7

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2014, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import unittest

import bliss
from bliss.core import log


class SysLogParserTest:
    """Unit test bliss.core.log.SysLogParser"""
    success = True
    messages = [ ]
    msglen = 0
    line = ""
    expected = {}

    def setUp(self):
        """Setting up for the test"""
        log.debug(self.__class__.__name__ + ":setup_:begin")
        self.parser = log.SysLogParser()
        log.debug(self.__class__.__name__ + ":setup_:begin")

    def run_test(self):
        """SysLogParserTest.run_test: Test parsing of syslog"""
        self.messages = [ ]
        payload = self.parser.parse(self.line)
        for key in self.expected:
            self.assertEquals(self.expected[key], payload[key],
                "Syslog Parsing failed for %s. Expected: %s. Actual: %s" %
                (key, self.expected[key], payload[key]))


class SysLogParserTestSuccess(SysLogParserTest, unittest.TestCase):
    """Unit test of the log.SysLogParser.parse method"""
    success = True
    msglen = 0
    line = "<14>1 2015-03-06T21:29:43.756496Z LMC-037512 bliss 12074 INFO - Waiting for BLISS telemetry on port 2514"

    expected = {}
    expected["pri"] = "14"
    #expected["version"] = "1"
    expected["asctime"] = "2015-03-06T21:29:43.756496Z"
    expected["name"] = "bliss"
    expected["levelname"] = "INFO"
    expected["message"] = "Waiting for BLISS telemetry on port 2514"


if __name__ == '__main__':
    log.begin()
    unittest.main(verbosity=4)
    log.end()
