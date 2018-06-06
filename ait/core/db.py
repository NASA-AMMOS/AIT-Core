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
import math

import ait
from ait.core import cfg, cmd, dmc, dtype, evr, tlm, log


# Backend must implement DB-API 2.0 [PEP 249]
# (https://www.python.org/dev/peps/pep-0249/).
Backend = None


@ait.deprecated('connect() will be replaced with SQLiteBackend methods in a future release')
def connect(database):
    """Returns a connection to the given database."""
    if Backend is None:
        raise cfg.AitConfigMissing('database.backend')

    return Backend.connect(database)


@ait.deprecated('create() will be replaced with SQLiteBackend methods in a future release')
def create(database, tlmdict=None):
    """Creates a new database for the given Telemetry Dictionary and
    returns a connection to it.
    """
    if tlmdict is None:
        tlmdict = tlm.getDefaultDict()
    
    dbconn = connect(database)

    for name, defn in tlmdict.items():
        createTable(dbconn, defn)

    return dbconn


@ait.deprecated('createTable() will be replaced with SQLiteBackend methods in a future release')
def createTable(dbconn, pd):
    """Creates a database table for the given PacketDefinition."""
    cols = ('%s %s' % (defn.name, getTypename(defn)) for defn in pd.fields)
    sql  = 'CREATE TABLE IF NOT EXISTS %s (%s)' % (pd.name, ', '.join(cols))

    dbconn.execute(sql)
    dbconn.commit()


@ait.deprecated('getTypename() will be replaced with SQLiteBackend methods in a future release')
def getTypename(defn):
    """Returns the SQL typename required to store the given
    FieldDefinition."""
    return 'REAL' if defn.type.float or defn.dntoeu else 'INTEGER'


@ait.deprecated('insert() will be replaced with SQLiteBackend methods in a future release')
def insert(dbconn, packet):
    """Inserts the given packet into the connected database."""
    values = [ ]
    pd     = packet._defn

    for defn in pd.fields:
        if defn.enum:
            val = getattr(packet.raw, defn.name)
        else:
            val = getattr(packet, defn.name)

        if val is None and defn.name in pd.history:
            val = getattr(packet.history, defn.name)
        
        values.append(val)

    qmark = ['?'] * len(values)
    sql   = 'INSERT INTO %s VALUES (%s)' % (pd.name, ', '.join(qmark))

    dbconn.execute(sql, values)


@ait.deprecated('use() will be replaced with SQLiteBackend methods in a future release')
def use(backend):
    """Use the given database backend, e.g. 'MySQLdb', 'psycopg2',
    'MySQLdb', etc.
    """
    global Backend

    try:
        Backend = importlib.import_module(backend)
    except ImportError:
        msg = 'Could not import (load) database.backend: %s' % backend
        raise cfg.AitConfigError(msg)

if ait.config.get('database.backend'):
    use( ait.config.get('database.backend') )


class GenericBackend(object):
    ''' Generic database backend abstraction

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
                The host to connect to. Defaults to 'localhost'

            database.port
                The port to connect to. Defaults to technology specific value

            database.un
                The username to use when connecting to the database. Defaults
                to a technology specific value

            database.pw
                The password to use when connecting to the database. Defaults
                to a technology specific value

            database.dbname
                The name of the database to create/use. Defaults to 'ait'

        create
            Create a database in the database instance

        insert
            Insert a packet into the database

        query
            Take a string defining a database query and return the results. The
            format of the results is backend specific.

        close
            Close the connection to the database instance and handle any cleanup
    '''

    __metaclass__ = ABCMeta

    _backend = None
    _conn = None

    @abstractmethod
    def __init__(self):
        try:
            self._backend = importlib.import_module(self._backend)
        except ImportError:
            msg = 'Could not import (load) database.backend: %s' % self._backend
            raise cfg.AitConfigError(msg)

    @abstractmethod
    def connect(self, **kwargs):
        '''Connect to a backend's database instance'''
        pass

    @abstractmethod
    def create(self, **kwargs):
        '''Create a database in the instance'''
        pass

    @abstractmethod
    def insert(self, packet, **kwargs):
        '''Insert a record into the database'''
        pass

    @abstractmethod
    def query(self, query, **kwargs):
        '''Query the database instance and return results'''
        pass

    @abstractmethod
    def close(self, **kwargs):
        '''Close connection to the database instance'''
        pass


class InfluxDBBackend(GenericBackend):
    ''' InfluxDB Backend Abstraction
    
    This requires the InfluxDB Python library to be installed and InfluxDB
    to be installed. Note, the InfluxDB Python library is only supports up
    to version 1.2.4. As such, this is only tested against 1.2.4. Newer
    versions may work but are not officially supported by AIT.

    https://github.com/influxdata/influxdb-python
    https://docs.influxdata.com/influxdb
    '''

    _backend = 'influxdb'
    _conn = None

    def __init__(self):
        ''''''
        super(InfluxDBBackend, self).__init__()

    def connect(self, **kwargs):
        ''''''
        host = ait.config.get('database.host', kwargs.get('host', 'localhost'))
        port = ait.config.get('database.port', kwargs.get('port', 8086))
        un = ait.config.get('database.un', kwargs.get('un', 'root'))
        pw = ait.config.get('database.pw', kwargs.get('pw', 'root'))
        dbname = ait.config.get('database.dbname', kwargs.get('database', 'ait'))

        self._conn = self._backend.InfluxDBClient(host, port, un, pw)

        if dbname not in [v['name'] for v in self._conn.get_list_database()]:
            self.create(database=dbname)

        self._conn.switch_database(dbname)

    def create(self, **kwargs):
        ''''''
        dbname = ait.config.get('database.dbname', kwargs.get('database', 'ait'))

        if self._conn is None:
            raise AttributeError('Unable to create database. No connection to database exists.')

        self._conn.create_database(dbname)
        self._conn.switch_database(dbname)

    def insert(self, packet, time=None, **kwargs):
        ''''''
        fields = {}
        pd = packet._defn

        for defn in pd.fields:
            val = getattr(packet.raw, defn.name)

            if pd.history and defn.name in pd.history:
                val = getattr(packet.history, defn.name)
            
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                fields[defn.name] = val

        if len(fields) == 0:
            log.error('No fields present to insert into Influx')
            return

        tags = kwargs.get('tags', {})

        if isinstance(time, dt.datetime):
            time = time.strftime("%Y-%m-%dT%H:%M:%S")

        data = {
            'measurement': pd.name,
            'tags': tags,
            'fields': fields
        }

        if time:
            data['time'] = time

        self._conn.write_points([data])

    def query(self, query, **kwargs):
        ''''''
        return self._conn.query(query)

    def close(self, **kwargs):
        ''''''
        if self._conn:
            self._conn.close()

    @classmethod
    def create_packets_from_results(self, packet_name, result_set):
        ''' Generate AIT Packets from a InfluxDB query ResultSet

        Extract Influx DB query results into one packet per result entry. This
        assumes that telemetry data was inserted in the format generated by
        :func:`InfluxDBBackend.insert`. Complex types such as CMD16 and EVR16 are
        evaluated if they can be properly encoded from the raw value in the
        query result. If there is no opcode / EVR-code for a particular raw
        value the value is skipped (and thus defaulted to 0).

        Args
            packet_name (string)
                The name of the AIT Packet to create from each result entry

            result_set (influxdb.resultset.ResultSet)
                The query ResultSet object to convert into packets

        Returns
            A list of packets extracted from the ResultSet object or None if
            an invalid packet name is supplied.
                
        '''
        try:
            pkt_defn = tlm.getDefaultDict()[packet_name]
        except KeyError:
            log.error('Unknown packet name {} Unable to unpack ResultSet'.format(packet_name))
            return None

        pkt = tlm.Packet(pkt_defn)

        pkts = []
        for r in result_set.get_points():
            new_pkt = tlm.Packet(pkt_defn)

            for f, f_defn in pkt_defn.fieldmap.iteritems():
                field_type_name = f_defn.type.name
                if field_type_name == 'CMD16':
                    if cmd.getDefaultDict().opcodes.get(r[f], None):
                        setattr(new_pkt, f, cmd_def.name)
                elif field_type_name == 'EVR16':
                    if evr.getDefaultDict().codes.get(r[f], None):
                        setattr(new_pkt, f, r[f])
                elif field_type_name == 'TIME8':
                    setattr(new_pkt, f, r[f] / 256.0)
                elif field_type_name == 'TIME32':
                    new_val = dmc.GPS_Epoch + dt.timedelta(seconds=r[f])
                    setattr(new_pkt, f, new_val)
                elif field_type_name == 'TIME40':
                    sec = int(r[f])
                    microsec = r[f] * 1e6
                    new_val = dmc.GPS_Epoch + dt.timedelta(seconds=sec, microseconds=microsec)
                    setattr(new_pkt, f, new_val)
                elif field_type_name == 'TIME64':
                    sec = int(r[f])
                    microsec = r[f] % 1 * 1e6
                    new_val = dmc.GPS_Epoch + dt.timedelta(seconds=sec, microseconds=microsec)
                    setattr(new_pkt, f, new_val)
                else:
                    try:
                        setattr(new_pkt, f, r[f])
                    except KeyError:
                        log.info('Field not found in query results {} Skipping ...'.format(f))

            pkts.append(new_pkt)
        return pkts


class SQLiteBackend(GenericBackend):
    _backend = 'sqlite3'
    _conn = None

    def __init__(self):
        ''''''
        super(SQLiteBackend, self).__init__()

    def connect(self, **kwargs):
        ''''''
        if 'database' not in kwargs:
            kwargs['database'] = 'ait'

        self._conn = self._backend.connect(kwargs['database'])

    def create(self, **kwargs):
        ''''''
        tlmdict = kwargs.get('tlmdict', tlm.getDefaultDict())
        
        self.connect(**kwargs)

        for name, defn in tlmdict.items():
            self.create_table(defn)

    def create_table(self, packet_defn):
        '''Creates a database table for the given PacketDefinition.'''
        cols = ('%s %s' % (defn.name, self._getTypename(defn)) for defn in packet_defn.fields)
        sql  = 'CREATE TABLE IF NOT EXISTS %s (%s)' % (packet_defn.name, ', '.join(cols))

        self._conn.execute(sql)
        self._conn.commit()

    def insert(self, packet, **kwargs):
        ''''''
        values = [ ]
        pd     = packet._defn

        for defn in pd.fields:
            val = getattr(packet.raw, defn.name)

            if val is None and defn.name in pd.history:
                val = getattr(packet.history, defn.name)
            
            values.append(val)

        qmark = ['?'] * len(values)
        sql   = 'INSERT INTO %s VALUES (%s)' % (pd.name, ', '.join(qmark))


        self._conn.execute(sql, values)

    def query(self, query, **kwargs):
        ''''''
        return self._conn.execute(query)
    
    def close(self, **kwargs):
        ''''''
        if self._conn:
            self._conn.close()

    def _getTypename(self, defn):
        """Returns the SQL typename required to store the given
        FieldDefinition."""
        return 'REAL' if defn.type.float or 'TIME' in defn.type.name or defn.dntoeu else 'INTEGER'
