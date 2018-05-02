# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import mock

import nose
import nose.tools

import ait.core
from ait.core import notify


@mock.patch('ait.core.notify.send_text_alert')
@mock.patch('ait.core.notify.send_email_alert')
def test_trigger_notification(send_email_mock, send_text_mock):
    ait.config._config['notifications'] = {
        'email': {
            'triggers': [
                'email-only-trigger',
                'both-trigger'
            ]
        },
        'text': {
            'triggers': [
                'text-only-trigger',
                'both-trigger'
            ]
        }
    }

    notify.trigger_notification('email-only-trigger', 'foo')
    send_email_mock.assert_called()

    notify.trigger_notification('text-only-trigger', 'foo')
    send_text_mock.assert_called()

    send_email_mock.reset_mock()
    send_text_mock.reset_mock()
    notify.trigger_notification('both-trigger', 'foo')
    send_email_mock.assert_called()
    send_text_mock.assert_called()
