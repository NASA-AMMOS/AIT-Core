# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2019, by the California Institute of Technology. ALL RIGHTS
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
AIT Plugin for OpenMCT Telemetry service

The ait.core.servers.plugins.openmct module provides an
a web service that implements the service API for the OpenMCT
framework for realtime and, eventually, historical telemetry
from AIT.
"""

import pickle
import datetime
import json
import random
import struct
import sys
import time
import urllib
import webbrowser

import gevent
import gevent.monkey; gevent.monkey.patch_all()
import geventwebsocket

import bottle

import ait.core
from ait.core import api, dtype, log, tlm
from ait.core.server.plugin import Plugin


class AITOpenMctPlugin(Plugin):
    """This is the implementation of the AIT plugin for interaction with
     OpenMCT framework.  Telemetry dispatched from AIT server/broker
     is passed along to OpenMct in the expected format.
    """

    DEFAULT_PORT = 8082
    DEFAULT_DEBUG = False

    def __init__(self, inputs, outputs, zmq_args=None, **kwargs):
        """
        Params:
            inputs:     names of inbound streams plugin receives data from
            outputs:    names of outbound streams plugin sends its data to
            zmq_args:   dict containing the follow keys:
                            zmq_context
                            zmq_proxy_xsub_url
                            zmq_proxy_xpub_url
                        Defaults to empty dict. Default values
                        assigned during instantiation of parent class.
            **kwargs:   (optional) Dependent on requirements of child class.
        """

        super(AITOpenMctPlugin, self).__init__(inputs, outputs, zmq_args, **kwargs)

        log.info('Running AIT OpenMCT Plugin')

        # Initialize state fields
        # Debug state fields
        self._debugEnabled = AITOpenMctPlugin.DEFAULT_DEBUG
        self._debugMimicRepeat = False
        # Port value for the server
        self._servicePort = AITOpenMctPlugin.DEFAULT_PORT


        # Setup server state
        self._app = bottle.Bottle()
        self._servers = []

        # Queues for AIT events events
        self._tlmQueue = api.GeventDeque(maxlen=100)
        self._logQueue = api.GeventDeque(maxlen=100)

        # Load AIT tlm dict and create OpenMCT format of it
        self._aitTlmDict = tlm.getDefaultDict()
        self._mctTlmDict = self.format_tlmdict_for_openmct(self._aitTlmDict)

        # Create lookup from packet-uid to packet def
        self._uidToPktDefMap = self.create_uid_pkt_map(self._aitTlmDict)

        # Check for AIT config overrides
        self._checkConfig()

        gevent.spawn(self.init)

    def _checkConfig(self):
        """Check AIT configuration for override values"""

        # Check if debug flag was included
        if hasattr(self, "debug"):
            self._debugEnabled = self.debug in ['true', '1', 'TRUE', 'enabled', 'ENABLED']
            self.dbg_message("Debug flag = " + str(self._debugEnabled))

        # Check if port is assigned
        if hasattr(self, "port"):
            try:
                self._servicePort = int(self.port)
            except ValueError:
                self._servicePort = DEFAULT_PORT
            self.dbg_message("Port = " + str(self._servicePort))


    def process(self, input_data, topic=None):
        """Process received input message

        Received messaged is expected to be a tuple of the form produced
        by AITPacketHandler.

        Handle telem messages based on topic
        Look for topic in list of telem stream names first
        If those lists don't exist or topic is not in them, try matching text
        in topic name to "telem_stream"

        """
        processed = False

        if hasattr(self, 'telem_stream_names'):
            if topic in self.telem_stream_names:
                self._process_telem_msg(input_data)
                processed = True

        if not processed:
            if 'telem_stream' in topic:
                self._process_telem_msg(input_data)
                processed = True

        if not processed:
            raise ValueError('Topic of received message not recognized as telem stream.')

    def _process_telem_msg(self, msg):
        msg = pickle.loads(msg)

        uid = msg[0]
        packet = msg[1]

        #Package as a tuple, then add to queue
        tlm_entry = (uid, packet)
        self._tlmQueue.append(tlm_entry)

    # We report our special debug messages on the 'Info' log level
    # so we dont have to turn on DEBUG logging globally
    def dbg_message(self, msg):
        if self._debugEnabled:
            log.info('AitOpenMctPlugin: ' + msg)

    @staticmethod
    def datetime_jsonifier(obj):
        """Required for JSONifying datetime objects"""
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return None

    @staticmethod
    def get_browser_name(browser):
        return getattr(browser, 'name', getattr(browser, '_name', '(none)'))

    def _get_tlm_packet_def(self, uid):
        """Return packet definition based on packet unique id"""
        pkt_defn = self._uidToPktDefMap[uid]
        return pkt_defn

    def init(self):
        """Initialize the web-server state"""

        self._route()
        wsgi_server = gevent.pywsgi.WSGIServer(('0.0.0.0', self._servicePort), self._app,
                      handler_class = geventwebsocket.handler.WebSocketHandler)

        self._servers.append(wsgi_server)

        for s in self._servers:
            s.start()

    def cleanup(self):
        """Clean-up the webservers"""
        for s in self._servers:
            s.stop()

    def start_browser(self, url, name=None):
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
        gevent.wait()

    @staticmethod
    def create_uid_pkt_map(aitDict):
        """Creates a dictionary from packet def UID to package definition"""
        uid_map = dict()
        for k, v in aitDict.items():
            uid_map[v.uid] = v
        return uid_map


    def format_tlmpkt_for_openmct(self, ait_pkt):
        """Formats an AIT telemetry packet instance as an
        OpenMCT telemetry packet structure"""

        mct_dict = dict()
        ait_pkt_def = ait_pkt._defn
        ait_pkt_id  = ait_pkt_def.name

        mct_pkt_value_dict = dict()

        mct_dict['packet'] = ait_pkt_id
        mct_dict['data'] = mct_pkt_value_dict

        ait_pkt_fieldmap = ait_pkt_def.fieldmap
        for ait_field_id in ait_pkt_fieldmap:
            ait_field_def = ait_pkt_fieldmap[ait_field_id]
            tlm_pt_id = ait_field_id
            tlm_pt_value = getattr(ait_pkt, ait_field_id)
            mct_pkt_value_dict[ait_field_id] = tlm_pt_value

        return mct_dict

    def format_tlmdict_for_openmct(self, ait_tlm_dict):
        """Formats the AIT telemetry dictionary as an
        OpenMCT telemetry dictionary"""

        mct_dict = dict()
        mct_dict['name'] = 'AIT Telemetry'
        mct_dict['key'] = 'ait_telemetry_dictionary'
        mct_dict['measurements'] = []

        for ait_pkt_id in ait_tlm_dict:
            ait_pkt_def = ait_tlm_dict[ait_pkt_id]
            ait_pkt_fieldmap = ait_pkt_def.fieldmap
            for ait_field_id in ait_pkt_fieldmap:
                ait_field_def = ait_pkt_fieldmap[ait_field_id]

                mct_field_dict = dict()
                mct_field_dict['key'] = ait_pkt_id + "." + ait_field_id
                mct_field_dict['name'] = ait_field_def.name
                mct_field_dict['name'] = ait_pkt_id + ":" + ait_field_def.name

                mct_field_value_list = []

                mct_field_val_range = self.create_mct_fieldmap(ait_field_def)

                mct_field_val_domain = {
                        "key": "utc",
                        "source": "timestamp",
                        "name": "Timestamp",
                        "format": "utc",
                        "hints": {
                            "domain": 1
                        }
                    }

                mct_field_value_list.append(mct_field_val_range)
                mct_field_value_list.append(mct_field_val_domain)

                mct_field_dict['values'] = mct_field_value_list

                mct_dict['measurements'].append(mct_field_dict)

        return mct_dict

    def create_mct_fieldmap(self, ait_pkt_fld_def):
        """Constructs an OpenMCT field declaration struct from an AIT packet definition"""
        mct_field_map = {
            "key": "value",
            "name": "Value",
            "hints": {
                "range": 1
            }
        }

        # Handle units
        if hasattr(ait_pkt_fld_def, 'units'):
            if ait_pkt_fld_def.units is not None :
                mct_field_map['units'] = ait_pkt_fld_def.units

        # Type and min/max
        # Borrowed code from AIT dtype to infer info form type-NAME
        if hasattr(ait_pkt_fld_def, 'type') :
            if ait_pkt_fld_def.type is not None:
                ttype = ait_pkt_fld_def.type

                typename = ttype.name

                tformat = dtype.PrimitiveTypeFormats.get(typename, None)
                tendian = None
                tfloat = False
                tmin = None
                tmax = None
                tsigned = False
                tstring = False
                tnbits = 0

                if typename.startswith("LSB_") or typename.startswith("MSB_"):
                    tendian = typename[0:3]
                    tsigned = typename[4] != "U"
                    tfloat = typename[4] == "F" or typename[4] == "D"
                    tnbits = int(typename[-2:])
                elif typename.startswith("S"):
                    tformat = typename[1:] + "s"
                    tnbits = int(typename[1:]) * 8
                    tstring = True
                else:
                    tsigned = typename[0] != "U"
                    tnbits = int(typename[-1:])

                tnbytes = tnbits / 8

                if tfloat:
                    tmax = +sys.float_info.max
                    tmin = -sys.float_info.max
                elif tsigned:
                    tmax = 2 ** (tnbits - 1)
                    tmin = -1 * (tmax - 1)
                elif not tstring:
                    tmax = 2 ** tnbits - 1
                    tmin = 0

                if not tmin is None:
                    mct_field_map['min'] = tmin
                if not tmax is None:
                    mct_field_map['max'] = tmax

                if tfloat:
                    mct_field_map['format'] = 'float'
                elif tstring:
                    mct_field_map['format'] = 'string'
                else:
                    mct_field_map['format'] = 'integer'

                ## TODO - handle array types?

        # Handle enumerations
        if hasattr(ait_pkt_fld_def, 'enum'):
            if ait_pkt_fld_def.enum is not None:
                del mct_field_map['min']
                del mct_field_map['max']
                mct_field_map['format'] = 'enum'
                mct_enum_array = []
                enum_dict = ait_pkt_fld_def.enum
                for eNumber in enum_dict:
                    eName = enum_dict.get(eNumber)
                    enum_entry = { "string": eName, "value": eNumber }
                    mct_enum_array.append(enum_entry)
                mct_field_map['enumerations'] = mct_enum_array

        return mct_field_map

    # ---------------------------------------------------------------------
    # Section of methods to which bottle requests will be routed

    def _cors_headers_hook(self):
        """After-request hook to set CORS response headers."""
        headers = bottle.response.headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'



    def get_tlm_dict_json(self):
        """Returns the OpenMCT-formatted dictionary"""
        return json.dumps(self._mctTlmDict)

    def get_tlm_dict_raw_json(self):
        """Returns the AIT-formatted dictionary"""
        return json.dumps(self._aitTlmDict.toJSON())

    def get_realtime_tlm(self):
        """Handles realtime packet dispatch via websocket layers"""
        pad = bytearray(1)
        websocket = bottle.request.environ.get('wsgi.websocket')

        if not websocket:
            bottle.abort(400, 'Expected WebSocket request.')

        empty_map = dict()  # default empty object for probing websocket connection

        req_env = bottle.request.environ
        client_ip = req_env.get('HTTP_X_FORWARDED_FOR') or req_env.get('REMOTE_ADDR') or "(unknown)"
        self.dbg_message('Creating a new web-socket session with client IP '+client_ip)

        try:
            while not websocket.closed:
                try:
                    self.dbg_message("Polling Telemtry queue...")
                    uid, data = self._tlmQueue.popleft(timeout=30)
                    pkt_defn = self._get_tlm_packet_def(uid)
                    if not pkt_defn:
                        continue

                    pkt_name = pkt_defn.name

                    ait_pkt = ait.core.tlm.Packet(pkt_defn, data=data)

                    openmct_pkt = self.format_tlmpkt_for_openmct(ait_pkt)

                    openmct_pkt_jsonstr = json.dumps(openmct_pkt, default=self.datetime_jsonifier)

                    self.dbg_message("Sending realtime telemtry websocket msg: "+openmct_pkt_jsonstr)

                    websocket.send(openmct_pkt_jsonstr)

                except IndexError:
                    # If no telemetry has been received by the GUI
                    # server after timeout seconds, "probe" the client
                    # websocket connection to make sure it's still
                    # active and if so, keep it alive.  This is
                    # accomplished by sending an empty JSON object.
                    self.dbg_message("Telemtry queue is empty.")

                    if not websocket.closed:
                        websocket.send(json.dumps(empty_map))

            self.dbg_message('Web-socket session closed with client IP '+client_ip)

        except geventwebsocket.WebSocketError as wser:
            log.warn('Web-socket session had an error with client IP '+client_ip+': '+str(wser))

    def get_historical_tlm(self, mct_pkt_id):
        """(Non-)handling of historial queries"""
        startParam = bottle.request.query.start
        endParam   = bottle.request.query.end
        # At some point we may support this query, but not for now...
        empty_dict = dict()
        return json.dumps(empty_dict)


    def mimic_tlm(self, ait_tlm_pkt_name, ait_tlm_pkt_fill=None):
        """Used for debugging, creates an instance of a packet based on
        packet name, and fills it with zero data.
        Special case for '1553_HS_Packet' which will get random number
        data fills.
        If HTTP Request query includes a value for 'repeat', then this
        will continue emitting telemetry.
        """

        # Http query option, if it is set to anything, consider it true
        self._debugMimicRepeat = len(str(bottle.request.query.repeat)) > 0

        # This will be helpful in testing by simulating TLM
        # but by a rest call instead of actual telem
        ait_pkt_defn = None
        if ait_tlm_pkt_name:
            ait_pkt_defn = tlm.getDefaultDict()[ait_tlm_pkt_name]
        else:
            ait_pkt_defn = tlm.getDefaultDict().values()[0]

        # Create the expected message format
        pkt_def_uid = ait_pkt_defn.uid
        pkt_size_bytes = ait_pkt_defn.nbytes

        #if self._debugMimicRepeat:
        repeatStr = " REPEATED " if self._debugMimicRepeat else " a single "
        info_msg = "Received request to mimic"+repeatStr+"telemetry packet for " + ait_pkt_defn.name
        self.dbg_message(info_msg)

        # Create a binary array of size filled with 0
        dummy_data = bytearray(pkt_size_bytes)

        info_msg = ""

        while True:

            # Special handling for simply integer based packet, others will
            # have all 0 zero
            if ait_pkt_defn.name == '1553_HS_Packet':
                hs_packet = struct.Struct('>hhhhh')
                randomNum = random.randint(1,100)
                dummy_data = hs_packet.pack(randomNum,randomNum,randomNum,randomNum,randomNum)

            msg_serial = pickle.dumps((pkt_def_uid, dummy_data), 2)
            self._process_telem_msg(msg_serial)

            info_msg = "AIT OpenMct Plugin submitted mimicked telemetry for " + ait_pkt_defn.name + " (" + str(datetime.datetime.now()) + ")"
            self.dbg_message(info_msg)

            # sleep if mimic on
            if self._debugMimicRepeat:
                time.sleep(5)

            # either it was immediate or we woke up, check break condition
            if not self._debugMimicRepeat:
                break

        # Return last status message as result to client
        return info_msg


    # ---------------------------------------------------------------------
    # Routing rules

    def _route(self):
        """Performs the Bottle app routing"""

        # Returns OpenMCT formatted tlm dict
        self._app.route('/tlm/dict',     callback=self.get_tlm_dict_json)

        # Returns AIT formatted tlm dict
        self._app.route('/tlm/dict/raw', callback=self.get_tlm_dict_raw_json)

        # Estasblished websocket for realtime tlm packets
        self._app.route('/tlm/realtime', callback=self.get_realtime_tlm)

        # Http: tlm query for a given time range
        self._app.route('/tlm/history/<mct_pkt_id>', callback=self.get_historical_tlm)

        # Enable CORS via headers
        self._app.add_hook('after_request', self._cors_headers_hook)

        # Debugging routes
        if (self._debugEnabled):
            self._app.route('/tlm/debug/sim/<ait_tlm_pkt_name>', callback=self.mimic_tlm)

        # self._App.route('/<pathname:path>', callback=self.get_static_file)


        # Was in the original impl, but not sure we need it.  Don't want to lose
        # it completely tho, just in case.
        # def __setResponseToEventStream():
        #     bottle.response.content_type  = 'text/event-stream'
        #     bottle.response.cache_control = 'no-cache'
        #
        # def __setResponseToJSON():
        #     bottle.response.content_type  = 'application/json'
        #     bottle.response.cache_control = 'no-cache'
