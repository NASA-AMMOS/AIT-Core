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
import webbrowser

import gevent
import gevent.monkey

gevent.monkey.patch_all()
import geventwebsocket
from gevent import sleep as gsleep, Timeout, Greenlet

import bottle
import importlib

import ait.core
from ait.core import api, dtype, log, tlm
from ait.core.server.plugin import Plugin


class ManagedWebSocket():
    """
    A data structure to maintain state for OpenMCT websockets
    """
    id_counter = 0  # to assign unique ids

    PACKET_ID_WILDCARD = "*"

    def __init__(self, web_socket, client_ip=None):
        self.web_socket = web_socket
        self.client_ip = client_ip
        self._subscribed_dict = dict()  # Dict from packetId to list of fieldIds
        self.is_closed = False
        self.is_error = False
        self.id = ManagedWebSocket._generate_id()

    @staticmethod
    def _generate_id():
        tmp_id = f"{ManagedWebSocket.id_counter}/{id(gevent.getcurrent())}"
        ManagedWebSocket.id_counter += 1
        return tmp_id

    def subscribe_field(self, openmct_field_id):
        """
        Adds a subscription to an OpenMCT field
        :param openmct_field_id: OpenMCT Field id
        """
        pkt_id, fld_id = DictUtils.parse_mct_pkt_id(openmct_field_id)
        if pkt_id and fld_id:
            # If packet id is not in dict, add it with empty set as value
            if pkt_id not in self._subscribed_dict.keys():
                self._subscribed_dict[pkt_id] = set()
            field_set = self._subscribed_dict.get(pkt_id, None)
            if field_set is not None:  # Unnecessary, but paranoid
                field_set.add(fld_id)

    def unsubscribe_field(self, openmct_field_id):
        """
        Removes a subscription to an OpenMCT field
        :param openmct_field_id: OpenMCT Field id
        """
        pkt_id, fld_id = DictUtils.parse_mct_pkt_id(openmct_field_id)
        if pkt_id and fld_id:
            field_set = self._subscribed_dict.get(pkt_id, None)
            if field_set:
                field_set.remove(fld_id)
                # If there are no more fields, then remove packet id
                if len(field_set) == 0:
                    self._subscribed_dict.pop(pkt_id)

    @property
    def is_alive(self):
        """
        Returns True if web-socket is active, False otherwise
        :return: Managed web-socket state
        """
        self._check_state()
        return not self.is_closed

    def _check_state(self):
        """
        Checks internal flags as well as state of underlying websocket
        to see if this instance can be considered closed
        """
        if not self.is_closed:
            if self.is_error:
                self.is_closed = True
            elif self.web_socket and self.web_socket.closed:
                self.is_closed = True

    def set_error(self):
        """
        Sets error flag
        """
        self.is_error = True

    def accepts_packet(self, pkt_id):
        """
        Returns True if pkt_id is considered subscribed to by this websocket
        If pkt_id is PACKET_ID_WILDCARD, it will be automatically accepted
        :param pkt_id: AIT Packet name
        :return: True if packet id is accepted, False otherwise
        """
        if pkt_id == ManagedWebSocket.PACKET_ID_WILDCARD:
            return True
        field_set = self._subscribed_dict.get(pkt_id, None)
        if field_set:  # Should be true if set is non-empty
            return True
        return False

    def create_subscribed_packet(self, omc_packet):
        """
        Returns a modified OpenMCT packet that contains only fields
        for which the web-socket is subscribed
        :param omc_packet: Full OpenMCT packet with all fields
        :return: New modified packet if any match in fields, else None
        """
        packet_id = omc_packet['packet']
        if not self.accepts_packet(packet_id):
            return None

        # Grab the original field data dict
        orig_fld_dict = omc_packet['data']
        if not orig_fld_dict:
            return None

        sub_pkt = None

        # Get set of fields of the packet to which session is subscribed
        field_set = self._subscribed_dict.get(packet_id, None)

        # Filter the original field value dict to only fields session is subscribed to
        if field_set:
            filt_fld_dict = {k: v for k, v in orig_fld_dict.items() if k in field_set}
            # If filtered dict is non-empty, then build new packet for return
            if filt_fld_dict:
                sub_pkt = {'packet': packet_id, 'data': filt_fld_dict}

        return sub_pkt


class DictUtils(object):
    """
    Encapsulates dictionary utilities, primarily for translating between
    AIT and OpenMCT dictionaries and packets
    """

    @staticmethod
    def create_mct_pkt_id(ait_pkt_id, ait_field_id):
        return ait_pkt_id + "." + ait_field_id

    @staticmethod
    def parse_mct_pkt_id(mct_pkt_id):
        if "." in mct_pkt_id:
            return mct_pkt_id.split(".")
        else:
            return None, None

    @staticmethod
    def create_uid_pkt_map(ait_dict):
        """Creates a dictionary from packet def UID to package definition"""
        uid_map = dict()
        for _k, v in ait_dict.items():
            uid_map[v.uid] = v
        return uid_map

    @staticmethod
    def format_tlmpkt_for_openmct(ait_pkt):
        """Formats an AIT telemetry packet instance as an
        OpenMCT telemetry packet structure"""

        mct_dict = dict()
        ait_pkt_def = ait_pkt._defn
        ait_pkt_id = ait_pkt_def.name

        mct_pkt_value_dict = dict()

        mct_dict["packet"] = ait_pkt_id
        mct_dict["data"] = mct_pkt_value_dict

        ait_pkt_fieldmap = ait_pkt_def.fieldmap
        for ait_field_id in ait_pkt_fieldmap:
            tlm_pt_value = getattr(ait_pkt, ait_field_id)
            mct_pkt_value_dict[ait_field_id] = tlm_pt_value

        return mct_dict

    @staticmethod
    def format_tlmdict_for_openmct(ait_tlm_dict):
        """Formats the AIT telemetry dictionary as an
        OpenMCT telemetry dictionary"""

        mct_dict = dict()
        mct_dict["name"] = "AIT Telemetry"
        mct_dict["key"] = "ait_telemetry_dictionary"
        mct_dict["measurements"] = []

        for ait_pkt_id in ait_tlm_dict:
            ait_pkt_def = ait_tlm_dict[ait_pkt_id]
            ait_pkt_fieldmap = ait_pkt_def.fieldmap
            for ait_field_id in ait_pkt_fieldmap:
                ait_field_def = ait_pkt_fieldmap[ait_field_id]

                mct_field_dict = dict()
                # mct_field_dict['key'] = ait_pkt_id + "." + ait_field_id
                mct_field_dict["key"] = DictUtils.create_mct_pkt_id(ait_pkt_id, ait_field_id)

                mct_field_dict["name"] = ait_field_def.name
                mct_field_dict["name"] = ait_pkt_id + ":" + ait_field_def.name

                mct_field_value_list = []

                mct_field_val_range = DictUtils.create_mct_fieldmap(ait_field_def)

                mct_field_val_domain = {
                    "key": "utc",
                    "source": "timestamp",
                    "name": "Timestamp",
                    "format": "utc",
                    "hints": {"domain": 1},
                }

                mct_field_value_list.append(mct_field_val_range)
                mct_field_value_list.append(mct_field_val_domain)

                mct_field_dict["values"] = mct_field_value_list

                mct_dict["measurements"].append(mct_field_dict)

        return mct_dict

    @staticmethod
    def create_mct_fieldmap(ait_pkt_fld_def):
        """Constructs an OpenMCT field declaration struct from an AIT packet definition"""
        mct_field_map = {"key": "value", "name": "Value", "hints": {"range": 1}}

        # Handle units
        if hasattr(ait_pkt_fld_def, "units"):
            if ait_pkt_fld_def.units is not None:
                mct_field_map["units"] = ait_pkt_fld_def.units

        # Type and min/max
        # Borrowed code from AIT dtype to infer info form type-NAME
        if hasattr(ait_pkt_fld_def, "type"):
            if ait_pkt_fld_def.type is not None:
                ttype = ait_pkt_fld_def.type

                typename = ttype.name

                tfloat = False
                tmin = None
                tmax = None
                tsigned = False
                tstring = False
                tnbits = 0

                if typename.startswith("LSB_") or typename.startswith("MSB_"):
                    tsigned = typename[4] != "U"
                    tfloat = typename[4] == "F" or typename[4] == "D"
                    tnbits = int(typename[-2:])
                elif typename.startswith("S"):
                    tnbits = int(typename[1:]) * 8
                    tstring = True
                else:
                    tsigned = typename[0] != "U"
                    tnbits = int(typename[-1:])

                if tfloat:
                    tmax = +sys.float_info.max
                    tmin = -sys.float_info.max
                elif tsigned:
                    tmax = 2 ** (tnbits - 1)
                    tmin = -1 * (tmax - 1)
                elif not tstring:
                    tmax = 2 ** tnbits - 1
                    tmin = 0

                if tmin is not None:
                    mct_field_map["min"] = tmin
                if tmax is not None:
                    mct_field_map["max"] = tmax

                if tfloat:
                    mct_field_map["format"] = "float"
                elif tstring:
                    mct_field_map["format"] = "string"
                else:
                    mct_field_map["format"] = "integer"

                # array types not supported

        # Handle enumerations
        if hasattr(ait_pkt_fld_def, "enum"):
            if ait_pkt_fld_def.enum is not None:
                del mct_field_map["min"]
                del mct_field_map["max"]
                mct_field_map["format"] = "enum"
                mct_enum_array = []
                enum_dict = ait_pkt_fld_def.enum
                for e_number in enum_dict:
                    e_name = enum_dict.get(e_number)
                    enum_entry = {"string": e_name, "value": e_number}
                    mct_enum_array.append(enum_entry)
                mct_field_map["enumerations"] = mct_enum_array

        return mct_field_map


class AITOpenMctPlugin(Plugin):
    """This is the implementation of the AIT plugin for interaction with
    OpenMCT framework.  Telemetry dispatched from AIT server/broker
    is passed along to OpenMct in the expected format.
    """

    DEFAULT_PORT = 8082
    DEFAULT_DEBUG = False
    DEFAULT_DEBUG_MAX_LEN = 512
    DEFAULT_DATABASE_ENABLED = False

    DEFAULT_WS_RECV_TIMEOUT_SECS = 0.1
    DEFAULT_TELEM_QUEUE_TIMEOUT_SECS = 10

    DEFAULT_TELEM_CHECK_SLEEP_SECS = 2
    DEFAULT_WEBSOCKET_CHECK_SLEEP_SECS = 2

    DEFAULT_WS_EMPTY_MESSAGE = json.dumps(dict())  # Empty Json string

    def __init__(
        self,
        inputs,
        outputs,
        zmq_args=None,
        datastore="ait.core.db.InfluxDBBackend",
        **kwargs
    ):
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
            datastore:   path to database backend to use
            **kwargs:   (optional) Dependent on requirements of child class.
        """

        super(AITOpenMctPlugin, self).__init__(inputs, outputs, zmq_args, **kwargs)

        log.info("Running AIT OpenMCT Plugin")

        self._datastore = datastore

        # Initialize state fields
        # Debug state fields
        self._debugEnabled = AITOpenMctPlugin.DEFAULT_DEBUG
        self._debugMimicRepeat = False
        # Port value for the server
        self._servicePort = AITOpenMctPlugin.DEFAULT_PORT
        # Flag indicating if we should create a database connection for historical queries
        self._databaseEnabled = AITOpenMctPlugin.DEFAULT_DATABASE_ENABLED

        # Check for AIT config overrides
        self._check_config()

        # Setup server state
        self._app = bottle.Bottle()
        self._servers = []

        # Queues for AIT events events
        self._tlmQueue = api.GeventDeque(maxlen=100)

        # Load AIT tlm dict and create OpenMCT format of it
        self._aitTlmDict = tlm.getDefaultDict()
        self._mctTlmDict = DictUtils.format_tlmdict_for_openmct(self._aitTlmDict)

        # Create lookup from packet-uid to packet def
        self._uidToPktDefMap = DictUtils.create_uid_pkt_map(self._aitTlmDict)

        # Attempt to initialize database, None if no DB
        self._database = self.load_database(**kwargs)

        # Maintains a set of active websocket structs
        self._socket_set = set()

        # Spawn greenlets to poll telemetry
        self.tlm_poll_greenlet = Greenlet.spawn(self.poll_telemetry_periodically)

        gevent.spawn(self.init)

    def _check_config(self):
        """Check AIT configuration for override values"""

        # Check if debug flag was included
        if hasattr(self, "debug_enabled"):
            if isinstance(self.debug_enabled, bool):
                self._debugEnabled = self.debug_enabled
            elif isinstance(self.debug_enabled, str):
                self._debugEnabled = self.debug_enabled.upper() == "TRUE"
            self.dbg_message("Debug flag = " + str(self._debugEnabled))

        # Check if port is assigned
        if hasattr(self, "service_port"):
            try:
                self._servicePort = int(self.service_port)
            except ValueError:
                self._servicePort = AITOpenMctPlugin.DEFAULT_PORT
            self.dbg_message("Service Port = " + str(self._servicePort))

        # Check if database flag was included
        if hasattr(self, "database_enabled"):
            if isinstance(self.database_enabled, bool):
                self._databaseEnabled = self.database_enabled
            elif isinstance(self.database_enabled, str):
                self._databaseEnabled = self.database_enabled.upper() == "TRUE"
            self.dbg_message("Database flag = " + str(self._databaseEnabled))

    def load_database(self, **kwargs):
        """
        If necessary database configuration is available, this method
        will create, connect and return a database connection.  If
        configuration is not available, then None is returned.

        :return: Database instance or None
        """
        """Connect to database"""

        # Initialize return value to None
        dbconn = None

        if self._databaseEnabled:

            # Perform sanity check that database config exists somewhere
            db_cfg = ait.config.get("database", kwargs.get("database", None))
            if not db_cfg:
                log.error(
                    "[OpenMCT] Plugin configured to use database but "
                    "no database configuration was found"
                )
                log.warn("Disabling historical queries.")
            else:
                try:
                    db_mod, db_cls = self._datastore.rsplit(".", 1)
                    dbconn = getattr(importlib.import_module(db_mod), db_cls)()
                    dbconn.connect(**kwargs)
                except Exception as ex:
                    self.error = log.error(f"Error connecting to database: {ex}")
                    log.warn("Disabling historical queries.")
        else:
            msg = (
                "[OpenMCT Database Configuration]"
                "This plugin is not configured with a database enabled. "
                "Historical telemetry queries "
                "will be disabled from this server endpoint."
            )
            log.warn(msg)

        return dbconn

    def process(self, input_data, topic=None):
        """
        Process received input message.

        This plugin should be configured to only receive telemetry.

        Received messaged is expected to be a tuple of the form produced
        by AITPacketHandler.
        """
        processed = False

        try:
            pkl_load = pickle.loads(input_data)
            pkt_id, pkt_data = int(pkl_load[0]), pkl_load[1]
            packet_def = self._get_tlm_packet_def(pkt_id)
            if packet_def:
                packet_def = self._uidToPktDefMap[pkt_id]
                tlm_packet = tlm.Packet(packet_def, data=bytearray(pkt_data))
                self._process_telem_msg(tlm_packet)
                processed = True
            else:
                log.error("OpenMCT Plugin received telemetry message with unknown "
                          f"packet id {pkt_id}.  Skipping input...")
        except Exception as e:
            log.error(f"OpenMCT Plugin: {e}")
            log.error("OpenMCT Plugin received input_data that it is unable to "
                      "process. Skipping input ...")

        return processed

    def _process_telem_msg(self, tlm_packet):
        """
        Places tlm_packet in telem queue
        """
        self._tlmQueue.append(tlm_packet)

    # We report our special debug messages on the 'Info' log level
    # so we dont have to turn on DEBUG logging globally
    def dbg_message(self, msg):
        if self._debugEnabled:
            max_len = self.DEFAULT_DEBUG_MAX_LEN
            max_msg = (msg[:max_len] + "...") if len(msg) > max_len else msg
            log.info("AitOpenMctPlugin: " + max_msg)

    @staticmethod
    def datetime_jsonifier(obj):
        """Required for JSONifying datetime objects"""
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return None

    @staticmethod
    def get_browser_name(browser):
        return getattr(browser, "name", getattr(browser, "_name", "(none)"))

    def _get_tlm_packet_def(self, uid):
        """Return packet definition based on packet unique id"""
        if uid in self._uidToPktDefMap.keys():
            return self._uidToPktDefMap[uid]
        else:
            return None

    def init(self):
        """Initialize the web-server state"""

        self._route()
        wsgi_server = gevent.pywsgi.WSGIServer(
            ("0.0.0.0", self._servicePort),
            self._app,
            handler_class=geventwebsocket.handler.WebSocketHandler,
        )

        self._servers.append(wsgi_server)

        for s in self._servers:
            s.start()

    def cleanup(self):
        """Clean-up the webservers"""
        for s in self._servers:
            s.stop()

    def start_browser(self, url, name=None):
        browser = None

        if name is not None and name.lower() == "none":
            log.info("Will not start any browser since --browser=none")
            return

        try:
            browser = webbrowser.get(name)
        except webbrowser.Error:
            msg = "Could not find browser: %s.  Will use: %s."
            browser = webbrowser.get()
            log.warn(msg, name, self.getBrowserName(browser))

        if type(browser) is webbrowser.GenericBrowser:
            msg = "Will not start text-based browser: %s."
            log.info(msg % self.getBrowserName(browser))
        elif browser is not None:
            log.info("Starting browser: %s" % self.getBrowserName(browser))
            browser.open_new(url)

    def wait(self):
        gevent.wait()

    # ---------------------------------------------------------------------
    # Section of methods to which bottle requests will be routed

    def _cors_headers_hook(self):
        """After-request hook to set CORS response headers."""
        headers = bottle.response.headers
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Methods"] = "PUT, GET, POST, DELETE, OPTIONS"
        headers[
            "Access-Control-Allow-Headers"
        ] = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"

    def get_tlm_dict_json(self):
        """Returns the OpenMCT-formatted dictionary"""
        return json.dumps(self._mctTlmDict)

    def get_tlm_dict_raw_json(self):
        """Returns the AIT-formatted dictionary"""
        return json.dumps(self._aitTlmDict.toJSON())

    def get_realtime_tlm_original_dumb(self):
        """Handles realtime packet dispatch via websocket layers"""
        websocket = bottle.request.environ.get("wsgi.websocket")

        if not websocket:
            bottle.abort(400, "Expected WebSocket request.")

        empty_map = dict()  # default empty object for probing websocket connection

        req_env = bottle.request.environ
        client_ip = (
            req_env.get("HTTP_X_FORWARDED_FOR")
            or req_env.get("REMOTE_ADDR")
            or "(unknown)"
        )
        self.dbg_message(
            "Creating a new web-socket session with client IP " + client_ip
        )

        try:
            while not websocket.closed:

                message = None
                with Timeout(3, False):
                    message = websocket.receive()
                if message:
                    self.dbg_message("Received websocket message: "+message)
                else:
                    self.dbg_message("Received NO websocket message")

                try:
                    self.dbg_message("Polling Telemtry queue...")
                    uid, data = self._tlmQueue.popleft(timeout=3)
                    pkt_defn = self._get_tlm_packet_def(uid)
                    if not pkt_defn:
                        continue

                    ait_pkt = ait.core.tlm.Packet(pkt_defn, data=data)

                    packet_id, openmct_pkt = DictUtils.format_tlmpkt_for_openmct(ait_pkt)

                    openmct_pkt_jsonstr = json.dumps(
                        openmct_pkt, default=self.datetime_jsonifier
                    )

                    self.dbg_message(
                        "Sending realtime telemetry websocket msg: "
                        + openmct_pkt_jsonstr
                    )

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

            self.dbg_message("Web-socket session closed with client IP " + client_ip)

        except geventwebsocket.WebSocketError as wser:
            log.warn(
                "Web-socket session had an error with client IP "
                + client_ip
                + ": "
                + str(wser)
            )

    def get_realtime_tlm(self):
        """Handles realtime packet dispatch via websocket layers"""
        websocket = bottle.request.environ.get("wsgi.websocket")

        if not websocket:
            bottle.abort(400, "Expected WebSocket request.")
            return

        req_env = bottle.request.environ
        client_ip = (
            req_env.get("HTTP_X_FORWARDED_FOR")
            or req_env.get("REMOTE_ADDR")
            or "(unknown)"
        )

        if websocket and not websocket.closed:
            mws = ManagedWebSocket(websocket, client_ip)
            self.manage_web_socket(mws)

    def manage_web_socket(self, mws):
        """
        Adds mws instance to managed set (for receiving telemetry),
        and then continuously checks web socket for new messages, which
        may affect its state.
        When web-socket is considered closed, it is removed from the
        managed set and this method returns
        :param mws: Managed web-socket instance
        """
        self.dbg_message(f"Adding record for new web-socket ID:{mws.id} with IP: {mws.client_ip}")
        self._socket_set.add(mws)

        while mws.is_alive:
            self.dbg_message(f"Polling web-socket record ID {mws.id} ")
            msg_processed = self.poll_websocket(mws)
            if not msg_processed:
                # If no message received, then sleep a lil
                gsleep(AITOpenMctPlugin.DEFAULT_WEBSOCKET_CHECK_SLEEP_SECS)

        # Web-socket is considered closed, so remove from set and return
        rem_msg_state = 'err' if mws.is_error else 'closed'
        self.dbg_message(f"Removing {rem_msg_state} web-socket record ID {mws.id}")
        self._socket_set.remove(mws)

    def get_historical_tlm(self, mct_pkt_id):
        """
        Handling of historical queries.  Time range is retrieved from bottle request query.
        :param mct_pkt_id_part: OpenMCT id part (single entry or comma-separated list)
        :return: JSON string representing list of result dicts
        """
        start_time_ms = float(bottle.request.query.start)
        end_time_ms = float(bottle.request.query.end)

        # Set the content type of response for OpenMct to know its JSON
        bottle.response.content_type = "application/json"

        self.dbg_message("Received request for historical tlm: "
                         f"Ids={mct_pkt_id} Start={start_time_ms} End={end_time_ms}")

        # The tutorial indicated that this could be a comma-separated list of ids...
        # If its a single, then this will create a list with one entry
        mct_pkt_id_list = mct_pkt_id.split(",")

        results = self.get_historical_tlm_for_range(
            mct_pkt_id_list, start_time_ms, end_time_ms
        )

        # Dump results to JSON string
        json_result = json.dumps(results)

        self.dbg_message(f"Result for historical tlm ( {start_time_ms} "
                         f"- {end_time_ms} ): {json_result}")

        return json_result

    def get_historical_tlm_for_range(self, mct_pkt_ids, start_epoch_ms, end_epoch_ms):
        """
        Perform a historical query of a list of OpenMCT telemetry ids between
        the start and end time (as milliseconds since Epoch)
        :param mct_pkt_ids: List or openMct telemetry ids
        :param start_epoch_ms: Start time
        :param end_epoch_ms: End time
        :return: List of result dicts, where each entry contains {timestamp, id, value}.
        """

        # List of dicts, where each dict entry is {timestamp: time, id: mct_field_id, value: field_value}
        result_list = []

        # If no database, then return empty result
        if not self._database:
            return result_list

        # Collect fields that share the same AIT packet (for more efficient queries)
        ait_pkt_fields_dict = {}  # Dict of pkt_id to list of field ids
        for mct_pkt_id_entry in mct_pkt_ids:
            ait_pkt_id, ait_field_name = DictUtils.parse_mct_pkt_id(mct_pkt_id_entry)

            # Add new list if this is the first time we see AIT pkt id
            if ait_pkt_id not in ait_pkt_fields_dict:
                ait_pkt_fields_dict[ait_pkt_id] = []

            field_list = ait_pkt_fields_dict[ait_pkt_id]
            field_list.append(ait_field_name)

        # For each requested AIT packet definition, perform a query
        for ait_pkt_id in ait_pkt_fields_dict:
            ait_pkt_field_names = ait_pkt_fields_dict[ait_pkt_id]
            cur_result_list = self.get_historical_tlm_for_packet_fields(
                ait_pkt_id, ait_pkt_field_names, start_epoch_ms, end_epoch_ms
            )

            # Add result if non-null and non-empty
            if cur_result_list:
                result_list.extend(cur_result_list)

        # Sort all results based on timestamp
        result_list.sort(key=lambda x: x["timestamp"])

        return result_list

    def get_historical_tlm_for_packet_fields(
        self, ait_pkt_id, ait_field_names, start_millis, end_millis
    ):
        """
        Perform a historical query for a particular AIT packet type
        :param ait_pkt_id: AIT Packet definition Id
        :param ait_field_names: List of field names to include, use None to include all fields
        :param start_millis: Start time, milliseconds since UNIX epoch
        :param end_millis: End time, milliseconds since UNIX epoch
        :return: List of OpenMct measurements that satisfy query
        """

        if not self._database and False:
            return None

        result_list = []

        ait_pkt_def = self._aitTlmDict[ait_pkt_id]
        ait_field_defs = ait_pkt_def.fields

        # Build field names list from tlm dictionary for sorting data query
        field_names = []
        # Build field types list from tlm dictionary for packing data
        field_formats = []

        # Collect the field type information (prolly dont need dtype)
        for i in range(len(ait_field_defs)):
            field_def = ait_field_defs[i]
            # if no request-list or current field is in request list
            if (not ait_field_names) or (field_def.name in ait_field_names):
                field_names.append(field_def.name)
                field_type = str(field_def.type).split("'")[1]
                field_formats.append(dtype.get(field_type).format)

        # A list with single entry of pkt id
        packet_ids = [ait_pkt_id]

        # Convert unix timestamp to UTC datetime for time range
        start_timestamp_secs = start_millis / 1000.0
        start_date = datetime.datetime.fromtimestamp(
            start_timestamp_secs, tz=datetime.timezone.utc
        )
        end_timestamp_secs = end_millis / 1000.0
        end_date = datetime.datetime.fromtimestamp(
            end_timestamp_secs, tz=datetime.timezone.utc
        )

        query_args_str = f"Packets = {packet_ids}; Start = {start_date};" \
                         f" End = {end_date}"
        self.dbg_message(f"Query args : {query_args_str}")

        # default response is empty
        res_pkts = list()

        # Query packet and time range from database
        try:
            if self._database:
                ait_db_result = self._database.query_packets(
                    packets=packet_ids,
                    start_time=start_date,
                    end_time=end_date,
                    yield_packet_time=True,
                )

                if ait_db_result.errors is not None:
                    log.error(
                        "[OpenMCT] Database query for packets "
                        + str(packet_ids)
                        + " resulted in errors: "
                    )
                    for db_err in ait_db_result.errors:
                        log.error("[OpenMCT] Error: " + str(db_err))
                elif ait_db_result.has_packets:
                    res_pkts = list(ait_db_result.get_packets())

                # Debug result size
                self.dbg_message(f"Number of results for query "
                                 f"{query_args_str} : {len(res_pkts)}")

        except Exception as e:
            log.error("[OpenMCT] Database query failed.  Error: " + str(e))
            return None

        for cur_pkt_time, cur_pkt in res_pkts:

            # Convert datetime to Javascript timestamp (in milliseconds)
            cur_timestamp_sec = datetime.datetime.timestamp(cur_pkt_time)
            unix_timestamp_msec = int(cur_timestamp_sec) * 1000

            # Add a record for each requested field for this timestamp
            for cur_field_name in field_names:
                record = {"timestamp": unix_timestamp_msec}
                record["id"] = DictUtils.create_mct_pkt_id(ait_pkt_id, cur_field_name)
                record["value"] = getattr(cur_pkt, cur_field_name)
                result_list.append(record)

        return result_list

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
        pkt_size_bytes = ait_pkt_defn.nbytes

        # if self._debugMimicRepeat:
        repeat_str = " REPEATED " if self._debugMimicRepeat else " a single "
        info_msg = (
            "Received request to mimic"
            + repeat_str
            + "telemetry packet for "
            + ait_pkt_defn.name
        )
        self.dbg_message(info_msg)

        # Create a binary array of size filled with 0
        dummy_data = bytearray(pkt_size_bytes)

        info_msg = ""

        while True:

            # Special handling for simply integer based packet, others will
            # have all 0 zero
            if ait_pkt_defn.name == "1553_HS_Packet":
                hs_packet = struct.Struct(">hhhhh")
                random_num = random.randint(1, 100)
                dummy_data = hs_packet.pack(
                    random_num, random_num, random_num, random_num, random_num
                )

            tlm_pkt = tlm.Packet(ait_pkt_defn, data=bytearray(dummy_data))
            self._process_telem_msg(tlm_pkt)

            info_msg = (
                "AIT OpenMct Plugin submitted mimicked telemetry for "
                + ait_pkt_defn.name
                + " ("
                + str(datetime.datetime.now())
                + ") to telem queue"
            )
            self.dbg_message(info_msg)

            # sleep if mimic on
            if self._debugMimicRepeat:
                gsleep(5)

            # either it was immediate or we woke up, check break condition
            if not self._debugMimicRepeat:
                break

        # Return last status message as result to client
        return info_msg

    # ---------------------------------------------------------------------

    # Greelet-invoked functions

    def poll_telemetry_periodically(self):
        while True:
            real_tlm_emitted = self.poll_telemetry()
            if not real_tlm_emitted:
                gsleep(AITOpenMctPlugin.DEFAULT_TELEM_CHECK_SLEEP_SECS)

    def poll_telemetry(self):
        """
        Polls the telemetry queue for next available telem entry.
        If found, it is broadcast to all of the managed web-sockets,
        where they decide if they are interested in the telemetry.
        If nothing on queue, then empty probe messag is sent.
        :return: True if real telemetry emitted, False otherwise.
        """
        try:
            self.dbg_message("Polling Telemetry queue...")
            ait_pkt = self._tlmQueue.popleft(timeout=self.DEFAULT_TELEM_QUEUE_TIMEOUT_SECS)
            openmct_pkt = DictUtils.format_tlmpkt_for_openmct(ait_pkt)
            self.dbg_message(f"Broadcasting {openmct_pkt} to managed web-sockets...")
            self.broadcast_packet(openmct_pkt)
            return True

        except IndexError:
            # If no telemetry has been received by the server
            # after timeout seconds, "probe" the client
            # websocket connection to make sure it's still
            # active and if so, keep it alive.  This is
            # accomplished by sending an empty JSON object.
            self.dbg_message("Telemetry queue is empty.")
            self.broadcast_message(self.DEFAULT_WS_EMPTY_MESSAGE)
            return False

    def broadcast_packet(self, openmct_pkt):
        """
        Attempt to broadcast OpenMCT packet to web-socket clients,
        the managed web-socket themselves determine if the Packet will
        be emitted.
        :param openmct_pkt: Instance of OpenMCT packet to be emitted
        :return: True if packet was emitted by at least one web-socket,
                 False otherwise.
        """
        pkt_emitted_by_any = False
        openmct_pkt_id = openmct_pkt["packet"]

        for mws in self._socket_set:
            pkt_emitted_by_cur = self.send_socket_pkt_mesg(mws,
                                                           openmct_pkt_id, openmct_pkt)
            pkt_emitted_by_any = pkt_emitted_by_cur or pkt_emitted_by_any
        return pkt_emitted_by_any

    def broadcast_message(self, message):
        """
        Broadcast OpenMCT packet to web-socket clients
        :param openmct_pkt: Instance of OpenMCT packet to be emitted
        :return:
        """
        for mws in self._socket_set:
            self.managed_web_socket_send(mws, message)

    def send_socket_pkt_mesg(self, mws, pkt_id, mct_pkt):
        """
        Attempts to send socket message if managed web-socket is alive
        and accepts the message by inspecting the pkt_id value
        :param mws: Managed web-socket
        :param pkt_id: Packet ID associated with message
        :param mct_pkt: OpenMCT telem packet
        :return: True if message sent to web-socket, False otherwise
        """
        if mws.is_alive and mws.accepts_packet(pkt_id):
            # Collect only fields the subscription cares about
            subscribed_pkt = mws.create_subscribed_packet(mct_pkt)
            # If that new packet still has fields, stringify and send
            if subscribed_pkt:
                pkt_mesg = json.dumps(subscribed_pkt,
                                      default=self.datetime_jsonifier)
                self.dbg_message("Sending realtime telemetry web-socket msg "
                                 f"to websocket {mws.id}: {pkt_mesg}")
                self.managed_web_socket_send(mws, pkt_mesg)
                return True

        return False

    # ---------------------------------------------------------------------

    @staticmethod
    def managed_web_socket_recv(mws):
        '''
        Attempts to read message from the websocket with timeout.
        :param mws: Managed web-socket instance
        :return: Message retrieved from underlying-websocket, or None
        '''
        message = None
        try:
            with Timeout(AITOpenMctPlugin.DEFAULT_WS_RECV_TIMEOUT_SECS, False):
                message = mws.web_socket.receive()
        except geventwebsocket.WebSocketError as wserr:
            log.warn(f"Error while reading from web-socket {mws.id}; Error: {wserr}")
            mws.set_error()
        return message

    @staticmethod
    def managed_web_socket_send(mws, message):
        '''
        Sends message to underlying web-socket
        :param mws: Managed web-socket instance
        :param message: Message to be sent
        '''
        if mws.is_alive:
            try:
                mws.web_socket.send(message)
            except geventwebsocket.WebSocketError as wserr:
                log.warn(f"Error while writing to web-socket {mws.id}; Message:'{message}'; Error: {wserr}")
                mws.set_error()

    # ---------------------------------------------------------------------

    def poll_websocket_periodically_while_alive(self, mws):
        while mws.is_alive:
            gsleep(self.DEFAULT_WEBSOCKET_CHECK_SLEEP_SECS)
            self.poll_websocket(mws)

    def poll_websockets(self):
        """
        Polls set of maintained web-sockets to test for:
            - web-socket is considered closed, in which case its removed from internal set;
            - web-socket has message available that affects its state.
        """
        removal_set = set()

        if len(self._socket_set) == 0:
            self.dbg_message("No websockets to poll")
        else:
            for mws in self._socket_set:
                if mws.is_alive:
                    self.poll_websocket(mws)
                else:
                    removal_set.add(mws)

        # Remove the closed/error entries from our set
        if len(removal_set) > 0:
            for rip_mws in removal_set:
                rem_msg = f"Removing closed web-socket record ID {rip_mws.id}"
                if mws.is_error:
                    rem_msg = f"Removing err web-socket record ID {rip_mws.id}"
                self.dbg_message(rem_msg)
                self._socket_set.remove(rip_mws)

    def poll_websocket(self, mws):
        """
        Polls instance of web-socket for message
        :return True if message was processed, False otherwise
        """
        # attempt to read message from websocket and process
        if mws.is_alive:
            message = self.managed_web_socket_recv(mws)
            if message:
                self.process_websocket_mesg(mws, message)
                return True
            else:
                return False

    def process_websocket_mesg(self, mws, message):
        """
        Processes message received from a web-socket.
        Handles the following directives: close, subscribe, unsubscribe
        :param mws: Managed web-socket instance associated with message
        :param message: Web-socket message
        """
        msg_parts = message.split(" ", 1)
        directive = msg_parts[0]
        if directive == 'close':
            self.dbg_message(f"Received 'close' message.  Marking web-socket ID {mws.id} as closed")
            mws.is_closed = True
        elif directive == 'subscribe' and len(msg_parts) > 1:
            self.dbg_message(f"Subscribing websocket {mws.id} to: {msg_parts[1]}")
            mws.subscribe_field(msg_parts[1])
        elif directive == 'unsubscribe':
            self.dbg_message(f"Unsubscribing websocket {mws.id} from: {msg_parts[1]}")
            mws.unsubscribe_field(msg_parts[1])
        else:
            self.dbg_message(f"Unrecognized web-socket message: {message}")

    # ---------------------------------------------------------------------
    # Routing rules

    def _route(self):
        """Performs the Bottle app routing"""

        # Returns OpenMCT formatted tlm dict
        self._app.route("/tlm/dict", callback=self.get_tlm_dict_json)

        # Returns AIT formatted tlm dict
        self._app.route("/tlm/dict/raw", callback=self.get_tlm_dict_raw_json)

        # Estasblished websocket for realtime tlm packets
        self._app.route("/tlm/realtime", callback=self.get_realtime_tlm)

        # Http: tlm query for a given time range
        self._app.route("/tlm/history/<mct_pkt_id>", callback=self.get_historical_tlm)

        # Enable CORS via headers
        self._app.add_hook("after_request", self._cors_headers_hook)

        # Debugging routes
        if self._debugEnabled:
            self._app.route(
                "/tlm/debug/sim/<ait_tlm_pkt_name>", callback=self.mimic_tlm
            )

        # self._App.route('/<pathname:path>', callback=self.get_static_file)

        # Was in the original impl, but not sure we need it.  Don't want to lose
        # it completely tho, just in case.
        # def __setResponseToEventStream():
        #     bottle.response.content_type  = 'text/event-stream'
        #     bottle.response.cache_control = 'no-cache'
        #
        # def __setResponseToJSON():
        #    bottle.response.content_type  = 'application/json'
        #    bottle.response.cache_control = 'no-cache'
