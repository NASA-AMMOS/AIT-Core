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


def test_syslog_parser_success():
    """Unit test of the log.SysLogParser.parse method"""

    test_message = (
        "<14>1 2015-03-06T21:29:43.756496Z LMC-037512 ait 12074 "
        "INFO - Waiting for AIT telemetry on port 2514"
    )
    test_expected = {
        "pri": "14",
        "version": "1",
        "timestamp": "2015-03-06T21:29:43.756496Z",
        "hostname": "LMC-037512",
        "appname": "ait",
        "procid": "12074",
        "msgid": "INFO",
        "msg": "Waiting for AIT telemetry on port 2514",
    }
    parts = log.parse_syslog(test_message)
    for key, expected in test_expected.items():
        actual = parts.get(key, "")
        msg = 'Syslog Parsing failed for "%s" ' % key
        msg += '(expected: "%s", actual: "%s")' % (expected, actual)
        assert actual == expected


def test_syslog_parser_msg_with_hypen():
    """Unit test of the log.SysLogParser.parse method"""

    test_message = (
        "<14>1 2015-03-06T21:29:43.756496Z LMC-037512 ait 12074 "
        "INFO - Waiting for AIT - GUI telemetry"
    )
    test_expected = {
        "pri": "14",
        "version": "1",
        "timestamp": "2015-03-06T21:29:43.756496Z",
        "hostname": "LMC-037512",
        "appname": "ait",
        "procid": "12074",
        "msgid": "INFO",
        "msg": "Waiting for AIT - GUI telemetry",
    }
    parts = log.parse_syslog(test_message)
    for key, expected in test_expected.items():
        actual = parts.get(key, "")
        msg = 'Syslog Parsing failed for "%s" ' % key
        msg += '(expected: "%s", actual: "%s")' % (expected, actual)
        assert actual == expected
