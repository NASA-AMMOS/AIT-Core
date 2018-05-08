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

import importlib

import ait
from ait.core import cfg, tlm


# Backend must implement DB-API 2.0 [PEP 249]
# (https://www.python.org/dev/peps/pep-0249/).
Backend = None


def connect(database):
    """Returns a connection to the given database."""
    if Backend is None:
        raise cfg.AitConfigMissing('database.backend')

    return Backend.connect(database)


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

    try:
        Backend = importlib.import_module(backend)
    except ImportError:
        msg = 'Could not import (load) database.backend: %s' % backend
        raise cfg.AitConfigError(msg)


if ait.config.get('database.backend'):
    use( ait.config.get('database.backend') )
