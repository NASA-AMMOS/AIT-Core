# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""BLISS Database

The bliss.db module provides a general database storage layer for
commands and telemetry with several backends.
"""

import importlib
import sqlite3

from bliss.core import tlm


# Backend must implement DB-API 2.0 (PEP 249)
Backend = sqlite3


def connect(dbname):
    """Returns a connection to the given database."""
    return Backend.connect(dbname)


def create(dbname, tlmdict=None):
    """Creates a new database for the given Telemetry Dictionary and
    returns a connection to it.
    """
    if tlmdict is None:
        tlmdict = tlm.getDefaultDict()
    
    dbconn = connect(dbname)

    for name, defn in tlmdict.items():
        createTable(dbconn, defn)

    return dbconn


def createTable(dbconn, pd):
    """Creates a database table for the given PacketDefinition."""
    cols = ('%s %s' % (defn.name, getTypename(defn)) for defn in pd.fields)
    sql  = 'CREATE TABLE IF NOT EXISTS %s (%s)' % (pd.name, ', '.join(cols))

    dbconn.execute(sql)
    dbconn.commit()


def getTypename(defn):
    """Returns the SQL typename required to store the given
    FieldDefinition."""
    return 'REAL' if defn.type.float or defn.dntoeu else 'INTEGER'


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


def use(backend):
    """Use the given database backend, e.g. 'MySQLdb', 'psycopg2',
    'MySQLdb', etc.
    """
    global Backend
    Backend = importlib.import_module(backend)
