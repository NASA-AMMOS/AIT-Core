# Copyright 2008 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Logging

The bliss.log module logs warnings, errors, and other information to
standard output and via syslog.
"""

import sys
import socket
import datetime
import time
import re

import logging
import logging.handlers

import bliss

NOTICE  = logging.INFO + 1
COMMAND = logging.INFO + 2
PROGRAM = logging.INFO + 3
logging.addLevelName(NOTICE , 'NOTICE' )
logging.addLevelName(COMMAND, 'COMMAND')
logging.addLevelName(PROGRAM, 'PROGRAM')


class LogFormatter (logging.Formatter):
    """LogFormatter

    Log output format is:

        YYYY-MM-DDTHH:MM:SS | levelname | message

    Where levelname is one of 'critical', 'error', 'warning', 'command',
    'info', or 'debug'.
    """

    DATEFMT = "%Y-%m-%dT%H:%M:%S"

    def __init__ (self):
        """LogFormatter()

        Creates and returns a new LogFormatter.
        """
        format  = "%(asctime)s | %(levelname)-8s | %(message)s"
        datefmt = self.DATEFMT
        logging.Formatter.__init__(self, format, datefmt)


    def formatTime (self, record, datefmt=None):
        """Return the creation time of the specified LogRecord as formatted
        text."""
        if datefmt is None:
            datefmt = '%Y-%m-%d %H:%M:%S'

        ct = self.converter(record.created)
        t  = time.strftime(datefmt, ct)
        s  = '%s.%03d' % (t, record.msecs)

        return s



class SysLogFormatter (logging.Formatter):
    """SysLogFormatter"""

    BSD_FMT = '%(asctime)s %(hostname)s %(name)s[%(process)d]: %(message)s'
    BSD_DATEFMT = '%b %d %H:%M:%S'

    SYS_DATEFMT = '%Y-%m-%dT%H:%M:%S.%fZ'
    SYSLOG_FMT = ('1 %(asctime)s %(hostname)s %(name)s %(process)d %(levelname)s - '
                                '%(message)s')


    def __init__ (self, bsd=False):
        """LogFormatter([bsd=False])

        Creates and returns a new SysLogFormatter.  If BSD is True, the
        sylog message is formatted according to the BSD Syslog Protocol:

            RFC 3164 - The BSD Syslog Protocol
            http://tools.ietf.org/html/rfc3164

        Otherwise, the syslog message is formatted according to the Syslog
        Protocol:

            RFC 5424 - The Syslog Protocol
            http://tools.ietf.org/html/rfc5424
        """
        self.bsd      = bsd
        self.hostname = socket.gethostname()

        if self.bsd is True:
            format  = self.BSD_FMT
        else:
            format  = self.SYSLOG_FMT

        logging.Formatter.__init__(self, format)


    def format (self, record):
        """Returns the given LogRecord as formatted text."""
        record.hostname = self.hostname
        return logging.Formatter.format(self, record)


    def formatTime (self, record, datefmt=None):
        """Returns the creation time of the given LogRecord as formatted text.

        NOTE: The datefmt parameter and self.converter (the time
        conversion method) are ignored.  BSD Syslog Protocol messages
        always use local time, and by our convention, Syslog Protocol
        messages use UTC.
        """
        if self.bsd:
            lt_ts = datetime.datetime.fromtimestamp(record.created)
            ts = lt_ts.strftime(self.BSD_DATEFMT)
            if ts[4] == '0':
                ts = ts[0:4] + ' ' + ts[5:]
        else:
            utc_ts = datetime.datetime.utcfromtimestamp(record.created)
            ts     = utc_ts.strftime(self.SYS_DATEFMT)
        return ts



class SysLogHandler (logging.handlers.SysLogHandler):
    def __init__(self, address=None, facility=None, socktype=None):
        self.bsd = False

        if address is None:
            if sys.platform == 'darwin':
                address  = '/var/run/syslog'
                self.bsd = True
            else:
                address = ('localhost', logging.handlers.SYSLOG_UDP_PORT)

        if facility is None:
            facility = logging.handlers.SysLogHandler.LOG_USER

        logging.handlers.SysLogHandler.__init__(self, address, facility, socktype)

        self.priority_map['NOTICE']  = 'notice'
        self.priority_map['COMMAND'] = 'notice'
        self.priority_map['PROGRAM'] = 'notice'

        self.setFormatter( SysLogFormatter(self.bsd) )

class SysLogParser(object):
    """Parses SysLog into a dictionary. Assumes RFC 5424 - The Syslog Protocol"""

    def __init__(self, fmt=None):
        self.fmt = fmt

        if not fmt:
            self.fmt = "<%(pri)s>" + SysLogFormatter.SYSLOG_FMT + "$"

    def parse(self, msg, fmt=None):
        if fmt:
            self.fmt = fmt

        regex = get_regex(self.fmt)
        match = regex.match(msg)
        return match.groupdict()


def addHandlers (logger):
    """Adds handlers to the given Logger."""
    termlog  = logging.StreamHandler()
    handlers = [ termlog, SysLogHandler(), SysLogHandler( ('localhost', 2514) ) ]

    termlog.setFormatter( LogFormatter() )

    try:
        try:
            hostname = bliss.config.logging.hostname
        except Exception:
            hostname = 'localhost'

        # We skip logging to hostname if:
        #
        #   1.  The hostname cannot be resolved (socket.gethostbyname()
        #       throws socket.gaierror), or
        #   2.  The host is the same as localhost, since that's covered by
        #       SysLogHandler() above.  That is, we don't want to log
        #       messages to localhost:514 (syslogd) twice.
        if socket.getfqdn() != hostname:
            socket.gethostbyname(hostname)
            handlers.append( SysLogHandler( (hostname,  514) ) )

    except socket.gaierror:
        pass

    for h in handlers:
        logger.addHandler(h)

def get_regex(fmt):
    """Transforms log format string into regex.

    Formats use the following syntax:

    .. code-block:: none

        :variable - one or more words expected (\w+)
        @variable - syslog time expected (SYSLOG_TIME_FMT)
        #variable - any character expected (.+)

    """
    def replace_decimal (match):
        return "(?P<%s>.+)" % match.group(1)

    def replace_any (match):
        return "(?P<%s>.+)" % match.group(1)


    # replace string-like format
    r = re.sub(r"%\((\w+)(\)s)", replace_any, fmt)

    # replace decimal-like format
    regex = re.compile(re.sub(r"%\((\w+)(\)d)", replace_decimal, r))
    return regex;

def begin ():
    """Command-line tools should begin logging with bliss.log.begin() to
    log the command name and arguments.
    """
    logger.log(PROGRAM, " ".join(sys.argv))


def end ():
    """Command-line tools should end logging with bliss.log.end() to
    log the completion of the command.
    """
    logger.log(PROGRAM, "done.")
    logging.shutdown()

def command(*args, **kwargs):
    logger.log(COMMAND, *args, **kwargs)


def program(*args, **kwargs):
    logger.log(PROGRAM, *args, **kwargs)


try:
    logger = logging.getLogger(bliss.config.logging.name)
except Exception:
    logger = logging.getLogger('bliss')

crit   = logger.critical
debug  = logger.debug
error  = logger.error
info   = logger.info
warn   = logger.warning

addHandlers(logger)
logger.setLevel(logging.INFO)
