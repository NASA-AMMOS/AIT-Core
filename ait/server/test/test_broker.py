from ait.server.broker import AitBroker
import ait
from ait.core import cfg, log
import nose
from nose.tools import *
import mock


class TestStreamConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def setUp(self):
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [ ]

    @mock.patch.object(ait.core.log, 'warn')
    @mock.patch.object(ait.server.broker.AitBroker, 'create_stream')
    @mock.patch.object(ait.server.broker.AitBroker, 'subscribe_streams')
    def test_no_inbound_streams(self, subscribe_stream_mock, create_stream_mock, log_warn_mock):
        """ Tests that broker started anyways and that warning is logged """
        yaml = """
                default:
                    server:
                        inbound-streams:

                        outbound-streams:
                            - stream:
                                name: sle_data_stream_parallel
                                input: sle_data_stream_ccsds
                                handlers:
                                    - a_handler
               """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml)

        ait.config.reload(filename=self.test_yaml_file)
        ait.broker.load_streams()

        assert log_warn_mock.assert_called_with(
            'No valid inbound telemetry stream configurations found. '
            'No telemetry will be received (or displayed).')
        assert len(ait.broker.outbound_streams) == 1

    @mock.patch.object(ait.core.log, 'warn')
    @mock.patch.object(ait.server.broker.AitBroker, 'create_stream')
    @mock.patch.object(ait.server.broker.AitBroker, 'subscribe_streams')
    def test_no_outbound_streams(self, subscribe_stream_mock, create_stream_mock, log_warn_mock):
        """ Tests that broker started anyways and that warning is logged """
        yaml = """
                default:
                    server:
                        inbound-streams:
                            - stream:
                                name: sle_data_stream_parallel
                                input: sle_data_stream_ccsds
                                handlers:
                                    - a_handler

                        outbound-streams:
               """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml)

        ait.config.reload(filename=self.test_yaml_file)
        ait.broker.load_streams()

        assert log_warn_mock.assert_called_with(
            'No valid outbound telemetry stream configurations found. '
            'No telemetry will be published.')
        assert len(broker.inbound_streams) == 1


class TestStreamCreation(object):

    @raises(ValueError)
    def test_no_stream_type(self):
        """ Tests that a ValueError is raised when creating a stream with
        stream_type of None """
        ait.broker.create_stream('some_config', 'some_path', None)

    @raises(ValueError)
    def test_no_stream_config(self):
        """ Tests that a ValueError is raised when creating a stream with
        a config of None """
        ait.broker.create_stream(None, 'some_path', 'inbound')

    def test_no_stream_name(self):
        return

    def test_duplicate_stream_name(self):
        return

    def test_no_stream_input(self):
        return

    @mock.patch('ait.server.broker.AitBroker.create_handler')
    @mock.patch('ait.server.stream.Stream')
    def test_successful_stream_creation(self, stream_mock, create_handler_mock):
        pass
