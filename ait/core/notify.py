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

from email.mime.text import MIMEText
import smtplib

import ait
from ait.core import log


def trigger_notification(trigger, msg):
    ''''''
    email_triggers = ait.config.get('notifications.email.triggers', [])
    text_triggers = ait.config.get('notifications.text.triggers', [])

    if trigger in email_triggers:
        send_email_alert(msg)

    if trigger in text_triggers:
        send_text_alert(msg)

def send_email_alert(msg, recipients=None):
    ''''''
    if not recipients:
        recipients = ait.config.get('notifications.email.recipients', [])

    _send_email(msg, recipients)

def send_text_alert(msg, recipients=None):
    ''''''
    if not recipients:
        recipients = ait.config.get('notifications.text.recipients', [])

    _send_email(msg, recipients)

def _send_email(message, recipients):
    ''''''
    if type(recipients) != list:
        recipients = [recipients]

    if len(recipients) == 0 or any([i is None for i in recipients]):
        m = (
            'Email recipient list error. Unable to send email. '
            'Recipient list length: {} Recipients: {}'
        ).format(len(recipients), ', '.join(recipients))
        log.error(m)
        return

    server = ait.config.get('notifications.smtp.server', None)
    port = ait.config.get('notifications.smtp.port', None)
    un = ait.config.get('notifications.smtp.username', None)
    pw = ait.config.get('notifications.smtp.password', None)

    if server is None or port is None or un is None or pw is None:
        log.error('Email SMTP connection parameter error. Please check config.')
        return

    msg = MIMEText(message)
    msg['Subject'] = 'AIT Notification'
    msg['To'] = ', '.join(recipients)
    msg['From'] = un

    try:
        s = smtplib.SMTP_SSL(server, port)
        s.login(un, pw)
        s.sendmail(un, recipients, msg.as_string())
        s.quit()
        log.info('Email notification sent')
    except smtplib.SMTPException as e:
        log.error('Failed to send email notification.')
        log.error(e)
