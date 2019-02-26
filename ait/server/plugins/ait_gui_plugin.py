from ait.server.plugin import Plugin
import gevent
import gevent.event
import gevent.util
import gevent.lock
import gevent.monkey; gevent.monkey.patch_all()
import geventwebsocket

import bdb
from collections import defaultdict
import importlib
import json
import os
import struct
import sys
import time
import urllib
import webbrowser
import re

import bottle
import pkg_resources

import ait.core

from ait.core import api, cmd, dmc, evr, limits, log, notify, pcap, tlm, gds
from ait.core import util


class Session (object):
    """Session

    A Session manages the state for a single GUI client connection.
    Sessions are managed through a SessionStore and may be used as a
    Python context.
    """

    def __init__ (self, store=None, maxlen=100):
        """Creates a new Session, capable of storing up to maxlen items of
        each event, message, and telemetry type.
        """
        self.events          = api.GeventDeque(maxlen=maxlen)
        self.messages        = api.GeventDeque(maxlen=maxlen)
        self.telemetry       = api.GeventDeque(maxlen=maxlen)
        self._maxlen         = maxlen
        self._store          = store
        self._numConnections = 0

    def __enter__ (self):
        """Begins a Session context / connection."""
        self._numConnections += 1
        return self

    def __exit__ (self, exc_type, exc_value, traceback):
        """Ends a Session context / connection.

        If no more active connections exist, the Session is deleted
        from its SessionStore.
        """
        assert self._numConnections > 0
        self._numConnections -= 1

        # FIXME: Age sessions out of existence instead?
        # if self._numConnections is 0 and self._store is not None:
        #     self._store.remove(self)

    @property
    def id (self):
        """A unique identifier for this Session."""
        return str( id(self) )


class SessionStore (dict):
    """SessionStore

    A SessionStore manages one or more Sessions.  SessionStores
    associate a Session with a GUI clients through an HTTP cookie.
    """
    History = Session(maxlen=600)

    def __init__ (self, *args, **kwargs):
        """Creates a new SessionStore."""
        dict.__init__(self, *args, **kwargs)

    def addTelemetry (self, uid, packet):
        """Adds a telemetry packet to all Sessions in the store."""
        item = (uid, packet)
        SessionStore.History.telemetry.append(item)
        for session in self.values():
            session.telemetry.append(item)

    def addMessage (self, msg):
        """Adds a log message to all Sessions in the store."""
        SessionStore.History.messages.append(msg)
        for session in self.values():
            session.messages.append(msg)

    def addEvent (self, name, data):
        """Adds an event to all Sessions in the store."""
        event = { 'name': name, 'data': data }
        SessionStore.History.events.append(event)
        for session in self.values():
            session.events.append(event)

    def current (self):
        """Returns the current Session for this HTTP connection or raise an
        HTTP 401 Unauthorized error.
        """
        session = self.get( bottle.request.get_cookie('sid') )
        if session is None:
            raise bottle.HTTPError(401, 'Invalid Session Id')
        return session

    def create (self):
        """Creates and returns a new Session for this HTTP connection.
        """
        session          = Session(self)
        self[session.id] = session
        bottle.response.set_cookie('sid', session.id)
        return session

    def remove (self, session):
        """Removes the given Session from this SessionStore."""
        del self[session.id]


Sessions = SessionStore()


_RUNNING_SCRIPT = None
_RUNNING_SEQ = None
CMD_API = ait.core.api.CmdAPI(ait.config.get('command.port', ait.DEFAULT_CMD_PORT))

class HTMLRoot:
    Static = pkg_resources.resource_filename('ait.gui', 'static/')
    User   = ait.config.get('gui.html.directory', Static)

SEQRoot = ait.config.get('sequence.directory', None)
if SEQRoot and not os.path.isdir(SEQRoot):
    msg = 'sequence.directory does not exist. Sequence loads may fail.'
    ait.core.log.warn(msg)

ScriptRoot = ait.config.get('script.directory', None)
if ScriptRoot and not os.path.isdir(ScriptRoot):
    msg = (
        'script.directory points to a directory that does not exist. '
        'Script loads may fail.'
    )
    ait.core.log.warn(msg)

App     = bottle.Bottle()
Servers = [ ]
Greenlets = []

bottle.debug(True)
bottle.TEMPLATE_PATH.append(HTMLRoot.User)

try:
    with open(os.path.join(HTMLRoot.Static, 'package.json')) as infile:
        package_data = json.loads(infile.read())
    VERSION = 'AIT GUI v{}'.format(package_data['version'])
    log.info('Running {}'.format(VERSION))
except:
    VERSION = ''
    log.warn('Unable to determine which AIT GUI Version is running')


class AitGuiPlugin(Plugin):

    def __init__(self, inputs, zmq_args=None, **kwargs):
        super(AitGuiPlugin, self).__init__(inputs, zmq_args, **kwargs)

        gevent.spawn(self.init)

    def process(self, input_data, topic=None):
        # msg is going to be a tuple from the ait_packet_handler
        # (packet_uid, packet)
        # need to handle log/telem messages differently based on topic
        # Sessions.addMessage vs Sessions.addTelemetry
        if topic == "telem_stream":
            self.process_telem_msg(input_data)
        elif topic == "log_stream":
            self.process_log_msg(input_data)

    def process_telem_msg(self, msg):
        split = re.split(r'\((\d),(\'.*\')\)', msg)
        Sessions.addTelemetry(int(split[1]), split[2])

    def process_log_msg(self, msg):
        parsed = log.parseSyslog(msg)
        Sessions.addMessage(parsed)

    def getBrowserName(self, browser):
        return getattr(browser, 'name', getattr(browser, '_name', '(none)'))

    def init(self, host=None, port=8080):

        @App.route('/ait/gui/static/<pathname:path>')
        def handle(pathname):
            return bottle.static_file(pathname, root=HTMLRoot.Static)

        @App.route('/<pathname:path>')
        def handle(pathname):
            return bottle.static_file(pathname, root=HTMLRoot.User)

        if host is None:
            host = 'localhost'

        streams = ait.config.get('gui.telemetry')

        # if streams is None:
        #     msg  = cfg.AitConfigMissing('gui.telemetry').args[0]
        #     msg += '  No telemetry will be received (or displayed).'
        #     log.error(msg)
        # else:
        #     nstreams = 0

        #     for index, s in enumerate(streams):
        #         param  = 'gui.telemetry[%d].stream' % index
        #         stream = cfg.AitConfig(config=s).get('stream')

        #         if stream is None:
        #             msg = cfg.AitConfigMissing(param).args[0]
        #             log.warn(msg + '  Skipping stream.')
        #             continue

        #         name  = stream.get('name', '<unnamed>')
        #         type  = stream.get('type', 'raw').lower()
        #         tport = stream.get('port', None)

        #         if tport is None:
        #             msg = cfg.AitConfigMissing(param + '.port').args[0]
        #             log.warn(msg + '  Skipping stream.')
        #             continue

        #         if type == 'ccsds':
        #             # Servers.append( UdpCcsdsTelemetryServer(tport) )
        #             nstreams += 1
        #         else:
        #             defn = tlm.getDefaultDict().get(name, None)

        #             if defn is None:
        #                 values = (name, param)
        #                 msg    = 'Packet name "%s" not found (%s.name).' % values
        #                 log.warn(msg + '  Skipping stream.')
        #                 continue

        #             nstreams += 1

        if streams and nstreams == 0:
            msg  = 'No valid telemetry stream configurations found.'
            msg += '  No telemetry will be received (or displayed).'
            log.error(msg)

        # Servers.append(
        #     UdpSysLogServer(':%d' % ait.config.get('logging.port', 2514))
        # )

        Servers.append( gevent.pywsgi.WSGIServer(
            ('0.0.0.0', port),
            App,
            handler_class = geventwebsocket.handler.WebSocketHandler)
        )

        for s in Servers:
            s.start()

    def cleanup(self):
        global Servers

        for s in Servers:
            s.stop()

        gevent.killall(Greenlets)

    def startBrowser(self, url, name=None):
        browser = None

        if name is not None and name.lower() == 'none':
            log.info('Will not start any browser since --browser=none')
            return

        try:
            browser = webbrowser.get(name)
        except webbrowser.Error:
            old     = name or 'default'
            msg     = 'Could not find browser: %s.  Will use: %s.'
            browser = webbrowser.get()
            log.warn(msg, name, self.getBrowserName(browser))

        if type(browser) is webbrowser.GenericBrowser:
            msg = 'Will not start text-based browser: %s.'
            log.info(msg % self.getBrowserName(browser))
        elif browser is not None:
            log.info('Starting browser: %s' % self.getBrowserName(browser))
            browser.open_new(url)

    def wait(self):
        if len(Greenlets) > 0:
            done = gevent.joinall(Greenlets, raise_error=True, count=1)
            for d in done:
                if issubclass(type(d.value), KeyboardInterrupt):
                    raise d.value
        else:
            gevent.wait()

    def enable_monitoring(self):
        def telem_handler(session):
            limit_dict = defaultdict(dict)
            for k, v in limits.getDefaultDict().iteritems():
                packet, field = k.split('.')
                limit_dict[packet][field] = v

            packet_dict = defaultdict(dict)
            for k, v in tlm.getDefaultDict().iteritems():
                packet_dict[v.uid] = v

            notif_thrshld = ait.config.get('notifications.options.threshold', 1)
            notif_freq = ait.config.get('notifications.options.frequency', float('inf'))

            log.info('Starting telemetry limit monitoring')
            try:
                limit_trip_repeats = {}
                while True:
                    if len(session.telemetry) > 0:
                        p = session.telemetry.popleft()
                        packet = packet_dict[p[0]]
                        decoded = tlm.Packet(packet, data=bytearray(p[1]))

                        if packet.name in limit_dict:
                            for field, defn in limit_dict[packet.name].iteritems():
                                v = decoded._getattr(field)

                                if packet.name not in limit_trip_repeats.keys():
                                    limit_trip_repeats[packet.name] = {}

                                if field not in limit_trip_repeats[packet.name].keys():
                                    limit_trip_repeats[packet.name][field] = 0

                                if defn.error(v):
                                    msg = 'Field {} error out of limit with value {}'.format(field, v)
                                    log.error(msg)

                                    limit_trip_repeats[packet.name][field] += 1
                                    repeats = limit_trip_repeats[packet.name][field]

                                    if (repeats == notif_thrshld or
                                        (repeats > notif_thrshld and
                                        (repeats - notif_thrshld) % notif_freq == 0)):
                                        notify.trigger_notification('limit-error', msg)

                                elif defn.warn(v):
                                    msg = 'Field {} warning out of limit with value {}'.format(field, v)
                                    log.warn(msg)

                                    limit_trip_repeats[packet.name][field] += 1
                                    repeats = limit_trip_repeats[packet.name][field]

                                    if (repeats == notif_thrshld or
                                        (repeats > notif_thrshld and
                                        (repeats - notif_thrshld) % notif_freq == 0)):
                                        notify.trigger_notification('limit-warn', msg)

                                else:
                                    limit_trip_repeats[packet.name][field] = 0

                    gevent.sleep(0)
            finally:
                log.info('Telemetry limit monitoring terminated')

        s = ait.gui.Sessions.create()
        telem_handler = gevent.util.wrap_errors(KeyboardInterrupt, telem_handler)
        Greenlets.append(gevent.spawn(telem_handler, s))

    def enable_data_archiving(self, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        packet_dict = defaultdict(dict)
        for k, v in tlm.getDefaultDict().iteritems():
            packet_dict[v.uid] = v

        try:
            mod, cls = datastore.rsplit('.', 1)
            dbconn = getattr(importlib.import_module(mod), cls)()
            dbconn.connect(**kwargs)
        except ImportError:
            log.error("Could not import specified datastore {}".format(datastore))
            return
        except Exception as e:
            log.error("Unable to connect to InfluxDB backend. Disabling data archive ...")
            return

        def data_archiver(session):
            try:
                log.info('Starting telemetry data archiving')
                while True:
                    if len(session.telemetry) > 0:
                        p = session.telemetry.popleft()
                        packet = packet_dict[p[0]]
                        decoded = tlm.Packet(packet, data=bytearray(p[1]))
                        dbconn.insert(decoded, **kwargs)

                    gevent.sleep(0)
            finally:
                dbconn.close()
                log.info('Telemetry data archiving terminated')

        s = ait.gui.Sessions.create()
        data_archiver = gevent.util.wrap_errors(KeyboardInterrupt, data_archiver)
        Greenlets.append(gevent.spawn(data_archiver, s))

    def send(self, command, *args, **kwargs):
        """Creates, validates, and sends the given command as a UDP
        packet to the destination (host, port) specified when this
        CmdAPI was created.

        Returns True if the command was created, valid, and sent,
        False otherwise.
        """
        status   = False
        cmdobj   = CMD_API._cmddict.create(command, *args, **kwargs)
        messages = []

        if not cmdobj.validate(messages):
            for msg in messages:
                log.error(msg)
        else:
            encoded = cmdobj.encode()

            if CMD_API._verbose:
                size = len(cmdobj.name)
                pad  = (size - len(cmdobj.name) + 1) * ' '
                gds.hexdump(encoded, preamble=cmdobj.name + ':' + pad)

            try:
                self.publish(encoded)
                status = True

                with pcap.open(CMD_API.CMD_HIST_FILE, 'a') as output:
                    output.write(str(cmdobj))
            except IOError as e:
                log.error(e.message)

        return status


def __setResponseToEventStream():
    bottle.response.content_type  = 'text/event-stream'
    bottle.response.cache_control = 'no-cache'

def __setResponseToJSON():
    bottle.response.content_type  = 'application/json'
    bottle.response.cache_control = 'no-cache'


@App.route('/')
def handle ():
    """Return index page"""
    Sessions.create()
    return bottle.template('index.html', version=VERSION)


@App.route('/events', method='GET')
def handle ():
    """Endpoint that pushes Server-Sent Events to client"""
    with Sessions.current() as session:
        __setResponseToEventStream()
        yield 'event: connected\ndata:\n\n'

        while True:
            try:
                event = session.events.popleft(timeout=30)
                __setResponseToEventStream()
                yield 'data: %s\n\n' % json.dumps(event)
            except IndexError as e:
                yield 'event: probe\ndata:\n\n'


@App.route('/events', method='POST')
def handle():
    """Add an event to the event stream

    :jsonparam name: The name of the event to add.
    :jsonparam data: The data to include with the event.
    """
    with Sessions.current() as session:
        name = bottle.request.POST.name
        data = bottle.request.POST.data
        Sessions.addEvent(name, data)


@App.route('/evr/dict', method='GET')
def handle():
    """Return JSON EVR dictionary"""
    return json.dumps(evr.getDefaultDict().toJSON())


@App.route('/messages', method='POST')
def handle():
    """ Log a message via core library logging utilities

    :jsonparam severity: The log message severity
    :jsonparam message: The message to be sent
    """
    severity = bottle.request.json.get('severity')
    message = bottle.request.json.get('message')

    logger = getattr(log, severity, log.info)
    logger(message)


@App.route('/messages', method='GET')
def handle():
    """Endpoint that pushes syslog output to client"""
    with Sessions.current() as session:
        __setResponseToEventStream()
        yield 'event: connected\ndata:\n\n'

        while True:
            try:
                msg = session.messages.popleft(timeout=30)
                __setResponseToEventStream()
                yield 'data: %s\n\n' % json.dumps(msg)
            except IndexError:
                yield 'event: probe\ndata:\n\n'


@App.route('/tlm/dict', method='GET')
def handle():
    """Return JSON Telemetry dictionary

    **Example Response**:

    .. sourcecode: json

       {
           ExaplePacket1: {
               uid: 1,
               fields: {
                   Voltage_B: {
                       type: "MSB_U16",
                       bytes: [2, 3],
                       name: "Voltage_B",
                       desc: "Voltage B as a 14-bit DN. Conversion to engineering units is TBD."
                   },
                   Voltage_C: {
                       type: "MSB_U16",
                       bytes: [4, 5],
                       name: "Voltage_C",
                       desc: "Voltage C as a 14-bit DN. Conversion to engineering units is TBD."
                   },
                   ...
               }
           },
           ExamplePacket2: {
               ...
           }
       }
    """
    return json.dumps( tlm.getDefaultDict().toJSON() )

@App.route('/cmd/dict', method='GET')
def handle():
    """Return JSON Command dictionary

    **Example Response**:

    .. sourcecode: json

       {
           NO_OP: {
               subsystem: "CORE",
               name: "NO_OP",
               title: "NO_OP",
               opcode: 1,
               arguments: [],
               desc: "Standard NO_OP command. "
           },
           SEQ_START: {
               subsystem: "CMD",
               name: "SEQ_START",
               title: "Start Sequence",
               opcode: 2,
               arguments: [
                   {
                       name: "sequence_id",
                       bytes: [0, 1],
                       units: "none",
                       fixed: false,
                       type: "MSB_U16",
                       desc: "Sequence ID"
                   }
               ],
               desc: "This command starts a specified command sequence. "
            },
           ...
       }
    """
    return json.dumps( cmd.getDefaultDict().toJSON() )

@App.route('/cmd/hist.json', method='GET')
def handle():
    """Return sent command history

    **Example Response**:

    .. sourcecode: json

       [
           "NO_OP",
           "SEQ_START 3423"
       ]

    If you set the **detailed** query string flag the JSON
    returned will include timestamp information.

    **Example Detailed Response**

    .. sourcecode: json

        [
            {
                "timestamp": "2017-08-01 15:41:13.117805",
                "command": "NO_OP"
            },
            {
                "timestamp": "2017-08-01 15:40:23.339886",
                "command": "NO_OP"
            }
        ]
    """
    cmds = []

    try:
        with pcap.open(CMD_API.CMD_HIST_FILE, 'r') as stream:
            if 'detailed' in bottle.request.query:
                cmds = [
                    {
                        'timestamp': str(header.timestamp),
                        'command': cmdname
                    }
                    for (header, cmdname) in stream
                ]
                return json.dumps(list(reversed(cmds)))
            else:
                cmds = [cmdname for (header, cmdname) in stream]
                return json.dumps(list(set(cmds)))
    except IOError:
        pass


@App.route('/cmd', method='POST')
def handle():
    """Send a given command

    :formparam command: The command that should be sent. If arguments
                        are to be included they should be separated via
                        whitespace.

    **Example command format**

    .. sourcecode:

       myExampleCommand argumentOne argumentTwo

    """
    with Sessions.current() as session:
        command = bottle.request.forms.get('command').strip()

        args = command.split()
        if args:
            name = args[0].upper()
            args = [util.toNumber(t, t) for t in args[1:]]

            if ait.GUI.send(name, *args):
                Sessions.addEvent('cmd:hist', command)
                bottle.response.status = 200
            else:
                bottle.response.status = 400
        else:
            bottle.response.status = 400


@App.route('/cmd/validate', method='POST')
def handle():
    ''''''
    command = bottle.request.forms.get('command').strip()

    args = command.split()
    name = args[0].upper()
    args = [util.toNumber(t, t) for t in args[1:]]
    valid, msgs = CMD_API.validate(name, *args)

    if valid:
        bottle.response.status = 200
        validation_status = '{} Passed Ground Verification'.format(command)
        log.info('Command Validation: {}'.format(validation_status))
    else:
        bottle.response.status = 400
        validation_status = '{} Command Failed Ground Verification'.format(command)

    bottle.response.content_type = 'application/json'
    return json.dumps({
        'msgs': [str(m) for m in msgs],
        'status': validation_status
    })


@App.route('/log', method='GET')
def handle():
    """Endpoint that pushes syslog output to client"""
    with Sessions.current() as session:
        __setResponseToEventStream()
        yield 'event: connected\ndata:\n\n'

        while True:
            msg = session.messages.popleft()
            __setResponseToEventStream()
            yield 'data: %s\n\n' % json.dumps(msg)

@App.route('/tlm/realtime/openmct')
def handle():
    """Return telemetry packets in realtime to client"""
    session = Sessions.create()
    pad   = bytearray(1)
    wsock = bottle.request.environ.get('wsgi.websocket')

    if not wsock:
        bottle.abort(400, 'Expected WebSocket request.')

    try:
        tlmdict = ait.core.tlm.getDefaultDict()
        while not wsock.closed:
            try:
                uid, data = session.telemetry.popleft(timeout=30)
                pkt_defn = None
                for k, v in tlmdict.iteritems():
                    if v.uid == uid:
                        pkt_defn = v
                        break
                else:
                    continue

                wsock.send(json.dumps({
                    'packet': pkt_defn.name,
                    'data': ait.core.tlm.Packet(pkt_defn, data=data).toJSON()
                }))

            except IndexError:
                # If no telemetry has been received by the GUI
                # server after timeout seconds, "probe" the client
                # websocket connection to make sure it's still
                # active and if so, keep it alive.  This is
                # accomplished by sending a packet with an ID of
                # zero and no packet data.  Packet ID zero with no
                # data is ignored by AIT GUI client-side
                # Javascript code.

                if not wsock.closed:
                    wsock.send(pad + struct.pack('>I', 0))
    except geventwebsocket.WebSocketError:
        pass


@App.route('/tlm/realtime')
def handle():
    """Return telemetry packets in realtime to client"""
    with Sessions.current() as session:
        # A null-byte pad ensures wsock is treated as binary.
        pad   = bytearray(1)
        wsock = bottle.request.environ.get('wsgi.websocket')

        if not wsock:
            bottle.abort(400, 'Expected WebSocket request.')

        try:
            while not wsock.closed:
                try:
                    uid, data = session.telemetry.popleft(timeout=30)
                    wsock.send(pad + struct.pack('>I', uid) + data)
                except IndexError:
                    # If no telemetry has been received by the GUI
                    # server after timeout seconds, "probe" the client
                    # websocket connection to make sure it's still
                    # active and if so, keep it alive.  This is
                    # accomplished by sending a packet with an ID of
                    # zero and no packet data.  Packet ID zero with no
                    # data is ignored by AIT GUI client-side
                    # Javascript code.

                    if not wsock.closed:
                        wsock.send(pad + struct.pack('>I', 0))
        except geventwebsocket.WebSocketError:
            pass

@App.route('/tlm/query', method='POST')
def handle():
    """"""
    _fields_file_path = os.path.join(HTMLRoot.Static, 'fields_in.txt')

    data_dir = bottle.request.forms.get('dataDir')
    time_field = bottle.request.forms.get('timeField')
    packet = bottle.request.forms.get('packet')
    fields = bottle.request.forms.get('fields').split(',')
    start_time = bottle.request.forms.get('startTime')
    end_time = bottle.request.forms.get('endTime')

    if not (time_field and packet and fields and start_time):
        bottle.abort(400, 'Malformed parameters')

    with open(_fields_file_path, 'w') as fields_file:
        for f in fields:
            fields_file.write(f + '\n')

    pcaps = []
    for d, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith('.pcap'):
                pcaps.append(os.path.join(d, f))

    if len(pcaps) == 0:
        msg = 'Unable to locate PCAP files for query given data directory {}'.format(data_dir)
        log.error(msg)
        bottle.abort(400, msg)

    tlm_query_proc = gevent.subprocess.call([
        "ait-tlm-csv",
        "--time_field",
        time_field,
        "--fields",
        _fields_file_path,
        "--stime",
        start_time,
        "--etime",
        end_time,
        "--packet",
        packet,
        "--csv",
        os.path.join(HTMLRoot.Static, 'query_out.csv')
    ] + ["{}".format(p) for p in pcaps])

    os.remove(_fields_file_path)

    return bottle.static_file('query_out.csv', root=HTMLRoot.Static, mimetype='application/octet-stream')


@App.route('/data', method='GET')
def handle():
    """Expose ait.config.data info to the frontend"""
    return json.dumps(ait.config._datapaths)


@App.route('/leapseconds', method='GET')
def handle():
    """Return UTC-GPS Leapsecond data

    **Example Response**:

    .. sourcecode: json

       [
           ["1981-07-01 00:00:00", 1],
           ["1982-07-01 00:00:00", 2],
           ["1983-07-01 00:00:00", 3]
       ]
    """
    return json.dumps(dmc.LeapSeconds.leapseconds, default=str)


@App.route('/seq', method='GET')
def handle():
    """Return a JSON array of filenames in the SEQRoot directory

    **Example Response**:

    .. sourcecode: json

       [
            sequenceOne.txt,
            sequenceTwo.txt
       ]
    """
    if SEQRoot is None:
        files = [ ]
    else:
        files = util.listAllFiles(SEQRoot, '.txt')

        return json.dumps( sorted(files) )


@App.route('/seq', method='POST')
def handle():
    """Run requested sequence file

    :formparam seqfile: The sequence filename located in SEQRoot to execute
    """
    global _RUNNING_SEQ

    with Sessions.current() as session:
        bn_seqfile = bottle.request.forms.get('seqfile')
        _RUNNING_SEQ = gevent.spawn(bgExecSeq, bn_seqfile)

@App.route('/seq/abort', method='POST')
def handle():
    """ Abort the active running sequence """
    global _RUNNING_SEQ

    with Sessions.current() as session:
        if _RUNNING_SEQ:
            _RUNNING_SEQ.kill()
            _RUNNING_SEQ = None
            log.info('Sequence aborted by user')
            Sessions.addEvent('seq:err', 'Sequence aborted by user')


def bgExecSeq(bn_seqfile):
    seqfile = os.path.join(SEQRoot, bn_seqfile)
    if not os.path.isfile(seqfile):
        msg  = "Sequence file not found.  "
        msg += "Reload page to see updated list of files."
        log.error(msg)
        return

    log.info("Executing sequence: " + seqfile)
    Sessions.addEvent('seq:exec', bn_seqfile)
    try:
        seq_p = gevent.subprocess.Popen(["ait-seq-send", seqfile],
                                        stdout=gevent.subprocess.PIPE)
        seq_out, seq_err = seq_p.communicate()
        if seq_p.returncode is not 0:
            if not seq_err:
                seq_err = "Unknown Error"
            Sessions.addEvent('seq:err', bn_seqfile + ': ' + seq_err)
            return

        Sessions.addEvent('seq:done', bn_seqfile)
    except gevent.GreenletExit:
        seq_p.kill()


script_exec_lock = gevent.lock.Semaphore(1)


@App.route('/scripts', method='GET')
def handle():
    """ Return a JSON array of script filenames

    Scripts are located via the script.directory configuration parameter.
    """
    with Sessions.current() as session:
        if ScriptRoot is None:
            files = []
        else:
            files = util.listAllFiles(ScriptRoot, '.py')

        return json.dumps(sorted(files))


@App.route('/scripts/load/<name>', method='GET')
def handle(name):
    """ Return the text of a script

    Scripts are located via the script.directory configuration parameter.

    :param name: The name of the script to load. Should be one of the values
                 returned by **/scripts**.

    :statuscode 400: When the script name cannot be located

    **Example Response**:

    .. sourcecode: json

       {
           script_text: "This is the example content of a fake script"
       }
    """
    with Sessions.current() as session:
        script_path = os.path.join(ScriptRoot, urllib.unquote(name))
        if not os.path.exists(script_path):
            bottle.abort(400, "Script cannot be located")

        with open(script_path) as infile:
            script_text = infile.read()

        return json.dumps({"script_text": script_text})


@App.route('/script/run', method='POST')
def handle():
    """ Run a script

    Scripts are located via the script.directory configuration parameter.

    :formparam scriptPath: The name of the script to load. This should be one
                           of the values returned by **/scripts**.

    :statuscode 400: When the script name cannot be located
    """
    global _RUNNING_SCRIPT

    if _RUNNING_SCRIPT is None:
        with Sessions.current() as session:
            script_name = bottle.request.forms.get('scriptPath')
            script_path = os.path.join(ScriptRoot, script_name)

            if not os.path.exists(script_path):
                bottle.abort(400, "Script cannot be located")

            _RUNNING_SCRIPT = gevent.spawn(bgExecScript, script_path)
    else:
        msg = (
            'Attempted to execute script while another script is running. '
            'Please wait until the previous script completes and try again'
        )
        log.warn(msg)


@App.route('/script/run', method='PUT')
def handle():
    """ Resume a paused script """
    with Sessions.current() as session:
        script_exec_lock.release()
        Sessions.addEvent('script:resume', None)


@App.route('/script/pause', method='PUT')
def handle():
    """ Pause a running script """
    with Sessions.current() as session:
        script_exec_lock.acquire()
        Sessions.addEvent('script:pause', None)


@App.route('/script/step', method='PUT')
def handle():
    """ Step a paused script """
    with Sessions.current() as session:
        script_exec_lock.release()
        gevent.sleep(0)
        script_exec_lock.acquire()


@App.route('/script/abort', method='DELETE')
def handle():
    """ Abort a running script """
    if not script_exec_lock.locked():
        script_exec_lock.acquire()

    if _RUNNING_SCRIPT:
        _RUNNING_SCRIPT.kill(UIAbortException())
    script_exec_lock.release()
    Sessions.addEvent('script:aborted', None)


def bgExecScript(script_path):
    global _RUNNING_SCRIPT

    debugger = AitDB()
    with open(script_path) as infile:
        script = infile.read()

    Sessions.addEvent('script:start', None)
    try:
        debugger.run(script)
        Sessions.addEvent('script:done', None)
    except Exception as e:
        ait.core.log.error('Script execution error: {}: {}'.format(
            sys.exc_info()[0].__name__,
            e
        ))
        Sessions.addEvent('script:error', str(e))
    finally:
        _RUNNING_SCRIPT = None


class AitDB(bdb.Bdb):
    def user_line(self, frame):
        fn = self.canonic(frame.f_code.co_filename)
        # When executing our script the code location will be
        # denoted as "<string>" since we're passing the script
        # to the debugger as such. If we don't check for this we'll
        # end up with a bunch of execution noise (specifically gevent
        # function calls). We also only want to report line changes
        # in the current script. A check that the `co_name` is
        # '<module>' ensures this.
        if fn == "<string>" and frame.f_code.co_name == '<module>':
            Sessions.addEvent('script:step', frame.f_lineno)
            gevent.sleep(0)
            script_exec_lock.acquire()
            script_exec_lock.release()


@App.route('/limits/dict')
def handle():
    return json.dumps(limits.getDefaultDict().toJSON())


PromptResponse = None

@App.route('/prompt', method='POST')
def handle():
    global PromptResponse

    prompt_type = bottle.request.json.get('type')
    options = bottle.request.json.get('options')
    timeout = int(bottle.request.json.get('timeout'))

    delay = 0.25
    elapsed = 0
    status = None

    prompt_data = {
        'type': prompt_type,
        'options': options,
    }

    Sessions.addEvent('prompt:init', prompt_data)
    while True:
        if PromptResponse:
            status = PromptResponse
            break

        if timeout > 0 and elapsed >= timeout:
            status = {u'response': u'timeout'}
            Sessions.addEvent('prompt:timeout', None)
            break
        else:
            time.sleep(delay)
            elapsed += delay

    PromptResponse = None
    return bottle.HTTPResponse(status=200, body=json.dumps(status))


@App.route('/prompt/response', method='POST')
def handle():
    global PromptResponse
    with Sessions.current() as session:
        Sessions.addEvent('prompt:done', None)
        PromptResponse = json.loads(bottle.request.body.read())


class UIAbortException(Exception):
    """ Raised when user aborts script execution via GUI controls """
    def __init__ (self, msg=None):
        self._msg = msg

    def __str__ (self):
        return self.msg

    @property
    def msg(self):
        s = 'UIAbortException: User aborted script execution via GUI controls.'

        if self._msg:
            s += ': ' + self._msg

        return s
