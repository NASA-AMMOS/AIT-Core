#!/usr/bin/env python2.7

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

import datetime as dt
import os
import unittest

import mock

import ait.core.db as db
import ait.core.tlm as tlm


class TestInfluxDBBackend(unittest.TestCase):
    test_yaml_file = '/tmp/test.yaml'

    @mock.patch('importlib.import_module')
    def test_influx_backend_init(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()

        importlib_mock.assert_called_with('influxdb')

    @mock.patch('importlib.import_module')
    def test_influx_connect(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._backend = mock.MagicMock()

        sqlbackend.connect()

        # Make backend connection
        assert sqlbackend._backend.InfluxDBClient.called
        sqlbackend._backend.InfluxDBClient.assert_called_with(
            'localhost', 8086, 'root', 'root'
        )

        # Switch to default database
        assert sqlbackend._conn.switch_database.called
        sqlbackend._conn.switch_database.assert_called_with('ait')
        sqlbackend._backend.reset_mock()

        sqlbackend.connect(database='foo')

        # make backend connection
        assert sqlbackend._backend.InfluxDBClient.called
        sqlbackend._backend.InfluxDBClient.assert_called_with(
            'localhost', 8086, 'root', 'root'
        )

        # Switch to custom database
        assert sqlbackend._conn.switch_database.called
        sqlbackend._conn.switch_database.assert_called_with('foo')

    @mock.patch('importlib.import_module')
    def test_influx_create(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._backend = mock.MagicMock()
        sqlbackend.create = mock.MagicMock()

        sqlbackend.create()
        assert sqlbackend.create.called

    @mock.patch('importlib.import_module')
    def test_influx_insert(self, importlib_mock):
        yaml_doc = """
        - !Packet
          name: Packet1
          history:
            - col1
          fields:
            - !Field
              name:       col1
              desc:       test column 1
              type:       MSB_U16
              enum:
                a: testa
            - !Field
              name: SampleTime
              type: TIME64
            - !Field
              name: SampleTime32
              type: TIME32
            - !Field
              name: SampleTime40
              type: TIME40
            - !Field
              name: SampleEvr16
              type: EVR16
            - !Field
              name: SampleCmd16
              type: CMD16
        """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        pkt_defn = tlmdict['Packet1']
        pkt = tlm.Packet(pkt_defn, bytearray(xrange(pkt_defn.nbytes)))

        now = dt.datetime.utcnow()
        sqlbackend.insert(pkt, time=now)
        sqlbackend._conn.write_points.assert_called_with([{
            'measurement': 'Packet1',
            'time': now.strftime('%Y-%m-%dT%H:%M:%S'),
            'tags': {},
            'fields': {
                'col1': 1,
                'SampleTime': 33752069.10112411,
                'SampleTime32': 168496141,
                'SampleTime40': 235868177.0703125,
                'SampleCmd16': 5398,
                'SampleEvr16': 4884
            }
        }])
        sqlbackend._conn.reset_mock()

        # Insert without a timestamp
        sqlbackend.insert(pkt)
        sqlbackend._conn.write_points.assert_called_with([{
            'measurement': 'Packet1',
            'tags': {},
            'fields': {
                'col1': 1,
                'SampleTime': 33752069.10112411,
                'SampleTime32': 168496141,
                'SampleTime40': 235868177.0703125,
                'SampleCmd16': 5398,
                'SampleEvr16': 4884
            }
        }])
        sqlbackend._conn.reset_mock()

        # Insert with additional tags
        sqlbackend.insert(pkt, tags={'testNum': '3'})
        sqlbackend._conn.write_points.assert_called_with([{
            'measurement': 'Packet1',
            'tags': {'testNum': '3'},
            'fields': {
                'col1': 1,
                'SampleTime': 33752069.10112411,
                'SampleTime32': 168496141,
                'SampleTime40': 235868177.0703125,
                'SampleCmd16': 5398,
                'SampleEvr16': 4884
            }
        }])
        sqlbackend._conn.reset_mock()

        os.remove(self.test_yaml_file)

    @mock.patch('importlib.import_module')
    def test_influx_query(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        sqlbackend.query('SELECT * FROM table')
        sqlbackend._conn.query.assert_called_with('SELECT * FROM table')


class TestSQLiteBackend(unittest.TestCase):
    test_yaml_file = '/tmp/test.yaml'

    @mock.patch('importlib.import_module')
    def test_sqlite_backend_init(self, importlib_mock):
        sqlbackend = db.SQLiteBackend()

        importlib_mock.assert_called_with('sqlite3')

    @mock.patch('importlib.import_module')
    def test_sqlite_connect(self, importlib_mock):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._backend = mock.MagicMock()

        sqlbackend.connect()
        assert sqlbackend._backend.connect.called
        sqlbackend._backend.connect.assert_called_with('ait')
        sqlbackend._backend.reset_mock()

        sqlbackend.connect(database='foo')
        assert sqlbackend._backend.connect.called
        sqlbackend._backend.connect.assert_called_with('foo')

    @mock.patch('importlib.import_module')
    def test_sqlite_create(self, importlib_mock):
        yaml_doc = """
        - !Packet
          name: Packet1
          fields:
            - !Field
              name:       col1
              desc:       test column 1
              type:       MSB_U16
              enum:
                a: testa
            - !Field
              name: SampleTime64
              type: TIME64
        """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend.connect = mock.MagicMock()
        sqlbackend._create_table = mock.MagicMock()

        sqlbackend.create(tlmdict=tlmdict)
        
        assert sqlbackend.connect.called
        sqlbackend._create_table.assert_called_with(tlmdict['Packet1'])

        os.remove(self.test_yaml_file)

    @mock.patch('importlib.import_module')
    def test_sqlite_create_table(self, importlib_mock):
        yaml_doc = """
        - !Packet
          name: Packet1
          history:
            - col1
          fields:
            - !Field
              name:       col1
              desc:       test column 1
              type:       MSB_U16
              enum:
                a: testa
            - !Field
              name: SampleTime
              type: TIME64
        """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        sqlbackend._create_table(tlmdict['Packet1'])
        sqlbackend._conn.execute.assert_called_with(
            'CREATE TABLE IF NOT EXISTS Packet1 (col1 INTEGER, SampleTime REAL)'
        )

        os.remove(self.test_yaml_file)

    @mock.patch('importlib.import_module')
    def test_sqlite_insert(self, importlib_mock):
        yaml_doc = """
        - !Packet
          name: Packet1
          history:
            - col1
          fields:
            - !Field
              name:       col1
              desc:       test column 1
              type:       MSB_U16
              enum:
                a: testa
            - !Field
              name: SampleTime
              type: TIME64
        """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        pkt_defn = tlmdict['Packet1']
        pkt = tlm.Packet(pkt_defn, bytearray(xrange(pkt_defn.nbytes)))

        sqlbackend.insert(pkt)
        sqlbackend._conn.execute.assert_called_with(
            'INSERT INTO Packet1 VALUES (?, ?)', [1, 33752069.10112411]
        )

        os.remove(self.test_yaml_file)
