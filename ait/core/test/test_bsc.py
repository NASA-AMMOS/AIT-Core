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

import gevent.monkey
gevent.monkey.patch_all()

import datetime
import logging
import mock
import os
import platform
import socket
import time

import gevent
import nose
import nose.tools

from ait.core import bsc, pcap


class TestSocketStreamCapturer(object):
    @mock.patch('gevent.socket.socket')
    def test_mocked_udp_socket(self, socket_mock):
        handler = {'name':'name', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer([handler], ['', 9000], 'udp')
        socket_mock.assert_called_with(gevent.socket.AF_INET,
                                       gevent.socket.SOCK_DGRAM)
        assert sl.conn_type == 'udp'

    @mock.patch('gevent.socket')
    def test_mocked_eth_socket(self, socket_mock):
        socket_family = getattr(gevent.socket,
                                'AF_PACKET',
                                gevent.socket.AF_INET)
        proto = bsc.ETH_PROTOCOL
        handler = {'name':'name', 'log_dir':'/tmp'}
        bsc.RAW_SOCKET_FD = 'foobar'
        sl = bsc.SocketStreamCapturer([handler], ['eho0', 0], 'ethernet')
        # We need to test a different load if the rawsocket package is used
        if not bsc.RAW_SOCKET_FD:
            socket_mock.socket.assert_called_with(socket_family,
                                                  gevent.socket.SOCK_RAW,
                                                  socket.htons(proto))
        else:
            socket_mock.fromfd.assert_called_with(bsc.RAW_SOCKET_FD,
                                                  socket_family,
                                                  gevent.socket.SOCK_RAW,
                                                  socket.htons(proto))
        assert sl.conn_type == 'ethernet'
        bsc.RAW_SOCKET_FD = None

    @mock.patch('gevent.socket')
    def test_mocked_eth_socket_with_rawsocket(self, socket_mock):
        socket_family = getattr(gevent.socket,
                                'AF_PACKET',
                                gevent.socket.AF_INET)

        rawsocket_is_installed = True if bsc.RAW_SOCKET_FD else False
        if not rawsocket_is_installed:
            rawsocket_fd = 'fake_rawsocket_fd'
            bsc.RAW_SOCKET_FD = rawsocket_fd
        else:
            rawsocket_fd = bsc.RAW_SOCKET_FD

        handler = {'name':'name', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer([handler], ['eho0', 0], 'ethernet')
        # We need to test a different load if the rawsocket package is used
        socket_mock.fromfd.assert_called_with(rawsocket_fd,
                                              socket_family,
                                              gevent.socket.SOCK_RAW,
                                              socket.htons(bsc.ETH_PROTOCOL))
        assert sl.conn_type == 'ethernet'

        if not rawsocket_is_installed:
            bsc.RAW_SOCKET_FD = None

    @mock.patch('ait.core.pcap.PCapStream')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_packet_log(self, socket_mock, pcap_open_mock, pcap_stream_mock):
        socket_mock.return_value = mock.MagicMock()
        pcap_open_mock.return_value = pcap.PCapStream()

        # Verify UDP packet log
        handler = {'name':'name', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer([handler], ['', 9000], 'udp')
        logger = sl.capture_handlers[0]['logger']
        sl.socket.recv.return_value = 'udp_data'
        sl.capture_packet()

        sl.socket.recv.assert_called_with(sl._buffer_size)
        logger.write.assert_called_with('udp_data')

        # Verify Ethernet log
        sl = bsc.SocketStreamCapturer([handler], ['etho0', 0], 'ethernet')
        logger = sl.capture_handlers[0]['logger']
        logger.write.reset_mock()
        sl.socket.recv.return_value = 'eth_data'
        sl.capture_packet()
        logger.write.assert_called_with('eth_data')

    @mock.patch('ait.core.pcap.PCapStream')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_packet_log_mutliple_handlers(self, socket_mock, pcap_open_mock, pcap_stream_mock):
        h1 = {'name':'h1', 'log_dir':'/tmp'}
        h2 = {'name':'h2', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer([h1, h2], ['', 9000], 'udp')

        sl.capture_handlers[0]['logger'] = mock.MagicMock()
        sl.capture_handlers[1]['logger'] = mock.MagicMock()
        logger1 = sl.capture_handlers[0]['logger']
        logger2 = sl.capture_handlers[1]['logger']
        sl.socket.recv.return_value = 'udp_data'
        sl.capture_packet()

        assert logger1.write.call_count == 1
        assert logger2.write.call_count == 1

    @mock.patch('ait.core.pcap.PCapStream')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_capture_with_data_manip(self, socket_mock, pcap_open_mock, pcap_stream_mock):
        transform_mock = mock.Mock(side_effect=['transformed data'])
        handler = {
            'name': 'name',
            'log_dir': '/tmp',
            'pre_write_transforms': [transform_mock]
        }
        sl = bsc.SocketStreamCapturer([handler], ['', 9000], 'udp')
        logger = sl.capture_handlers[0]['logger']
        sl.socket.recv.return_value = 'udp_data'
        sl.capture_packet()

        assert transform_mock.called
        logger.write.assert_called_with('transformed data')

    @mock.patch('gevent.socket.socket')
    def test_logger_conf_dump(self, socket_mock):
        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        addr = ['', 9000]
        conn_type = 'udp'

        sl = bsc.SocketStreamCapturer(handler, addr, conn_type)
        conf_dump = sl.dump_handler_config_data()

        handler = sl.capture_handlers[0]
        expected_log_file_path = sl._get_log_file(handler)

        assert len(conf_dump) == 1
        assert conf_dump[0]['handler']['name'] == 'name'
        assert conf_dump[0]['handler']['log_dir'] == '/tmp'
        assert conf_dump[0]['handler']['rotate_log'] == True
        assert conf_dump[0]['log_file_path'] == expected_log_file_path
        assert conf_dump[0]['conn_type'] == conn_type
        assert conf_dump[0]['address'] == addr

    @mock.patch('gevent.socket.socket')
    def test_handler_stat_dump(self, socket_mock):
        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        addr = ['', 9000]
        conn_type = 'udp'

        sl = bsc.SocketStreamCapturer(handler, addr, conn_type)
        handler = sl.capture_handlers[0]
        new_date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        handler['log_rot_time'] = new_date.timetuple()

        stats = sl.dump_all_handler_stats()

        assert len(stats) == 1
        assert stats[0]['name'] == 'name'
        assert stats[0]['reads'] == 0
        assert stats[0]['data_read_length'] == '0 bytes'
        assert stats[0]['approx_data_rate'] == '0.0 bytes/second'


        handler['reads'] = 2
        handler['data_read'] = 27
        stats = sl.dump_all_handler_stats()

        print stats
        assert len(stats) == 1
        assert stats[0]['name'] == 'name'
        assert stats[0]['reads'] == 2
        assert stats[0]['data_read_length'] == '27 bytes'
        data_rate = float(stats[0]['approx_data_rate'].split(' ')[0])
        assert data_rate != 0.0

    @mock.patch('gevent.socket.socket')
    def test_should_rotate_log(self, socket_mock):
        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')
        h = sl.capture_handlers[0]
        assert sl._should_rotate_log(h) == False

        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')
        h = sl.capture_handlers[0]
        new_date = datetime.datetime.now() - datetime.timedelta(days=1)
        h['log_rot_time'] = new_date.timetuple()
        assert sl._should_rotate_log(h) == True

    @mock.patch('gevent.socket.socket')
    def test_custon_log_rotation(self, socket_mock):
        handler = {
            'name': 'name',
            'log_dir': '/tmp',
            'rotate_log': True,
            'rotate_log_index': 'months',
            'rotate_log_delta': 2
        }

        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')
        h = sl.capture_handlers[0]

        assert sl._should_rotate_log(h) == False

        # Check the default 1 day log rotation case to make sure our config
        # is being used
        new_date = datetime.datetime.now() - datetime.timedelta(days=1)
        h['log_rot_time'] = new_date.timetuple()
        assert sl._should_rotate_log(h) == False

        # Check a working case for our "rotate every 2 months" use case.
        new_date = datetime.datetime.now() - datetime.timedelta(days=62)
        h['log_rot_time'] = new_date.timetuple()
        assert sl._should_rotate_log(h) == True

    @mock.patch('ait.core.pcap.PCapStream')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_log_rotation(self, socket_mock, pcap_open_mock, pcap_stream_mock):
        pcap_open_mock.return_value = pcap.PCapStream()

        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')
        handler = sl.capture_handlers[0]

        log_path = sl._get_log_file(handler)
        pcap_open_mock.assert_called_with(
            log_path,
            mode='a'
        )

        # New name so our open call changes from above. This means we can
        # ensure that the log rotation opens a new logger as expected.
        sl_new_name = 'newname'
        handler['name'] = sl_new_name
        # We expect the rotation to set the last log rotation time. To test
        # we'll set it to None and expect it to be set after
        handler['log_rot_time'] = None

        sl._rotate_log(handler)

        # We expect the log rotation to close the existing logger
        assert pcap_stream_mock.return_value.close.call_count == 1

        # Since we change the name and rotated the log we expect this
        # updated value to be present in the new file name and the call
        # to open the new stream.
        log_path = sl._get_log_file(handler)
        assert sl_new_name in log_path
        pcap_open_mock.assert_called_with(
            log_path,
            mode='a'
        )

        assert pcap_open_mock.call_count == 2

        # We expect the rotation to fix our None assignment on the log_rot_time
        # and we expect it to be replaced by a time struct object.
        assert handler['log_rot_time'] != None
        assert type(handler['log_rot_time']) == type(time.gmtime())

    @mock.patch('gevent.socket.socket')
    def test_time_rotation_index_decoding(self, socket_mock):
        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')

        # We expect an error when we input a bad time index value
        nose.tools.assert_raises(
            ValueError,
            sl._decode_time_rotation_index,
            'this is not a valid value'
        )

        assert 2 == sl._decode_time_rotation_index('tm_mday')

    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_get_log_file(self, socket_mock, pcap_open_mock):
        h = {
            'name':'name',
            'log_dir': '/tmp',
            'path':'foobarbaz/%j/',
            'file_name_pattern': 'extrafolder/%j/%Y-%m-%d-%H-%M-randomUDPtestData-{name}.pcap'
        }
        sl = bsc.SocketStreamCapturer(h, ['', 9000], 'udp')
        handler = sl.capture_handlers[0]

        # Check log path generation with user specified handler-specific path
        # and file_name_pattern. This includes strftime substitution and handler
        # metadata substitution.
        log_path = sl._get_log_file(handler)
        expected_path = os.path.join(h['log_dir'], h['path'], h['file_name_pattern'])
        expected_path = time.strftime(expected_path, time.gmtime())
        expected_path = expected_path.format(**handler)
        assert log_path == expected_path

        h = {'name':'name', 'log_dir': '/tmp'}
        sl = bsc.SocketStreamCapturer(h, ['', 9000], 'udp')
        handler = sl.capture_handlers[0]

    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_get_logger(self, socket_mock, pcap_open_mock):
        handler = {'name':'name', 'log_dir':'/tmp', 'rotate_log':True}
        sl = bsc.SocketStreamCapturer(handler, ['', 9000], 'udp')
        # We expect _get_logger to generate the file path for the PCapStream
        # and call the ait.core.pcap.open static function to generate the
        # stream.
        handler = sl.capture_handlers[0]
        log_path = sl._get_log_file(handler)
        pcap_open_mock.assert_called_with(log_path, mode='a')

    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_add_handler(self, socket_mock, pcap_open_mock):
        h1 = {'name':'h1', 'log_dir':'/tmp'}
        h2 = {'name':'h2', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer(h1, ['', 9000], 'udp')

        assert len(sl.capture_handlers) == 1
        sl.add_handler(h2)
        assert len(sl.capture_handlers) == 2
        assert pcap_open_mock.call_count == 2

    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_remove_handler(self, socket_mock, pcap_open_mock):
        h1 = {'name':'h1', 'log_dir':'/tmp'}
        h2 = {'name':'h2', 'log_dir':'/tmp'}
        sl = bsc.SocketStreamCapturer([h1, h2], ['', 9000], 'udp')

        assert len(sl.capture_handlers) == 2
        sl.remove_handler('h2')
        assert len(sl.capture_handlers) == 1
        assert sl.capture_handlers[0]['name'] == 'h1'

class TestStreamCaptureManager(object):
    @mock.patch('ait.core.bsc.SocketStreamCapturer')
    def test_log_manager_init(self, socket_log_mock):
        loggers = [
            ('foo', ['', 9000], 'udp', '/tmp', {'rotate_log': True}),
            ('bar', ['', 8125], 'udp', '/tmp', {}),
        ]
        fake_mngr_conf = 'mngr_conf'
        lm = bsc.StreamCaptureManager(fake_mngr_conf, loggers)

        assert lm._mngr_conf == fake_mngr_conf
        assert len(lm._stream_capturers.keys()) == 2
        assert "['', 9000]" in lm._stream_capturers.keys()
        assert "['', 8125]" in lm._stream_capturers.keys()

    @mock.patch('os.makedirs')
    @mock.patch('ait.core.bsc.SocketStreamCapturer')
    def test_add_logger(self, socket_log_mock, mkdirs_mock):
        mngr_conf = {'root_log_directory': '/totally/a/../fake/dir/../name'}
        # We'll use this to make sure directory paths are cleaned
        cleaned_dir_path = os.path.normpath(mngr_conf['root_log_directory'])

        lm = bsc.StreamCaptureManager(mngr_conf, [])
        lm.add_logger('foo', ['', 9000], 'udp', '/tmp')

        assert len(lm._stream_capturers.keys()) == 1
        assert "['', 9000]" in lm._stream_capturers

        # Default root_log_directory usage and normalization check
        lm.add_logger('baz', ['', 8500], 'udp')
        socket_log_mock.assert_called_with(
            {
                'log_dir': cleaned_dir_path,
                'name': 'baz',
                'rotate_log': True,
                'pre_write_transforms': [],
            }, ['', 8500], 'udp'
        )
        assert lm._pool.free_count() == 48

        # Check to make sure that home directory expansion is being done
        socket_log_mock.reset_mock()
        lm.add_logger('testlog', ['', 1234], 'udp', '~/logger_dir')
        expanded_user_path = os.path.expanduser('~/logger_dir')
        socket_log_mock.assert_called_with(
            {
                'log_dir': expanded_user_path,
                'name': 'testlog',
                'rotate_log': True,
                'pre_write_transforms': [],
            }, ['', 1234], 'udp'
        )

    @mock.patch('ait.core.pcap.open')
    @mock.patch('os.makedirs')
    @mock.patch('gevent.socket.socket')
    def test_pre_write_transform_load(self, socket_mock, mkdirs_mock, pcap_open_mock):
        mngr_conf = {'root_log_directory': '/tmp'}
        lm = bsc.StreamCaptureManager(mngr_conf, [])

        kwargs = {
            'pre_write_transforms': [
                'identity_transform',
                lambda x: 1
            ]
        }
        lm.add_logger('testlog', ['', 9876], 'udp', '~/logger_dir', **kwargs)
        stream_capturer = lm._stream_capturers["['', 9876]"][0]
        handler = stream_capturer.capture_handlers[0]

        assert 'pre_write_transforms' in handler
        assert len(handler['pre_write_transforms']) == 2

        for t in handler['pre_write_transforms']:
            assert hasattr(t, '__call__')

        assert 'identity_transform' == handler['pre_write_transforms'][0].__name__
        assert 1 == handler['pre_write_transforms'][1]('bogus input')

    @mock.patch('ait.core.log.warn')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('os.makedirs')
    @mock.patch('gevent.socket.socket')
    def test_bad_builtin_transform_load(self, socket_mock, mkdirs_mock, open_mock, log_mock):
        logging.getLogger('ait').setLevel(logging.INFO)

        mngr_conf = {'root_log_directory': '/tmp'}
        lm = bsc.StreamCaptureManager(mngr_conf, [])

        bad_func_name = 'this function name doesnt exist'
        kwargs = {
            'pre_write_transforms': [
                bad_func_name
            ]
        }
        lm.add_logger('testlog', ['', 9876], 'udp', '~/logger_dir', **kwargs)
        msg = 'Unable to load data transformation "{}" for handler "{}"'.format(
            bad_func_name,
            'testlog'
        )
        log_mock.assert_called_with(msg)

        logging.getLogger('ait').setLevel(logging.CRITICAL)

    @mock.patch('ait.core.log.warn')
    @mock.patch('ait.core.pcap.open')
    @mock.patch('os.makedirs')
    @mock.patch('gevent.socket.socket')
    def test_bad_type_transform_load(self, socket_mock, mkdirs_mock, open_mock, log_mock):
        logging.getLogger('ait').setLevel(logging.INFO)

        mngr_conf = {'root_log_directory': '/tmp'}
        lm = bsc.StreamCaptureManager(mngr_conf, [])

        bad_func_name = ('foobarbaz',)
        kwargs = {
            'pre_write_transforms': [
                bad_func_name
            ]
        }
        lm.add_logger('testlog', ['', 9876], 'udp', '~/logger_dir', **kwargs)
        msg = 'Unable to determine how to load data transform "{}"'.format(bad_func_name)
        log_mock.assert_called_with(msg)

        logging.getLogger('ait').setLevel(logging.CRITICAL)

    @mock.patch('ait.core.bsc.SocketStreamCapturer')
    def test_remove_logger(self, socket_log_mock):
        lm = bsc.StreamCaptureManager(None, [])
        lm.add_logger('foo', ['', 9000], 'udp', '/tmp')

        lm.stop_capture_handler('foo')
        assert mock.call().remove_handler('foo') in socket_log_mock.mock_calls

    @mock.patch('ait.core.bsc.SocketStreamCapturer')
    def test_get_logger_data(self, socket_log_mock):
        lm = bsc.StreamCaptureManager(None, [])
        with mock.patch('os.mkdir') as mkdir_mock:
            lm.add_logger('foo', ['', 9000], 'udp', '/tmp')
            lm.add_logger('bar', ['', 8500], 'udp', '/tmp')

        logger_data = lm.get_logger_data()
        # Note we're not going to test content of the returned data because
        # that is handled by SocketStreamCapturer. There is an appropriate test
        # for that in the SocketStreamCapturer section.
        assert len(logger_data.keys()) == 2
        assert "['', 8500]" in logger_data.keys()
        assert "['', 9000]" in logger_data.keys()

    @mock.patch('ait.core.bsc.SocketStreamCapturer')
    def test_get_logger_stats(self, socket_log_mock):
        lm = bsc.StreamCaptureManager(None, [])
        with mock.patch('os.mkdir') as mkdir_mock:
            lm.add_logger('foo', ['', 9000], 'udp', '/tmp')
            lm.add_logger('bar', ['', 8500], 'udp', '/tmp')

        logger_data = lm.get_handler_stats()
        # Note we're not going to test content of the returned data because
        # that is handled by SocketStreamCapturer. There is an appropriate test
        # for that in the SocketStreamCapturer section.
        assert len(logger_data.keys()) == 2
        assert "['', 8500]" in logger_data.keys()
        assert "['', 9000]" in logger_data.keys()

    @mock.patch('ait.core.pcap.open')
    @mock.patch('gevent.socket.socket')
    def test_forced_log_rotation(self, socket_mock, pcap_open_mock):
        ''''''
        lm = bsc.StreamCaptureManager(None, [])
        with mock.patch('os.mkdir') as mkdir_mock:
            lm.add_logger('foo', ['', 9000], 'udp', '/tmp')
            lm.add_logger('bar', ['', 8500], 'udp', '/tmp')

        bar = lm._stream_capturers["['', 8500]"][0]

        pre_rot_count = pcap_open_mock.call_count
        lm.rotate_capture_handler_log('bar')
        post_rot_count = pcap_open_mock.call_count
        assert post_rot_count - pre_rot_count == 1
