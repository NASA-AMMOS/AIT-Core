# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""AIT Database

The ait.db module provides a general database storage layer for
commands and telemetry with several backends.
"""

from abc import ABCMeta, abstractmethod
import datetime as dt
import importlib
import itertools
import math
import os.path

import sqlite3

import ait
from ait.core import cfg, cmd, dmc, evr, log, tlm


class AITDBResult:
    """AIT Database result wrapper.

    :class:`AITDBResult` is a minimal wrapper around database query results /
    errors. All AIT database APIs that execute a query will return their results
    wrapped in an :class:`AITDBResult` object.

    :class:`AITDbResult` tracks four main attributes. Generally, an unused attribute
    will be None.

    **query**
        The query string(s) execute by the backend. This will be returned as a
        String. Backends are free to format this as appropriate but, in general,
        the contents of this will be a viable query that could be executed without
        modification by the backend whenever possible.

    **results**
        The raw results from the backend library query. This field is populated by
        an API query that doesn't further process results (e.g., into
        :class:`ait.core.tlm.Packet`). Users will need to consult the appropriate
        backend driver documentation for details on the format returned.

    **packets**
        A generator that returns :class:`ait.core.tlm.Packet` objects parsed from
        the executed query. Interfacing with queried data as :class:`ait.core.tlm.Packet`
        objects is the most use case for AIT's database APIs. All "high level" API
        functions return their data as Packet objects. In general, a result
        object will either have data accessible through **packets** or **results**,
        but not both.

    **errors**
        An iterator of errors encountered during query execution. Depending on the
        specific backend implementation, errors and query results (either in
        **results** or **packets**) may or may not be mutually exclusive. Specific
        API endpoints will document this.

    **Example uses:**

        # Query SQLite for all available packets and iterate over the results,
        # printing them to stdout.
        be = db.SQLiteBackend()
        be.connect()
        res = be.query_packets()
        for packet in res.get_packets():
            print(packet)
    """

    def __init__(self, query=None, results=None, packets=None, errors=None):
        self._query = query
        self._results = results
        self._packets = packets
        self._errors = errors

    @property
    def query(self):
        return self._query

    @property
    def errors(self):
        return self._errors

    @property
    def results(self):
        return self._results

    @property
    def has_packets(self):
        return self._packets is not None

    def get_packets(self):
        if self._packets is not None:
            yield from self._packets
        else:
            return []

    def __repr__(self):
        return (
            f"AITDBResult("
            f"has_results: {self._results is not None}, "
            f"has_packets: {self._packets is not None}, "
            f"has_errors: {self._errors is not None})"
        )


class GenericBackend(object):
    """Generic database backend abstraction

    GenericBackend attempts to adequately abstract database operations into
    a small set of common methods. Not all methods will be useful for every
    database type and additional methods may need to be added for future
    database support.

    Generally, the expected method functionality should be

        connect
            Connect to instance of the database via the backend driver. Five
            configuration options are respected by convention in AIT built-in
            backend implementations if they're applicable to the given backend

            database.host
                The host to connect to. Defaults to **localhost**

            database.port
                The port to connect to. Defaults to technology specific value.

            database.un
                The username to use when connecting to the database. Defaults
                to a technology specific value.

            database.pw
                The password to use when connecting to the database. Defaults
                to a technology specific value.

            database.dbname
                The name of the database to create/use. Defaults to **ait**.

        create
            Create a database in the database instance

        insert
            Insert a packet into the database

        query
            Take a string defining a database query and return the results. The
            format of the results is backend specific.

        query_packets
            Query for packet types with optional filters.

        close
            Close the connection to the database instance and handle any cleanup
    """

    __metaclass__ = ABCMeta

    _backend = ""
    _conn = None

    @abstractmethod
    def __init__(self):
        try:
            self._backend = importlib.import_module(self._backend)
        except ImportError:
            msg = "Could not import (load) database.backend: %s" % self._backend
            raise cfg.AitConfigError(msg)

    @abstractmethod
    def connect(self, **kwargs):
        """Connect to a backend's database instance."""
        pass

    @abstractmethod
    def create(self, **kwargs):
        """Create a database in the instance."""
        pass

    @abstractmethod
    def insert(self, packet, time=None, **kwargs):
        """Insert a record into the database."""
        pass

    @abstractmethod
    def query(self, query, **kwargs):
        """Query the database instance and return results."""
        pass

    @abstractmethod
    def query_packets(self, packets=None, start_time=None, end_time=None, **kwargs):
        """Query the database instance for packet objects

        Return all packets of the defined type from the data store, filtering
        over an optional time range. If no parameters are specified, this will
        return all data for all packet types as Packet objects.
        """
        pass

    @classmethod
    @abstractmethod
    def create_packet_from_result(cls, packet_name, result):
        """Return an AIT Packet from a given database query result item

        Creates and returns an AIT Packet denoted by `packet_name` with
        field values set given the contents of `result`. Values that are
        missing in the result will be defaulted in the returned Packet.
        Specific implementations will have caveats related to their backend
        and the limitations of the API.
        """
        pass

    @abstractmethod
    def close(self, **kwargs):
        """Close connection to the database instance."""
        pass


class InfluxDBBackend(GenericBackend):
    """InfluxDB Backend Abstraction

    This requires the InfluxDB Python library to be installed and InfluxDB
    to be installed. Note, the InfluxDB Python library is only supports up
    to version 1.2.4. As such, this is only tested against 1.2.4. Newer
    versions may work but are not officially supported by AIT.

    https://github.com/influxdata/influxdb-python
    https://docs.influxdata.com/influxdb
    """

    _backend = "influxdb"
    _conn = None

    def __init__(self):
        """"""
        super(InfluxDBBackend, self).__init__()

    def connect(self, **kwargs):
        """Connect to an InfluxDB instance

        Connects to an InfluxDB instance and switches to a given database.
        If the database doesn't exist it is created first via :func:`create`.

        **Configuration Parameters**

        host
          The host for the connection. Passed as either the config key
          **database.host** or the kwargs argument **host**. Defaults to
          **localhost**.

        port
          The port for the connection. Passed as either the config key
          **database.port** or the kwargs argument **port**. Defaults to
          **8086**.

        un
          The un for the connection. Passed as either the config key
          **database.un** or the kwargs argument **un**. Defaults to
          **root**.

        pw
          The pw for the connection. Passed as either the config key
          **database.pw** or the kwargs argument **pw**. Defaults to
          **pw**.

        database name
          The database name for the connection. Passed as either
          the config key **database.dbname** or the kwargs argument
          **database**. Defaults to **ait**.
        """
        host = kwargs.get("host", ait.config.get("database.host", "localhost"))
        port = kwargs.get("port", ait.config.get("database.port", 8086))
        un = kwargs.get("un", ait.config.get("database.un", "root"))
        pw = kwargs.get("pw", ait.config.get("database.pw", "root"))
        dbname = kwargs.get("database", ait.config.get("database.dbname", "ait"))

        self._conn = self._backend.InfluxDBClient(host, port, un, pw)

        if dbname not in [v["name"] for v in self._conn.get_list_database()]:
            self.create(database=dbname)

        self._conn.switch_database(dbname)

    def create(self, **kwargs):
        """Create a database in a connected InfluxDB instance

        **Configuration Parameters**

        database name
          The database name to create. Passed as either the config
          key **database.dbname** or the kwargs argument
          **database**. Defaults to **ait**.

        Raises:
            AttributeError:
                If a connection to the database doesn't exist
        """
        dbname = ait.config.get("database.dbname", kwargs.get("database", "ait"))

        if self._conn is None:
            raise AttributeError(
                "Unable to create database. No connection to database exists."
            )

        self._conn.create_database(dbname)
        self._conn.switch_database(dbname)

    def insert(self, packet, time=None, **kwargs):
        """Insert a packet into the database

        Arguments
            packet
                The :class:`ait.core.tlm.Packet` instance to insert into
                the database

            time
                Optional parameter specifying the time value to use when inserting
                the record into the database. Default case does not provide a time
                value so Influx defaults to the current time when inserting the
                record.

            tags
                Optional kwargs argument for specifying a dictionary of tags to
                include when adding the values. Defaults to nothing.

        """
        fields = {}
        pd = packet._defn

        for defn in pd.fields:
            val = getattr(packet.raw, defn.name)

            if pd.history and defn.name in pd.history:
                val = getattr(packet.history, defn.name)

            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                fields[defn.name] = val

        if len(fields) == 0:
            log.error("No fields present to insert into Influx")
            return

        tags = kwargs.get("tags", {})

        if isinstance(time, dt.datetime):
            # time = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            time = time.strftime(dmc.RFC3339_Format)

        data = {"measurement": pd.name, "tags": tags, "fields": fields}

        if time:
            data["time"] = time

        self._conn.write_points([data])

    def _query(self, query, **kwargs):
        """Query the database and return results

        Queries the Influx instance and returns a ResultSet of values. For
        API documentation for InfluxDB-Python check out the project
        documentation. https://github.com/influxdata/influxdb-python

        Arguments
            query
                The query string to send to the database
        """
        return self._conn.query(query, **kwargs)

    def query(self, query, **kwargs):
        """Query the database and return results

        Queries the Influx instance and returns a ResultSet of values. For
        API documentation for InfluxDB-Python check out the project
        documentation. https://github.com/influxdata/influxdb-python

        Arguments:
            query:
                The query string to send to the database

        Returns:
            An :class:`AITDBResult` with the database query results set in
            **results** or errors recorded in **errors**.
        """
        try:
            db_res = self._query(query)
            return AITDBResult(query=query, results=db_res)
        except self._backend.exceptions.InfluxDBClientError as e:
            log.error(f"db.InfluxDBBackend.query failed with exception: {e}")
            return AITDBResult(query=query, errors=[str(e)])

    def query_packets(self, packets=None, start_time=None, end_time=None, **kwargs):
        """Query the database for packet types over a time range.

        Query the database for packet types over a time range. By default, all packet
        types will be queried from the start of the GPS time epoch to current time.
        In other words, you will (probably) receive everything in the database.
        Be careful!

        .. note:
            In general, this function assumes you're automatically inserting packet data
            via AIT's database APIs. If you're handling your data with a custom
            implementation it may or may not work.

        Arguments:
            packets: An iterator containing the packet names over which to query. (
                default: All packet types defined in the telemetry dictionary)

            start_time: A :class:`datetime.datetime` object defining the query time
                range start inclusively. (default: The start of the GPS time Epoch)

            end_time: A :class:`datetime.datetime` object defining the query time
                range end inclusively. (default: The current UTC Zulu time).

        Additional Keyword Arguments:
            yield_packet_time: If True, the packet generator will yield results
                in the form (packet time as datetime object, Packet object). This
                provides access to the time field associated with the packet in
                the database.

            **kwargs**: Additional kwargs are passed to the backend query without
                modification.

        Returns:
            An :class:`AITDBResult` with **packets** set to a generator of all
                packet objects returned by the query in time-sorted order. Otherwise,
                **errors** will contain any encountered errors.

        Raises:
            ValueError: If a provided packet type name cannot be located in the
                telemetry dictionary.
        """
        if packets is not None:
            tlm_dict = tlm.getDefaultDict()
            for name in packets:
                if name not in tlm_dict:
                    msg = f'Invalid packet name "{name}" provided'
                    log.error(msg)
                    raise ValueError(msg)
            pkt_names = ", ".join(packets)
        else:
            pkt_names = ", ".join([f'"{i}"' for i in tlm.getDefaultDict().keys()])

        if start_time is not None:
            stime = start_time.strftime(dmc.RFC3339_Format)
        else:
            stime = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)

        if end_time is not None:
            etime = end_time.strftime(dmc.RFC3339_Format)
        else:
            etime = dt.datetime.utcnow().strftime(dmc.RFC3339_Format)

        yield_packet_time = kwargs.pop("yield_packet_time", False)

        query_string = f"SELECT * FROM \"{pkt_names}\" WHERE time >= '{stime}' AND time <= '{etime}'"

        try:
            db_res = self._query(query_string, **kwargs)
        except self._backend.exceptions.InfluxDBClientError as e:
            log.error(f"db.InfluxDBBackend.query failed with exception: {e}")
            return AITDBResult(query=query_string, errors=[str(e)])

        def influx_results_gen(db_res, **kwargs):
            from ait.core import dmc

            res_items = db_res.items()
            pkt_names = [i[0][0] for i in res_items]
            pkt_gens = [i[1] for i in res_items]

            for packets in itertools.zip_longest(*pkt_gens, fillvalue=None):
                pkt_conv = [
                    (
                        # strptime throws away timezone, so re-enforce UTC
                        dmc.rfc3339_str_to_datetime(d["time"]),
                        InfluxDBBackend.create_packet_from_result(pkt_names[i], d),
                    )
                    for i, d in enumerate(packets)
                    if d is not None
                ]

                pkt_conv.sort(key=lambda x: x[0])

                for t, pkt in pkt_conv:
                    if yield_packet_time:
                        yield (t, pkt)
                    else:
                        yield pkt

        return AITDBResult(
            query=query_string, packets=influx_results_gen(db_res, **kwargs)
        )

    def close(self, **kwargs):
        """Close the database connection"""
        if self._conn:
            self._conn.close()

    @ait.deprecated(  # type: ignore
        "create_packets_from_results has been deprecated. Near equivalent functionality "
        "is available in create_packet_from_result."
    )
    @classmethod
    def create_packets_from_results(cls, packet_name, result_set):
        """Generate AIT Packets from a InfluxDB query ResultSet

        Extract Influx DB query results into one packet per result entry. This
        assumes that telemetry data was inserted in the format generated by
        :func:`InfluxDBBackend.insert`. Complex types such as CMD16 and EVR16 are
        evaluated if they can be properly encoded from the raw value in the
        query result. If there is no opcode / EVR-code for a particular raw
        value the value is skipped (and thus defaulted to 0).

        Arguments
            packet_name (string)
                The name of the AIT Packet to create from each result entry

            result_set (influxdb.resultset.ResultSet)
                The query ResultSet object to convert into packets

        Returns
            A list of packets extracted from the ResultSet object or None if
            an invalid packet name is supplied.

        """
        try:
            tlm.getDefaultDict()[packet_name]
        except KeyError:
            log.error(
                "Unknown packet name {} Unable to unpack ResultSet".format(packet_name)
            )
            return None

        return [
            InfluxDBBackend.create_packet_from_result(packet_name, r)
            for r in result_set.get_points()
        ]

    @classmethod
    def create_packet_from_result(cls, packet_id, result):
        """Create an AIT Packet from an InfluxDB query ResultSet item

        Extract Influx DB query results entry into an AIT packet. This
        assumes that telemetry data was inserted in the format generated by
        :func:`InfluxDBBackend.insert`. Complex types such as CMD16 and EVR16 are
        evaluated if they can be properly encoded from the raw value in the
        query result. If there is no opcode / EVR-code for a particular raw
        value the value is skipped (and thus defaulted to 0).

        TODO: Reevaluate this assumption that missing opcodes / EVR-codes should be
        left as 0 if a match isn't found in the dictionary.

        Arguments
            packet_id (string or PacketDefinition)
                The "id" for the packet to create. If packet_id is a string it must
                name a valid PacketDefintion in the telemetry dictionary. Otherwise,
                it must be a PacketDefinition.

            result (dict)
                The :class:`influxdb.resultset.ResultSet` entry from which values
                should be extracted to form the AIT packet


        Returns
            A :class:`ait.core.tlm.Packet` with values initialized from the values in the
            ResultSet entry. If a field cannot be located in the result entry it will left
            as the default value in the Packet or set to None if it's a CMD / EVR type.
        """
        if isinstance(packet_id, str):
            try:
                pkt_defn = tlm.getDefaultDict()[packet_id]
            except KeyError:
                log.error(f"Unknown packet name {packet_id} Unable to unpack ResultSet")
                return None
        elif isinstance(packet_id, tlm.PacketDefinition):
            pkt_defn = packet_id
        else:
            log.error(f"Unknown packet id type {packet_id}. Unable to unpack ResultSet")
            return None

        new_pkt = tlm.Packet(pkt_defn)
        cmd_dict = cmd.getDefaultDict()
        evr_dict = evr.getDefaultDict()

        for f, f_defn in pkt_defn.fieldmap.items():
            field_type_name = f_defn.type.name
            if field_type_name == "CMD16":
                if cmd_dict.opcodes.get(result[f], None):
                    cmd_def = cmd_dict.opcodes.get(result[f])
                    setattr(new_pkt, f, cmd_def.name)
            elif field_type_name == "EVR16":
                if evr_dict.codes.get(result[f], None):
                    evr_def = evr_dict.codes.get(result[f])
                    setattr(new_pkt, f, evr_def.name)
            elif field_type_name == "TIME8":
                setattr(new_pkt, f, result[f] / 256.0)
            elif field_type_name == "TIME32":
                new_val = dmc.GPS_Epoch + dt.timedelta(seconds=result[f])
                setattr(new_pkt, f, new_val)
            elif field_type_name == "TIME40":
                sec = int(result[f])
                microsec = result[f] % 1 * 1e6
                new_val = dmc.GPS_Epoch + dt.timedelta(
                    seconds=sec, microseconds=microsec
                )
                setattr(new_pkt, f, new_val)
            elif field_type_name == "TIME64":
                sec = int(result[f])
                microsec = result[f] % 1 * 1e6
                new_val = dmc.GPS_Epoch + dt.timedelta(
                    seconds=sec, microseconds=microsec
                )
                setattr(new_pkt, f, new_val)
            else:
                try:
                    setattr(new_pkt, f, result[f])
                except KeyError:
                    log.info(
                        "Field not found in query results {} Skipping ...".format(f)
                    )

        return new_pkt


class SQLiteBackend(GenericBackend):
    _backend = "sqlite3"
    _conn = None

    def __init__(self):
        """"""
        super(SQLiteBackend, self).__init__()

    def connect(self, **kwargs):
        """Connect to a SQLite instance
        If the database doesn't exist it is created first via :func:`create`.

        **Configuration Parameters**

        database name
          The database name of file to "connect" to. Passed as either
          the config key **database.dbname** or the kwargs argument
          **database**. Defaults to **ait.db**.
        """

        dbname = kwargs.get("database", ait.config.get("database.dbname", "ait.db"))
        db_exists = os.path.isfile(dbname)

        self._conn = self._backend.connect(dbname)
        if not db_exists:
            self.create()

    def create(self, **kwargs):
        """Create packet tables in the connected database

        **Configuration Parameters**

        tlmdict
            The :class:`ait.core.tlm.TlmDict` instance to use. Defaults to
            the currently configured telemetry dictionary.
        """
        tlmdict = kwargs.get("tlmdict", tlm.getDefaultDict())
        for _name, defn in tlmdict.items():
            self._create_table(defn)

    def _create_table(self, packet_defn):
        """Creates a database table for the given PacketDefinition
        Automatically adds a self-filling time column

        Arguments
            packet_defn
                The :class:`ait.core.tlm.PacketDefinition` instance for which a table entry
                should be made.
        """
        time_def = "time DATETIME DEFAULT(STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'NOW')), "
        sql = 'CREATE TABLE IF NOT EXISTS "%s" (%s)' % (
            packet_defn.name,
            time_def + "PKTDATA BLOB NOT NULL",
        )

        self._conn.execute(sql)
        self._conn.commit()

    def insert(self, packet, time=None, **kwargs):
        """Insert a packet into the database

        Arguments
            packet
                The :class:`ait.core.tlm.Packet` instance to insert into
                the database

        """
        if isinstance(time, dt.datetime):
            time = time.strftime(dmc.RFC3339_Format)

        sql = f'INSERT INTO "{packet._defn.name}" (PKTDATA, time) VALUES (?, ?)' \
            if time \
            else f'INSERT INTO "{packet._defn.name}" (PKTDATA) VALUES (?)'
        values = (sqlite3.Binary(packet._data), time) \
            if time \
            else (sqlite3.Binary(packet._data))

        self._conn.execute(sql, values)
        self._conn.commit()

    def _query(self, query, **kwargs):
        """Query the database and return results

        Queries the SQLite instance and returns raw results.

        Arguments:
            query:
                The query string to send to the database

        Returns:
            The raw results of the database query.

        Raises:
            Any sqlite3.OperationalError or other sqlite-specific exceptions
            raised from the driver during execution of the query.
        """
        return self._conn.execute(query)

    def query(self, query, **kwargs):
        """Query the database and return results

        Queries the SQLite instance and returns the raw results object.
        API documentation for Python's SQLite3 interface provides format
        details. https://docs.python.org/3.7/library/sqlite3.html

        Arguments:
            query:
                The query string to send to the database

        Returns:
            An :class:`AITDBResult` with the database query results set in
            **results** or errors recorded in **errors**.
        """
        try:
            results = self._query(query, **kwargs)
            return AITDBResult(query=query, results=results)
        except self._backend.OperationalError as e:
            log.error(f"db.SQLiteBackend.query failed with exception: {e}")
            return AITDBResult(query=query, errors=[str(e)])

    def query_packets(self, packets=None, start_time=None, end_time=None, **kwargs):
        """Query the database for packet types over a time range.

        Query the database for packet types over a time range. By default, all packet
        types will be queried from the start of the GPS time epoch to current time.
        In other words, you will (probably) receive everything in the database.
        Be careful!

        .. note:
            In general, this function assumes you're automatically inserting packet data
            via AIT's database APIs. If you're handling your data with a custom
            implementation it may or may not work.

        Arguments:
            packets: An iterator containing the packet names over which to query. (
                default: All packet types defined in the telemetry dictionary)

            start_time: A :class:`datetime.datetime` object defining the query time
                range start inclusively. (default: The start of the GPS time Epoch)

            end_time: A :class:`datetime.datetime` object defining the query time
                range end inclusively. (default: The current UTC Zulu time).

        Additional Keyword Arguments:
            yield_packet_time: If True, the packet generator will yield results
                in the form (packet time as datetime object, Packet object). This
                provides access to the time field associated with the packet in
                the database.

            **kwargs**: Additional kwargs are passed to the backend query without
                modification.

        Returns:
            An :class:`AITDBResult` with **packets** set to a generator of all
                packet objects returned by the query in time-sorted order. The
                **errors** attribute will include any errors encountered.

                Note, because queries are broken up by packet type, this could contain
                both results and errors.

        Raises:
            ValueError: If a provided packet type name cannot be located in the
                telemetry dictionary.
        """
        if packets is not None:
            tlm_dict = tlm.getDefaultDict()
            for name in packets:
                try:
                    tlm_dict[name]
                except KeyError:
                    msg = 'Invalid packet name "{name}" provided'
                    log.error(msg)
                    raise ValueError(msg)
        else:
            packets = list(tlm.getDefaultDict().keys())

        if start_time is not None:
            stime = start_time.strftime(dmc.RFC3339_Format)
        else:
            stime = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)

        if end_time is not None:
            etime = end_time.strftime(dmc.RFC3339_Format)
        else:
            etime = dt.datetime.utcnow().strftime(dmc.RFC3339_Format)

        yield_packet_time = kwargs.pop("yield_packet_time", False)

        results = []
        errs = []
        query = []
        for pkt in packets:
            query_string = f'SELECT * FROM "{pkt}" WHERE time >= "{stime}" AND time <= "{etime}" ORDER BY time ASC'
            query.append(query_string)

            try:
                results.append((pkt, self._query(query_string)))
            except self._backend.OperationalError as e:
                log.error(f"db.SQLiteBackend.query failed with exception: {e}")
                errs.append(str(e))

        def sqlite_results_gen(results, **kwargs):
            from ait.core import dmc

            for packets in itertools.zip_longest(
                *[r[1] for r in results], fillvalue=None
            ):
                pkt_conv = [
                    (
                        # strptime throws away timezone, so re-enforce UTC
                        dmc.rfc3339_str_to_datetime(d[0]),
                        SQLiteBackend.create_packet_from_result(results[i][0], d[1]),
                    )
                    for i, d in enumerate(packets)
                    if d is not None
                ]

                pkt_conv.sort(key=lambda x: x[0])

                for t, pkt in pkt_conv:
                    if yield_packet_time:
                        yield (t, pkt)
                    else:
                        yield pkt

        return AITDBResult(
            query="; ".join(query),
            packets=sqlite_results_gen(results, **kwargs),
            errors=errs if len(errs) > 0 else None,
        )

    def close(self, **kwargs):
        """Close the database connection."""
        if self._conn:
            self._conn.close()

    @classmethod
    def create_packet_from_result(cls, packet_name, data):
        try:
            pkt_defn = tlm.getDefaultDict()[packet_name]
        except KeyError:
            log.error(
                "Unknown packet name {}. Unable to unpack SQLite result".format(
                    packet_name
                )
            )
            return None

        return tlm.Packet(pkt_defn, data=data)
