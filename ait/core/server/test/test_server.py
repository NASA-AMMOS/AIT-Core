import os
import os.path

import nose
from nose.tools import *
from unittest import mock

import ait.core
import ait.core.server
from ait.core import cfg
from ait.core.server.handlers import *
from ait.core.server.server import Server

@mock.patch.object(ait.core.log, 'warn')
@mock.patch('ait.core.server.broker.Broker')
@mock.patch.object(ait.core.server.server.Server, '__init__', return_value=None)
@mock.patch.object(ait.core.server.server.Server, '_create_outbound_stream')
@mock.patch.object(ait.core.server.server.Server, '_create_inbound_stream')
class TestStreamConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def tearDown(self):
        ait.config = cfg.AitConfig()

        if os.path.exists(self.test_yaml_file):
            os.remove(self.test_yaml_file)

    def test_no_inbound_streams(self,
                                create_inbound_stream_mock,
                                create_outbound_stream_mock,
                                server_init_mock,
                                broker_class_mock,
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
                                input: 
                                    - sle_data_stream_ccsds
                                handlers:
                                    - a_handler
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server = Server()
        server._load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid inbound stream configurations found. '
            'No data will be received (or displayed).')
        # assert outbound stream is added successfully
        assert len(server.outbound_streams) == 1

    def test_no_outbound_streams(self,
                                 create_inbound_stream_mock,
                                 create_outbound_stream_mock,
                                 server_init_mock,
                                 broker_class_mock,
                                 log_warn_mock):
        """ Tests that broker started with no outbound streams specified
        and that warning is logged """
        yaml = """
                default:
                    server:
                        inbound-streams:
                            - stream:
                                name: sle_data_stream_parallel
                                input: 
                                    - sle_data_stream_ccsds
                                handlers:
                                    - a_handler

                        outbound-streams:
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server = Server()
        server._load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid outbound stream configurations found. '
            'No data will be published.')
        # assert inbound stream is added successfully
        assert len(server.inbound_streams) == 1


@mock.patch('ait.core.server.broker.Broker')
@mock.patch.object(ait.core.server.server.Server, '__init__', return_value=None)
class TestStreamCreation(object):

    def test_no_stream_config(self,
                                      server_init_mock,
                                      broker_class_mock):
        """ Tests that a ValueError is raised when creating streams
        with a config of None """
        server = Server()
        with assert_raises_regexp(ValueError,
                                  'No stream config to create stream from.'):
            server._create_inbound_stream(None)

        with assert_raises_regexp(ValueError,
                                  'No stream config to create stream from.'):
            server._create_outbound_stream(None)

    def test_no_stream_name(self,
                            server_init_mock,
                            broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream
        with no name specified in the config """
        config = {'input': 'some_stream',
                  'handlers': [{'name': 'some-handler'}]}
        server = Server()
        with assert_raises_regexp(cfg.AitConfigMissing,
                                  'The parameter %s is missing from config.yaml'
                                  % 'stream name'):
            server._get_stream_name(config)

    def test_duplicate_stream_name(self,
                                   server_init_mock,
                                   broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        a name that already belongs to another stream or plugin """
        server = Server()

        config = {'input': ['some_stream'],
                  'name': 'myname',
                  'handlers': [{'name': 'some-handler'}]}

        # Testing existing name in plugins
        server.plugins = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError,
                                  ('Duplicate stream name "{}" encountered.'
                                   ' Stream names must be unique.').format('myname')):
            server._get_stream_name(config)

        # Testing existing name in inbound_streams
        server.plugins = [ ]
        server.inbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError,
                                  ('Duplicate stream name "{}" encountered.'
                                   ' Stream names must be unique.').format('myname')):
            server._get_stream_name(config)

        # Testing existing name in outbound_streams
        server.inbound_streams = [ ]
        server.outbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError,
                                  ('Duplicate stream name "{}" encountered.'
                                   ' Stream names must be unique.').format('myname')):
            server._get_stream_name(config)

    @mock.patch.object(ait.core.server.server.Server, '_create_handler')
    def test_no_inbound_stream_input(self,
                                     create_handler_mock,
                                     server_init_mock,
                                     broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        no input specified in the config """
        server = Server()

        config = {'name': 'some_stream',
                  'handlers': [{'name': 'some-handler'}]}

        with assert_raises_regexp(cfg.AitConfigMissing,
                                  'The parameter {} is missing from config.yaml'
                                  .format('inbound stream {}\'s input'.format('some_stream'))):
            server._create_inbound_stream(config)

    @mock.patch.object(ait.core.server.server.Server, '_create_handler')
    def test_successful_inbound_stream_creation(self,
                                                create_handler_mock,
                                                server_init_mock,
                                                broker_class_mock):
        """ Tests that all types of inbound streams are successfully created """
        # Testing creation of inbound stream with ZMQ input/output
        server = Server()
        server.broker = ait.core.server.broker.Broker()

        config = {'name': 'some_stream',
                  'input': ['some_input'],
                  'handlers': [{'name': 'some-handler'}]}
        created_stream = server._create_inbound_stream(config)
        assert type(created_stream) == ait.core.server.stream.ZMQStream
        assert created_stream.name == 'some_stream'
        assert created_stream.inputs == ['some_input']
        assert type(created_stream.handlers) == list

        # Testing creation of inbound stream with port input
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'input': [3333]})
        created_stream = server._create_inbound_stream(config)
        assert type(created_stream) == ait.core.server.stream.PortInputStream
        assert created_stream.name == 'some_stream'
        assert created_stream.inputs == [3333]
        assert created_stream.handlers == [ ]

    @mock.patch.object(ait.core.server.server.Server, '_create_handler')
    def test_successful_outbound_stream_creation(self,
                                                 create_handler_mock,
                                                 server_init_mock,
                                                 broker_class_mock):
        """ Tests that all types of outbound streams are successfully created """
        # Testing creation of outbound stream with ZMQ input/output
        server = Server()
        server.broker = ait.core.server.broker.Broker()

        config = {'name': 'some_stream',
                  'handlers': [{'name': 'some-handler'}]}
        created_stream = server._create_outbound_stream(config)
        assert type(created_stream) == ait.core.server.stream.ZMQStream
        assert created_stream.name == 'some_stream'
        assert type(created_stream.handlers) == list

        # Testing creation of outbound stream with port output
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'output': 3333})
        created_stream = server._create_outbound_stream(config)
        assert type(created_stream) == ait.core.server.stream.PortOutputStream
        assert created_stream.name == 'some_stream'
        assert created_stream.out_port == 3333
        assert created_stream.handlers == [ ]


@mock.patch('ait.core.server.broker.Broker')
@mock.patch.object(ait.core.server.server.Server, '__init__', return_value=None)
class TestHandlerCreation(object):

    def test_no_handler_config(self,
                               server_init_mock,
                               broker_mock):
        """ Tests that a ValueError is raised when creating a handler with
        a config of None """
        server = Server()
        with assert_raises_regexp(ValueError,
                                  'No handler config to create handler from.'):
            server._create_handler(None)

    def test_handler_creation_with_no_configs(self,
                                              server_init_mock,
                                              broker_mock):
        """ Tests handler is successfully created when it has no configs """
        server = Server()

        config = {'name': 'ait.core.server.handlers.PacketHandler',
                  'packet': 'CCSDS_HEADER'}
        handler = server._create_handler(config)
        assert type(handler) == ait.core.server.handlers.PacketHandler
        assert handler.input_type is None
        assert handler.output_type is None

    def test_handler_creation_with_configs(self,
                                           server_init_mock,
                                           broker_mock):
        """ Tests handler is successfully created when it has configs """
        server = Server()

        # config = {'name': 'ait.core.server.handlers.example_handler', 'input_type': 'int', 'output_type': 'int'}
        config = {'name': 'ait.core.server.handlers.PacketHandler',
                  'input_type': 'int',
                  'output_type': 'int',
                  'packet': 'CCSDS_HEADER'}
        handler = server._create_handler(config)
        assert type(handler) == ait.core.server.handlers.PacketHandler
        assert handler.input_type == 'int'
        assert handler.output_type == 'int'

    def test_handler_that_doesnt_exist(self,
                                       server_init_mock,
                                       broker_mock):
        """ Tests that exception thrown if handler doesn't exist """
        server = Server()

        config = {'name': 'some_nonexistant_handler'}
        with assert_raises_regexp(ImportError, "No module named '{}'".format(config['name'])):
            server._create_handler(config)


@mock.patch.object(ait.core.log, 'warn')
@mock.patch.object(ait.core.log, 'error')
@mock.patch('ait.core.server.broker.Broker')
@mock.patch.object(ait.core.server.server.Server, '__init__', return_value=None)
class TestPluginConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def tearDown(self):
        ait.config = cfg.AitConfig()

        if os.path.exists(self.test_yaml_file):
            os.remove(self.test_yaml_file)

    def test_no_plugins_listed(self,
                               server_init_mock,
                               broker_mock,
                               log_error_mock,
                               log_warn_mock):
        """ Tests that warning logged if no plugins configured """
        server = Server()

        yaml = """
                default:
                    server:
                        plugins:
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server._load_plugins()

        log_warn_mock.assert_called_with(
            'No plugins specified in config.')


@mock.patch('ait.core.server.broker.Broker')
@mock.patch.object(ait.core.server.server.Server, '__init__', return_value=None)
class TestPluginCreation(object):

    def test_plugin_with_no_config(self,
                                   server_init_mock,
                                   broker_mock):
        """ Tests that error raised if plugin not configured """
        server = Server()

        config = None
        with assert_raises_regexp(ValueError,
                                  'No plugin config to create plugin from.'):
            server._create_plugin(config)

    def test_plugin_missing_name(self,
                                 server_init_mock,
                                 broker_mock):
        """ Tests that error raised if plugin has no name """
        server = Server()

        config = {'inputs': 'some_inputs'}
        with assert_raises_regexp(cfg.AitConfigMissing,
                                  'The parameter plugin name is missing from config.yaml'):
            server._create_plugin(config)

    @mock.patch.object(ait.core.log, 'warn')
    def test_plugin_missing_inputs(self,
                                   log_warn_mock,
                                   server_init_mock,
                                   broker_mock):
        """ Tests that warning logged if plugin has no inputs and
        plugin created anyways """
        server = Server()
        server.broker = ait.core.server.broker.Broker()

        config = {'name': 'ait.core.server.plugins.TelemetryLimitMonitor',
                  'outputs': 'some_stream'}
        server._create_plugin(config)

        log_warn_mock.assert_called_with('No plugin inputs specified for ait.core.server.plugins.TelemetryLimitMonitor')

    @mock.patch.object(ait.core.log, 'warn')
    def test_plugin_missing_outputs(self,
                                    log_warn_mock,
                                    server_init_mock,
                                    broker_mock):
        """ Tests that warning logged if plugin has no inputs and
        plugin created anyways """
        server = Server()
        server.broker = ait.core.server.broker.Broker()

        config = {'name': 'ait.core.server.plugins.TelemetryLimitMonitor',
                  'inputs': 'some_stream'}
        server._create_plugin(config)

        log_warn_mock.assert_called_with('No plugin outputs specified for ait.core.server.plugins.TelemetryLimitMonitor')

    def test_plugin_name_already_in_use(self,
                                        server_init_mock,
                                        broker_mock):
        """ Tests that error raised if name already in use """
        server = Server()

        server.plugins = [FakeStream(name='Plugin')]
        config = {'name': 'Plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ValueError,
                                  'Plugin "Plugin" already loaded. Only one plugin of a given name is allowed'):
            server._create_plugin(config)

    def test_plugin_doesnt_exist(self,
                                 server_init_mock,
                                 broker_mock):
        """ Tests that error raised if plugin doesn't exist """
        server = Server()

        config = {'name': 'some_nonexistant_plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ImportError,
                                  "No module named 'some_nonexistant_plugin'"):
            server._create_plugin(config)


def rewrite_and_reload_config(filename, yaml):
    with open(filename, 'wt') as out:
        out.write(yaml)

    ait.config.reload(filename=filename)


class FakeStream(object):

    def __init__(self, name, input_=None, handlers=None, zmq_args=None):
        self.name = name
