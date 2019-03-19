# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
AIT API

The ait.core.api module provides an Application Programming
Interface (API) to your instrument by bringing together the core.cmd
and core.tlm modules in a complementary whole, allowing you to
script instrument interactions, e.g.:

.. code-block:: python

    # TBA
"""

from __future__ import absolute_import

import gevent.monkey; gevent.monkey.patch_all()
import gevent
import gevent.event
import gevent.server
import requests

import collections
import inspect
import json
import os
import socket
import time

import ait.core
from ait.core import cmd, gds, log, pcap, tlm

class APIError (Exception):
    """All AIT API exceptions are derived from this class"""
    pass


class APITimeoutError (Exception):
    """Raised when a timeout limit is exceeded"""
    def __init__ (self, timeout=0, msg=None):
        self._timeout = timeout
        self._msg     = msg

    def __str__ (self):
        return self.msg

    @property
    def msg(self):
        s = 'APITimeoutError: Timeout (%d seconds) exceeded' % self._timeout

        if self._msg:
            s += ': ' + self._msg

        return s

    @property
    def timeout(self):
        return self._timeout


class FalseWaitError (Exception):
    """Raised when a 'False' boolean is passed as an argument to wait (in order to avoid infinite loop)"""
    def __init__ (self, msg=None):
        self._msg     = msg

    def __str__ (self):
        return self.msg

    @property
    def msg(self):
        s = 'FalseWaitError: "False" boolean passed as argument to wait. Ensure wait condition args are surounded by lambda or " "' 

        if self._msg:
            s += ': ' + self._msg

        return s



class CmdAPI:
    """CmdAPI

    Provides an API to send commands to your Instrument via User
    Datagram Protocol (UDP) packets.
    """
    def __init__ (self, destination, cmddict=None, verbose=False):
        if type(destination) is int:
            destination = ('127.0.0.1', destination)

        if cmddict is None:
            cmddict = cmd.getDefaultCmdDict()

        self._host    = destination[0]
        self._port    = destination[1]
        self._cmddict = cmddict
        self._verbose = verbose
        self._socket  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        _def_cmd_hist = os.path.join(ait.config._ROOT_DIR, 'ait-cmdhist.pcap')
        self.CMD_HIST_FILE = ait.config.get('command.history.filename', _def_cmd_hist)
        if not os.path.isfile(self.CMD_HIST_FILE):
            if not os.path.isdir(os.path.dirname(self.CMD_HIST_FILE)):
                self.CMD_HIST_FILE = _def_cmd_hist
                msg  = (
                    'command.history.filename directory does not exist. '
                    'Reverting to default {}'
                ).format(_def_cmd_hist)
                ait.core.log.warn(msg)


    def send (self, command, *args, **kwargs):
        """Creates, validates, and sends the given command as a UDP
        packet to the destination (host, port) specified when this
        CmdAPI was created.

        Returns True if the command was created, valid, and sent,
        False otherwise.
        """
        status   = False
        cmdobj   = self._cmddict.create(command, *args, **kwargs)
        messages = []

        if not cmdobj.validate(messages):
            for msg in messages:
                log.error(msg)
        else:
            encoded = cmdobj.encode()

            if self._verbose:
                size = len(cmdobj.name)
                pad  = (size - len(cmdobj.name) + 1) * ' '
                gds.hexdump(encoded, preamble=cmdobj.name + ':' + pad)

            try:
                values = (self._host, self._port, str(cmdobj))
                log.command('Sending to %s:%d: %s' % values)
                self._socket.sendto(encoded, (self._host, self._port))
                status = True

                with pcap.open(self.CMD_HIST_FILE, 'a') as output:
                    output.write(str(cmdobj))
            except socket.error as e:
                log.error(e.message)
            except IOError as e:
                log.error(e.message)

        return status

    def validate(self, command, *args, **kwargs):
        if not isinstance(command, ait.core.cmd.Cmd):
            try:
                command = self._cmddict.create(command, *args, **kwargs)
            except TypeError as e:
                log.error('Command Validation: {}'.format(e))
                return False, [e]

        messages = []
        if not command.validate(messages):
            for msg in messages:
                log.error(msg)
            return False, messages

        return True, []


class GeventDeque (object):
    """GeventDeque

    A Python collections.deque that can be used in a Gevent context.
    """

    def __init__(self, iterable=None, maxlen=None):
        """Returns a new GeventDeque object initialized left-to-right
        (using append()) with data from *iterable*. If *iterable* is
        not specified, the new GeventDeque is empty.

        If *maxlen* is not specified or is ``None``, GeventDeques may
        grow to an arbitrary length.  Otherwise, the GeventDeque is
        bounded to the specified maximum length.  Once a bounded
        length GeventDeque is full, when new items are added, a
        corresponding number of items are discarded from the opposite
        end.
        """
        if iterable is None:
            self._deque = collections.deque(maxlen=maxlen)
        else:
            self._deque = collections.deque(iterable, maxlen)

        self.notEmpty = gevent.event.Event()

        if len(self._deque) > 0:
            self.notEmpty.set()

    def _pop(self, block=True, timeout=None, left=False):
        """Removes and returns the an item from this GeventDeque.

        This is an internal method, called by the public methods
        pop() and popleft().
        """
        item  = None
        timer = None
        deque = self._deque
        empty = IndexError('pop from an empty deque')

        if block is False:
            if len(self._deque) > 0:
                item = deque.popleft() if left else deque.pop()
            else:
                raise empty
        else:
            try:
                if timeout is not None:
                    timer = gevent.Timeout(timeout, empty)
                    timer.start()

                while True:
                    self.notEmpty.wait()
                    if len(deque) > 0:
                        item = deque.popleft() if left else deque.pop()
                        break
            finally:
                if timer is not None:
                    timer.cancel()

        if len(deque) == 0:
            self.notEmpty.clear()

        return item

    def __copy__(self):
        """Creates a new copy of this GeventDeque."""
        return GeventDeque(self._deque, self.maxlen)

    def __eq__(self, other):
        """True if other is equal to this GeventDeque, False otherwise."""
        return self._deque == other

    def __getitem__(self, index):
        """Returns GeventDeque[index]"""
        return self._deque.__getitem__(index)

    def __iter__(self):
        """Returns an iterable of items in this GeventDeque."""
        return self._deque.__iter__()

    def __len__(self):
        """The number of items in this GeventDeque."""
        return len(self._deque)

    @property
    def maxlen(self):
        """Maximum size of this GeventDeque or None if unbounded."""
        return self.maxlen

    def append(self, item):
        """Add item to the right side of the GeventDeque.

        This method does not block.  Either the GeventDeque grows to
        consume available memory, or if this GeventDeque has and is at
        maxlen, the leftmost item is removed.
        """
        self._deque.append(item)
        self.notEmpty.set()

    def appendleft(self, item):
        """Add item to the left side of the GeventDeque.

        This method does not block.  Either the GeventDeque grows to
        consume available memory, or if this GeventDeque has and is at
        maxlen, the rightmost item is removed.
        """
        self._deque.appendleft(item)
        self.notEmpty.set()

    def clear(self):
        """Remove all elements from the GeventDeque leaving it with
        length 0.
        """
        self._deque.clear()
        self.notEmpty.clear()

    def count(self, item):
        """Count the number of GeventDeque elements equal to item."""
        return self._deque.count(item)

    def extend(self, iterable):
        """Extend the right side of this GeventDeque by appending
        elements from the iterable argument.
        """
        self._deque.extend(iterable)
        if len(self._deque) > 0:
            self.notEmpty.set()

    def extendleft(self, iterable):
        """Extend the left side of this GeventDeque by appending
        elements from the iterable argument.  Note, the series of left
        appends results in reversing the order of elements in the
        iterable argument.
        """
        self._deque.extendleft(iterable)
        if len(self._deque) > 0:
            self.notEmpty.set()

    def pop(self, block=True, timeout=None):
        """Remove and return an item from the right side of the
        GeventDeque. If no elements are present, raises an IndexError.

        If optional args *block* is True and *timeout* is ``None``
        (the default), block if necessary until an item is
        available. If *timeout* is a positive number, it blocks at
        most *timeout* seconds and raises the :class:`IndexError`
        exception if no item was available within that time. Otherwise
        (*block* is False), return an item if one is immediately
        available, else raise the :class:`IndexError` exception
        (*timeout* is ignored in that case).
        """
        return self._pop(block, timeout)

    def popleft(self, block=True, timeout=None):
        """Remove and return an item from the right side of the
        GeventDeque. If no elements are present, raises an IndexError.

        If optional args *block* is True and *timeout* is ``None``
        (the default), block if necessary until an item is
        available. If *timeout* is a positive number, it blocks at
        most *timeout* seconds and raises the :class:`IndexError`
        exception if no item was available within that time. Otherwise
        (*block* is False), return an item if one is immediately
        available, else raise the :class:`IndexError` exception
        (*timeout* is ignored in that case).
        """
        return self._pop(block, timeout, left=True)

    def remove(item):
        """Removes the first occurrence of *item*. If not found,
        raises a ValueError.

        Unlike ``pop()`` and ``popleft()`` this method does not have
        an option to block for a specified period of time (to wait for
        item).
        """
        self._deque.remove(item)

    def reverse(self):
        """Reverse the elements of the deque in-place and then return
        None."""
        self._deque.reverse()

    def rotate(self, n):
        """Rotate the GeventDeque *n* steps to the right. If *n* is
        negative, rotate to the left.  Rotating one step to the right
        is equivalent to: ``d.appendleft(d.pop())``.
        """
        self._deque.rotate(n)


class PacketBuffers (dict):
    def __init__(self):
        super(PacketBuffers, self).__init__()


    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def create(self, name, capacity=60):
        created = False

        if name not in self:
            self[name] = GeventDeque(maxlen=capacity)
            created    = True

        return created


    def insert(self, name, packet):
        if name not in self:
            self._create(name)
        self[name].appendleft(packet)


class TlmWrapper (object):
    def __init__ (self, packets):
        self._packets = packets

    def __getattr__(self, name):
        return self._packets[0].__getattr__(name)

    def __getitem__(self, index):
        return self._packets[index]

    def __len__(self):
        return len(self._packets)



class TlmWrapperAttr (object):
    def __init__(self, buffers):
        super(TlmWrapperAttr, self).__init__()
        self._buffers = buffers

    def __getattr__(self, name):
        return TlmWrapper(self._buffers[name])



class UdpTelemetryServer (gevent.server.DatagramServer):
    """UdpTelemetryServer

    Listens for telemetry packets delivered via User Datagram Protocol
    (UDP) to a particular (host, port).
    """

    def __init__ (self, listener, pktbuf, defn=None):
        """Creates a new UdpTelemetryServer.

        The server listens for UDP packets matching the given
        ``PacketDefinition`` *defn*.

        The *listener* is either a port on localhost, a tuple
        containing ``(hostname, port)``, or a
        ``gevent.socket.socket``.

        If the optional *defn* is not specified, the first
        ``PacketDefinition`` (alphabetical by name) in the default
        telemetry dictionary (i.e. ``tlm.getDefaultDict()``) is used.
        """
        if type(listener) is int:
            listener = ('127.0.0.1', listener)

        super(UdpTelemetryServer, self).__init__(listener)
        self._defn   = defn
        self._pktbuf = pktbuf

    @property
    def packets (self):
        """The packet buffer."""
        return self._pktbuf

    def handle (self, data, address):
        self._pktbuf.appendleft( tlm.Packet(self._defn, data) )

    def start (self):
        """Starts this UdpTelemetryServer."""
        values = self._defn.name, self.server_host, self.server_port
        log.info('Listening for %s telemetry on %s:%d (UDP)' % values)
        super(UdpTelemetryServer, self).start()



class Instrument (object):
    def __init__(self,
                 cmdport=ait.config.get('command.port', ait.DEFAULT_CMD_PORT),
                 tlmport=3076, defn=None):
        if defn is None:
            tlmdict = tlm.getDefaultDict()
            names   = sorted( tlmdict.keys() )

            if len(names) == 0:
                msg = 'No packets defined in default TLM dictionary.'
                raise TypeError(msg)

            defn = tlmdict[ names[0] ]

        self._packets = PacketBuffers()
        self._cmd     = CmdAPI(cmdport)

        self._packets.create(defn.name)
        pktbuf        = self._packets[defn.name]
        self._tlm     = UdpTelemetryServer(tlmport, pktbuf, defn)
        self._tlm.start()

    @property
    def cmd (self):
        return self._cmd

    @property
    def tlm (self):
        return TlmWrapperAttr(self._packets)


def wait (cond, msg=None, _timeout=10, _raiseException=True):
    """Waits either a specified number of seconds, e.g.:

    .. code-block:: python

        wait(1.2)

    or for a given condition to be True.  Conditions may be take
    several forms: Python string expression, lambda, or function,
    e.g.:

    .. code-block:: python

        wait('instrument_mode == "SAFE"')
        wait(lambda: instrument_mode == "SAFE")

        def isSafe(): return instrument_mode == "SAFE"
        wait(isSafe)

    The default ``_timeout`` is 10 seconds.  If the condition is not
    satisfied before the timeout has elapsed, an
    :exception:``APITimeoutError`` exception is raised.

    The :exception:``APITimeoutError`` exception may be supressed in
    favor of returning ``True`` on success (i.e. condition satisfied)
    and ``False`` on failure (i.e. timeout exceeded) by setting the
    ``_raiseException`` parameter to ``False``.
     
    The :exception:``FalseWaitError`` will be thrown only if a boolean 
    with value "False" is passed as an argument to wait. The purpose of 
    this is to avoid infinite loops and catch conditional arguments are
    not passed in as strings and therefore evaluated before the wait
    function gets called. 
    
    These parameters are prefixed with an underscore so they may also
    be used to control exception handling when sending commands.
    Since methods that generate commands take keyword arguments, we
    did not want these parameter names to conflict with command
    parameter names.
    """
    status  = False
    delay   = 0.25
    elapsed = 0

    if msg is None and type(cond) is str:
        msg = cond

    if type(cond) is bool:
        if cond:
            log.warn('Boolean passed as argument to wait. Make sure argument to wait is surrounded by a lambda or " "')
        else:
            raise FalseWaitError(msg)

    if type(cond) in (int, float):
        gevent.sleep(cond)
        status = True
    else:
        while True:
            if _timeout is not None and elapsed >= _timeout:
                if _raiseException:
                    raise APITimeoutError(_timeout, msg)
                else:
                    status = False
                    break

            if type(cond) is str:
                caller = inspect.stack()[1][0]
                status = eval(cond, caller.f_globals, caller.f_locals)
            elif callable(cond):
                status = cond()
            else:
                status = cond

            if status:
                break

            gevent.sleep(delay)
            elapsed += delay

    return status


class UIAPI(object):
    def confirm(self, msg, _timeout=-1):
        ''' Send a confirm prompt to the GUI
        
        Arguments:
            msg (string):
                The message to display to the user.

            _timeout (int):
                The optional amount of time for which the prompt
                should be displayed to the user before a timeout occurs.
                Defaults to -1 which indicates there is no timeout limit.
        '''
        return self.msgBox('confirm', _timeout=_timeout, msg=msg)

    def msgBox(self, promptType, _timeout=-1, **options):
        ''' Send a user prompt request to the GUI

        Arguments:
            promptType (string):
                The prompt type to send to the GUI. Currently
                the only type supported is 'confirm'.

            _timeout (int):
                The optional amount of time for which the prompt
                should be displayed to the user before a timeout occurs.
                Defaults to -1 which indicates there is no timeout limit.

            options (dict):
                The keyword arguments that should be passed to the requested
                prompt type. Check prompt specific sections below for information on what
                arguments are expected to be present.

        Raises:
            ValueError:
                If the prompt type received is an unexpected value

        **Confirm Prompt**

        Display a message to the user and prompt them for a confirm/deny
        response to the message.

        Arguments:
            msg (string):
                The message to display to the user

        Returns:
            True if the user picks 'Confirm', False if the user picks 'Deny'

        Raises:
            KeyError:
                If the options passed to the prompt handler doesn't contain a
                `msg` attribute.

            APITimeoutError:
                If the timeout value is reached without receiving a response.
        '''
        if promptType == 'confirm':
            return self._sendConfirmPrompt(_timeout, options)
        else:
            raise ValueError('Unknown prompt type: {}'.format(promptType))

    def _sendConfirmPrompt(self, _timeout, options):
        ''''''
        if 'msg' not in options:
            raise KeyError('Confirm prompt options does not contain a `msg` attribute')

        data = {
            'type': 'confirm',
            'options': options,
            'timeout': _timeout
        }
        ret = self._sendMsgBoxRequest(data)

        if ret == 'timeout':
            raise APIError('Confirm request returned invalid response: {}'.format(ret))
        elif ret == 'confirm':
            return True
        elif ret == 'deny':
            return False

    def _sendMsgBoxRequest(self, data):
        host = ait.config.get('gui.host', 'localhost')
        port = ait.config.get('gui.port', 8080)
        url = 'http://{}:{}/prompt'.format(host, port)
        connTimeout = data['timeout'] * 2

        try:
            if connTimeout > 0:
                ret = requests.post(url, json=data, timeout=connTimeout)
            else:
                ret = requests.post(url, json=data)

            ret = json.loads(ret.text)['response']
        except requests.exceptions.ConnectionError as e:
            log.error('User prompt request connection failed')
            ret = None
        except requests.exceptions.HTTPError:
            log.error('User prompt request received an unsuccessful HTTP status code')
            ret = None
        except requests.exceptions.TooManyRedirects:
            log.error('User prompt request failed due to too many redirects')
            ret = None
        except requests.exceptions.Timeout:
            raise APITimeoutError(timeout=timeout, msg='User confirm prompt timed out')
        except KeyError:
            log.error('User prompt request received malformed response')
            ret = None

        return ret


ui = UIAPI()
