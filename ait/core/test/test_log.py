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

import ait
from ait.core import log


class SysLogParserTest:
    """Unit test ait.core.log.SysLogParser"""
    message  = ''
    expected = { }

    def run_test(self):
        """Test parsing of syslog"""
        parts = log.parseSyslog(self.message)
        for key, expected in self.expected.items():
            actual = parts.get(key, '')
            msg    = 'Syslog Parsing failed for "%s" ' % key
            msg   += '(expected: "%s", actual: "%s")'  % (expected, actual)
            self.assertEquals(expected, actual, msg)


class SysLogParserTestSuccess(SysLogParserTest, unittest.TestCase):
    """Unit test of the log.SysLogParser.parse method"""
    message  = ('<14>1 2015-03-06T21:29:43.756496Z LMC-037512 ait 12074 '
               'INFO - Waiting for AIT telemetry on port 2514')
    expected = {
        'pri'      : '14',
        'version'  : '1',
        'timestamp': '2015-03-06T21:29:43.756496Z',
        'hostname' : 'LMC-037512',
        'appname'  : 'ait',
        'procid'   : '12074',
        'msgid'    : 'INFO',
        'msg'      : 'Waiting for AIT telemetry on port 2514'
    }


class SysLogParserTestMsgWithHyphen(SysLogParserTest, unittest.TestCase):
    """Unit test of the log.SysLogParser.parse method"""
    message  = ('<14>1 2015-03-06T21:29:43.756496Z LMC-037512 ait 12074 '
                'INFO - Waiting for AIT - GUI telemetry')
    expected = {
        'pri'      : '14',
        'version'  : '1',
        'timestamp': '2015-03-06T21:29:43.756496Z',
        'hostname' : 'LMC-037512',
        'appname'  : 'ait',
        'procid'   : '12074',
        'msgid'    : 'INFO',
        'msg'      : 'Waiting for AIT - GUI telemetry'
    }


if __name__ == '__main__':
    log.begin()
    unittest.main(verbosity=4)
    log.end()
