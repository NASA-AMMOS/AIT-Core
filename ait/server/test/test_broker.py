from ait.server.broker import AitBroker
import ait
from ait.core import cfg, log
from ait.server.stream import Stream
import nose
from nose.tools import *
import mock


@mock.patch.object(ait.core.log, 'warn')
@mock.patch.object(ait.server.broker.AitBroker, 'create_stream')
@mock.patch.object(ait.server.broker.AitBroker, 'load_plugins')
@mock.patch.object(ait.server.broker.AitBroker, 'subscribe_all')
@mock.patch.object(ait.server.broker.AitBroker, 'start_broker')
class TestStreamConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def setUp(self):
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [ ]

    def test_no_inbound_streams(self,
                                start_broker_mock,
                                subscribe_mock,
                                plugin_load_mock,
                                create_stream_mock,
                                log_warn_mock):
        """ Tests that broker started with no inbound streams specified
        and that warning is logged """
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
        ait.broker.__init__()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid inbound telemetry stream configurations found. '
            'No telemetry will be received (or displayed).')
        # assert outbound stream is added successfully
        assert len(ait.broker.outbound_streams) == 1
        # assert initiailization continues
        subscribe_mock.assert_called()
        start_broker_mock.assert_called()

    def test_no_outbound_streams(self,
                                 start_broker_mock,
                                 subscribe_mock,
                                 plugin_load_mock,
                                 create_stream_mock,
                                 log_warn_mock):
        """ Tests that broker started with no outbound streams specified
        and that warning is logged """
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
        ait.broker.__init__()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid outbound telemetry stream configurations found. '
            'No telemetry will be published.')
        # assert inbound stream is added successfully
        assert len(ait.broker.inbound_streams) == 1
        # assert broker initialization continues
        subscribe_mock.assert_called()
        start_broker_mock.assert_called()


class TestStreamCreation(object):

    def test_no_stream_type(self):
        """ Tests that a ValueError is raised when creating a stream with
        stream_type of None """
        with assert_raises_regexp(ValueError,
                                  'Stream type must be \'inbound\' or \'outbound\'.'):
            ait.broker.create_stream('some_config', 'some_path', None)

    def test_bad_stream_type(self):
        """ Tests that a ValueError is raised when creating a stream with
        a stream_type not equal to either 'inbound' or 'outboud' """
        with assert_raises_regexp(ValueError,
                                  'Stream type must be \'inbound\' or \'outbound\'.'):
            ait.broker.create_stream('some_config', 'some_path', 'some_type')

    def test_no_stream_config(self):
        """ Tests that a ValueError is raised when creating a stream with
        a config of None """
        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path'):
            ait.broker.create_stream(None, 'some_path', 'inbound')

    def test_no_stream_name(self):
        """ Tests that a ValueError is raised when creating a stream with
        no name specified in the config """
        config = cfg.AitConfig(config={'input': 'some_stream',
                                       'handlers': ['some-handler']})

        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path.name'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    def test_duplicate_stream_name(self):
        """ Tests that a ValueError is raised when creating a stream with
        a name that already belongs to another stream or plugin """
        config = cfg.AitConfig(config={'input': 'some_stream',
                                       'name': 'myname',
                                       'handlers': ['some-handler']})

        # Testing existing name in plugins
        ait.broker.plugins = [FakePluginOrStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'outbound')

        # Testing existing name in inbound_streams
        ait.broker.plugins = [ ]
        ait.broker.inbound_streams = [FakePluginOrStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

        # Testing existing name in outbound_streams
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [FakePluginOrStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    def test_no_stream_input(self):
        """ Tests that a ValueError is raised when creating a stream with
        no input specified in the config """
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'handlers': ['some-handler']})

        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path.input'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    @mock.patch.object(ait.server.broker.AitBroker, 'create_handler')
    def test_successful_stream_creation(self, create_handler_mock):
        """ Tests that streams are successfully created both with or without
        handlers """
        # Testing stream creating with handlers
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'input': 'some_input',
                                       'handlers': ['some-handler']})
        created_stream = ait.broker.create_stream(config, 'some_path', 'inbound')
        assert type(created_stream) == Stream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list
        assert len(created_stream.handlers) == 1

        # Testing stream creation without handlers
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'input': 'some_input'})
        created_stream = ait.broker.create_stream(config, 'some_path', 'inbound')
        assert type(created_stream) == Stream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list
        assert len(created_stream.handlers) == 0


class FakePluginOrStream(object):

    def __init__(self, name, input_=None, handlers=None,
                 zmq_context=None, broker_xpub=None, broker_xsub=None):
        self.name = name
