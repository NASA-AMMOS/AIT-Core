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
import inspect
import os
import sqlite3
import unittest

import nose.tools
from unittest import mock

import ait.core.cfg as cfg
import ait.core.db as db
import ait.core.dmc as dmc
import ait.core.tlm as tlm


class TestDBResultObject(unittest.TestCase):
    def test_default_init(self):
        res = db.AITDBResult()
        assert res.query is None
        assert res.results is None
        assert res._packets is None
        assert list(res.get_packets()) == []
        assert res.errors is None

        query = 'foobar'
        results = [1, 2, 3]
        errors = ['error1', 'error2']
        res = db.AITDBResult(query=query, results=results, errors=errors)
        assert res.query == query
        assert res.results == results
        assert res.errors == errors

    def test_get_packets(self):
        # AITDBResult expects to receive packet results to be provided
        # in a form from which it can `yield from`. If it doesn't get
        # an object it returns an empty list.

        res = db.AITDBResult()
        assert list(res.get_packets()) == []

        res = db.AITDBResult(packets=range(5))
        assert list(res.get_packets()) == [0, 1, 2, 3, 4]
        assert inspect.isgenerator(res.get_packets())


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
        with open(self.test_yaml_file, 'wt') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        pkt_defn = tlmdict['Packet1']
        pkt = tlm.Packet(pkt_defn, bytearray(range(pkt_defn.nbytes)))

        now = dt.datetime.utcnow()
        sqlbackend.insert(pkt, time=now)
        sqlbackend._conn.write_points.assert_called_with([{
            'measurement': 'Packet1',
            'time': now.strftime(dmc.RFC3339_Format),
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
    def test_influx_query_calldown(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        sqlbackend.query('SELECT * FROM table')
        sqlbackend._conn.query.assert_called_with('SELECT * FROM table')

    def test_query_return_types(self):
        # This test is only relevant if we can raise a specific exception. Skip otherwise
        # Tested and running with python-influxdb=5.3.0
        try:
            sqlbackend = db.InfluxDBBackend()
        except cfg.AitConfigError:
            self.skipTest('Test requires database library to be installed')
        sqlbackend._conn = mock.MagicMock()
        sqlbackend._query = mock.MagicMock()

        # Check that a successful query returns a properly formatted AITDBResult
        ret_val = [1, 2, 3]
        query_string = 'select * from table'
        sqlbackend._query.return_value = ret_val
        results = sqlbackend.query(query_string)
        assert isinstance(results, db.AITDBResult)
        assert results.query == query_string
        assert results.results == ret_val

        # Check that a failed query returns a properly formatted AITDBResult
        sqlbackend._query.side_effect = sqlbackend._backend.exceptions.InfluxDBClientError('foo')
        results = sqlbackend.query(query_string)
        assert results.query == query_string
        assert results.errors == ['foo']

    @mock.patch('importlib.import_module')
    def test_query_packets_calldown(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        start = dmc.GPS_Epoch
        end = dt.datetime.utcnow()
        packets = [list(tlm.getDefaultDict().keys())[0]]

        sqlbackend.query_packets(packets=packets, start_time=start, end_time=end)

        packets = ', '.join(packets)
        start = start.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        query = f"SELECT * FROM {packets} WHERE time >= '{start}' AND time <= '{end}'"

        assert sqlbackend._conn.query.call_args[0][0] == query

    @mock.patch('importlib.import_module')
    def test_query_packets_arg_handling(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        # Test no packet provided handling
        #######################################
        start = dmc.GPS_Epoch
        end = dt.datetime.utcnow()

        sqlbackend.query_packets(start_time=start, end_time=end)

        packets = ', '.join([f'"{i}"' for i in tlm.getDefaultDict().keys()])
        start = start.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        query = f"SELECT * FROM {packets} WHERE time >= '{start}' AND time <= '{end}'"

        assert sqlbackend._conn.query.call_args[0][0] == query
        sqlbackend._conn.reset_mock()

        # Test no start time handling
        #######################################
        end = dt.datetime.utcnow()

        sqlbackend.query_packets(end_time=end)

        packets = ', '.join([f'"{i}"' for i in tlm.getDefaultDict().keys()])
        start = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        query = f"SELECT * FROM {packets} WHERE time >= '{start}' AND time <= '{end}'"

        assert sqlbackend._conn.query.call_args[0][0] == query
        sqlbackend._conn.reset_mock()

        # Test no end time handling
        #######################################
        sqlbackend.query_packets()

        packets = ', '.join([f'"{i}"' for i in tlm.getDefaultDict().keys()])
        start = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)
        end = dt.datetime.utcnow()
        query = f"SELECT * FROM {packets} WHERE time >= '{start}' AND time <= '{end}'"

        exec_end_time = dt.datetime.strptime(
            sqlbackend._conn.query.call_args[0][0].split("'")[-2],
            dmc.RFC3339_Format
        )

        assert (end - exec_end_time).seconds < 1
        sqlbackend.query_packets()

        # Test bad packet name exception
        #######################################
        nose.tools.assert_raises(
            ValueError,
            sqlbackend.query_packets,
            packets=['not_a_valid_packet']
        )

    def test_query_fail_handling(self):
        # This test is only relevant if we can raise a specific exception. Skip otherwise
        # Tested and running with python-influxdb=5.3.0
        try:
            sqlbackend = db.InfluxDBBackend()
        except cfg.AitConfigError:
            self.skipTest('Test requires database library to be installed')

        sqlbackend._conn = mock.MagicMock()
        sqlbackend._query = mock.MagicMock()
        sqlbackend._query.side_effect = sqlbackend._backend.exceptions.InfluxDBClientError('foo')

        res = sqlbackend.query_packets()
        assert res.errors == ['foo']

    @mock.patch('importlib.import_module')
    def test_query_success_handling(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        res_mock = mock.MagicMock()
        res_mock.items = mock.MagicMock(return_value=[
            (
                ('1553_HS_Packet', None), [
                    {
                        'time': '2020-11-17T21:12:17.677316Z',
                        'Current_A': 0,
                        'Voltage_A': 0,
                        'Voltage_B': 0,
                        'Voltage_C': 0,
                        'Voltage_D': 0
                    }, {
                        'time': '2020-11-17T21:12:18.675379Z',
                        'Current_A': 1,
                        'Voltage_A': 1,
                        'Voltage_B': 1,
                        'Voltage_C': 1,
                        'Voltage_D': 1
                    }, {
                        'time': '2020-11-17T21:12:19.682312Z',
                        'Current_A': 2,
                        'Voltage_A': 2,
                        'Voltage_B': 2,
                        'Voltage_C': 2,
                        'Voltage_D': 2
                    }
                ]
            )]
        )

        sqlbackend._query = mock.MagicMock(return_value=res_mock)

        res = sqlbackend.query_packets()

        assert isinstance(res, db.AITDBResult)
        assert res._packets is not None

        res_pkts = list(res.get_packets())
        assert len(res_pkts) == 3
        assert isinstance(res_pkts[0], tlm.Packet)

        assert res_pkts[0].Voltage_A == 0
        assert res_pkts[1].Voltage_A == 1
        assert res_pkts[2].Voltage_A == 2

    @mock.patch('importlib.import_module')
    def test_query_packet_time_inclusion(self, importlib_mock):
        sqlbackend = db.InfluxDBBackend()
        sqlbackend._conn = mock.MagicMock()

        ret_data = [
            (
                ('1553_HS_Packet', None), [
                    {
                        'time': '2020-11-17T21:12:17.677316Z',
                        'Current_A': 0,
                        'Voltage_A': 0,
                        'Voltage_B': 0,
                        'Voltage_C': 0,
                        'Voltage_D': 0
                    }, {
                        'time': '2020-11-17T21:12:18.675379Z',
                        'Current_A': 1,
                        'Voltage_A': 1,
                        'Voltage_B': 1,
                        'Voltage_C': 1,
                        'Voltage_D': 1
                    }, {
                        'time': '2020-11-17T21:12:19.682312Z',
                        'Current_A': 2,
                        'Voltage_A': 2,
                        'Voltage_B': 2,
                        'Voltage_C': 2,
                        'Voltage_D': 2
                    }
                ]
            )]
        res_mock = mock.MagicMock()
        res_mock.items = mock.MagicMock(return_value=ret_data)

        sqlbackend._query = mock.MagicMock(return_value=res_mock)

        res = sqlbackend.query_packets(yield_packet_time=True)

        assert isinstance(res, db.AITDBResult)
        assert res._packets is not None

        res_pkts = list(res.get_packets())
        assert len(res_pkts) == 3
        assert isinstance(res_pkts[0], tuple)

        for i, test_data in enumerate(ret_data[0][1]):
            assert dt.datetime.strptime(test_data['time'], dmc.RFC3339_Format) == res_pkts[i][0]
            assert res_pkts[i][1].Voltage_A == i

    @mock.patch('importlib.import_module')
    def test_packet_creation_from_result(self, importlib_mock):
        yaml_doc = """
        - !Packet
          name: TestPacket
          fields:
            - !Field
              name: SampleField
              type: MSB_U16
            - !Field
              name: SampleTime
              type: TIME64
            - !Field
              name: SampleTime8
              type: TIME8
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
        with open(self.test_yaml_file, 'wt') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        res = {
            'time': '2020-11-17T21:12:17.677316Z',
            'SampleField': 1,
            'SampleTime': 33752069.101124,
            'SampleTime8': 100,
            'SampleTime32': 168496141,
            'SampleTime40': 1113733097.03125,
            'SampleCmd16': 1,
            'SampleEvr16': 1
        }

        pkt = db.InfluxDBBackend.create_packet_from_result(tlmdict['TestPacket'], res)

        for f in pkt._defn.fields:
            assert getattr(pkt.raw, f.name) == res[f.name]

        os.remove(self.test_yaml_file)


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

        # Check default database naming
        sqlbackend.connect()
        assert sqlbackend._backend.connect.called
        sqlbackend._backend.connect.assert_called_with('ait.db')
        sqlbackend._backend.reset_mock()

        # Check custom database naming
        sqlbackend.connect(database='foo.db')
        assert sqlbackend._backend.connect.called
        sqlbackend._backend.connect.assert_called_with('foo.db')

        # Backend should only call self.create if a database doesn't exist
        #
        # Mock return_value handling wasn't cooperating with decorators
        # so we'll handle it manually instead ...
        import os.path
        isfile_mock = mock.MagicMock(return_value=True)
        isfile_orig = os.path.isfile
        os.path.isfile = isfile_mock

        sqlbackend.create = mock.MagicMock()

        assert isfile_mock is os.path.isfile
        isfile_mock.return_value = True

        sqlbackend.connect()
        assert sqlbackend.create.called is False

        isfile_mock.return_value = False
        sqlbackend.connect()
        assert sqlbackend.create.called

        os.path.isfile = isfile_orig


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
        with open(self.test_yaml_file, 'wt') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend.connect = mock.MagicMock()
        sqlbackend._create_table = mock.MagicMock()

        sqlbackend.create(tlmdict=tlmdict)

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
        with open(self.test_yaml_file, 'wt') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        sqlbackend._create_table(tlmdict['Packet1'])
        sqlbackend._conn.execute.assert_called_with(
            'CREATE TABLE IF NOT EXISTS "Packet1" (time DATETIME DEFAULT(STRFTIME(\'%Y-%m-%dT%H:%M:%fZ\', \'NOW\')), PKTDATA BLOB NOT NULL)'
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
        with open(self.test_yaml_file, 'wt') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        pkt_defn = tlmdict['Packet1']
        pkt = tlm.Packet(pkt_defn, bytearray(range(pkt_defn.nbytes)))

        # We can't fully test this call given the modification to the packet
        # data on insert. Better than nothing I suppose.
        sqlbackend.insert(pkt)
        assert 'INSERT INTO "Packet1" (PKTDATA) VALUES (?)' in sqlbackend._conn.execute.call_args[0]

        os.remove(self.test_yaml_file)

    def test_sqlite_query_calldown(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        sqlbackend.query('SELECT * FROM table')
        sqlbackend._conn.execute.assert_called_with('SELECT * FROM table')

    def test_query_return_types(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()
        sqlbackend._query = mock.MagicMock()

        # Check that a successful query returns a properly formatted AITDBResult
        ret_val = [1, 2, 3]
        query_string = 'select * from table'
        sqlbackend._query.return_value = ret_val
        results = sqlbackend.query(query_string)
        assert isinstance(results, db.AITDBResult)
        assert results.query == query_string
        assert results.results == ret_val

        # Check that a failed query returns a properly formatted AITDBResult
        sqlbackend._query.side_effect = sqlbackend._backend.OperationalError('foo')
        results = sqlbackend.query(query_string)
        assert results.query == query_string
        assert results.errors == ['foo']

    def test_query_packets_calldown(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        start = dmc.GPS_Epoch
        end = dt.datetime.utcnow()
        packets = [list(tlm.getDefaultDict().keys())[0]]

        sqlbackend.query_packets(packets=packets, start_time=start, end_time=end)

        start = start.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        for i, pkt in enumerate(packets):
            query = f'SELECT * FROM "{pkt}" WHERE time >= "{start}" AND time <= "{end}" ORDER BY time ASC'
            assert sqlbackend._conn.execute.call_args[i][0] == query

    def test_query_packets_arg_handling(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()
        query_string = 'SELECT * FROM "{}" WHERE time >= "{}" AND time <= "{}" ORDER BY time ASC'

        # Test no packet provided handling
        #######################################
        start = dmc.GPS_Epoch
        end = dt.datetime.utcnow()

        res = sqlbackend.query_packets(start_time=start, end_time=end)

        packets = list(tlm.getDefaultDict().keys())
        start = start.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        query = query_string.format(packets, start, end)

        for i, pkt in enumerate(packets):
            query = f'SELECT * FROM "{pkt}" WHERE time >= "{start}" AND time <= "{end}" ORDER BY time ASC'
            assert sqlbackend._conn.execute.call_args_list[i][0][0] == query

        sqlbackend._conn.reset_mock()

        # Test no start time handling
        #######################################
        end = dt.datetime.utcnow()

        packets = [list(tlm.getDefaultDict().keys())[0]]

        sqlbackend.query_packets(packets=packets, end_time=end)

        start = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)
        end = end.strftime(dmc.RFC3339_Format)
        query = query_string.format(packets[0], start, end)

        assert sqlbackend._conn.execute.call_args[0][0] == query
        sqlbackend._conn.reset_mock()

        # Test no end time handling
        #######################################
        packets = [list(tlm.getDefaultDict().keys())[0]]

        sqlbackend.query_packets(packets=packets)

        start = dmc.GPS_Epoch.strftime(dmc.RFC3339_Format)
        end = dt.datetime.utcnow()
        query = query_string.format(packets, start, end)

        exec_end_time = dt.datetime.strptime(
            sqlbackend._conn.execute.call_args[0][0].split('"')[-2],
            dmc.RFC3339_Format
        )

        assert (end - exec_end_time).seconds < 1
        sqlbackend.query_packets()

        # Test bad packet name exception
        #######################################
        nose.tools.assert_raises(
            ValueError,
            sqlbackend.query_packets,
            packets=['not_a_valid_packet']
        )

    def test_query_fail_handling(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()
        sqlbackend._query = mock.MagicMock()
        sqlbackend._query.side_effect = sqlbackend._backend.OperationalError('foo')

        res = sqlbackend.query_packets()
        for e in res.errors:
            assert e == 'foo'

    def test_query_success_handling(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        res_mock = mock.MagicMock()
        res_mock.return_value=[
            ('2020-12-02T00:41:43.199Z', b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            ('2020-12-02T00:41:44.200Z', b'\x00\x01\x00\x01\x00\x01\x00\x01\x00\x01'),
            ('2020-12-02T00:41:45.205Z', b'\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02'),
            ('2020-12-02T00:41:46.211Z', b'\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03'),
            ('2020-12-02T00:41:47.216Z', b'\x00\x04\x00\x04\x00\x04\x00\x04\x00\x04'),
            ('2020-12-02T00:41:48.221Z', b'\x00\x05\x00\x05\x00\x05\x00\x05\x00\x05')
        ]

        sqlbackend._query = res_mock

        res = sqlbackend.query_packets(packets=['1553_HS_Packet'])

        assert isinstance(res, db.AITDBResult)
        assert res._packets is not None

        res_pkts = list(res.get_packets())
        assert len(res_pkts) == 6
        assert isinstance(res_pkts[0], tlm.Packet)

        assert res_pkts[0].Voltage_A == 0
        assert res_pkts[1].Voltage_A == 1
        assert res_pkts[2].Voltage_A == 2
        assert res_pkts[3].Voltage_A == 3
        assert res_pkts[4].Voltage_A == 4
        assert res_pkts[5].Voltage_A == 5

    def test_query_packet_time_inclusion(self):
        sqlbackend = db.SQLiteBackend()
        sqlbackend._conn = mock.MagicMock()

        ret_data = [
            ('2020-12-02T00:41:43.199Z', b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            ('2020-12-02T00:41:44.200Z', b'\x00\x01\x00\x01\x00\x01\x00\x01\x00\x01'),
            ('2020-12-02T00:41:45.205Z', b'\x00\x02\x00\x02\x00\x02\x00\x02\x00\x02'),
            ('2020-12-02T00:41:46.211Z', b'\x00\x03\x00\x03\x00\x03\x00\x03\x00\x03'),
            ('2020-12-02T00:41:47.216Z', b'\x00\x04\x00\x04\x00\x04\x00\x04\x00\x04'),
            ('2020-12-02T00:41:48.221Z', b'\x00\x05\x00\x05\x00\x05\x00\x05\x00\x05')
        ]
        res_mock = mock.MagicMock()
        res_mock.return_value=ret_data
        sqlbackend._query = res_mock

        res = sqlbackend.query_packets(packets=['1553_HS_Packet'], yield_packet_time=True)

        assert isinstance(res, db.AITDBResult)
        assert res._packets is not None

        res_pkts = list(res.get_packets())
        assert len(res_pkts) == 6
        assert isinstance(res_pkts[0], tuple)

        for i, test_data in enumerate(ret_data):
            assert dt.datetime.strptime(ret_data[i][0], dmc.RFC3339_Format) == res_pkts[i][0]
            assert res_pkts[i][1].Voltage_A == i

