import ait
from ait.core import cfg
import ait.server
from ait.server.handlers import *
from ait.server.server import AITServer
import nose
from nose.tools import *
import mock


@mock.patch.object(ait.core.log, 'warn')
@mock.patch('ait.server.broker.AITBroker')
@mock.patch.object(ait.server.server.AITServer, '__init__', return_value=None)
@mock.patch.object(ait.server.server.AITServer, '_create_stream')
class TestStreamConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def test_no_inbound_streams(self,
                                create_stream_mock,
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
                                input: sle_data_stream_ccsds
                                handlers:
                                    - a_handler
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server = AITServer()
        server._load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid inbound telemetry stream configurations found. '
            'No telemetry will be received (or displayed).')
        # assert outbound stream is added successfully
        assert len(server.outbound_streams) == 1

    def test_no_outbound_streams(self,
                                 create_stream_mock,
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
                                input: sle_data_stream_ccsds
                                handlers:
                                    - a_handler

                        outbound-streams:
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server = AITServer()
        server._load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid outbound telemetry stream configurations found. '
            'No telemetry will be published.')
        # assert inbound stream is added successfully
        assert len(server.inbound_streams) == 1


@mock.patch('ait.server.broker.AITBroker')
@mock.patch.object(ait.server.server.AITServer, '__init__', return_value=None)
class TestStreamCreation(object):

    def test_no_stream_type(self,
                            server_init_mock,
                            broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        stream_type of None """
        server = AITServer()
        with assert_raises_regexp(ValueError,
                                  'Stream type must be \'inbound\' or \'outbound\'.'):
            server._create_stream('some_config', None)

    def test_bad_stream_type(self,
                             server_init_mock,
                             broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        a stream_type not equal to either 'inbound' or 'outboud' """
        server = AITServer()
        with assert_raises_regexp(ValueError,
                                  'Stream type must be \'inbound\' or \'outbound\'.'):
            server._create_stream('some_config', 'some_type')

    def test_no_stream_config(self,
                              server_init_mock,
                              broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        a config of None """
        server = AITServer()
        with assert_raises_regexp(ValueError,
                                  'No stream config to create stream from.'):
            server._create_stream(None, 'inbound')

    def test_no_stream_name(self,
                            server_init_mock,
                            broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        no name specified in the config """
        config = {'input': 'some_stream',
                  'handlers': ['some-handler']}
        server = AITServer()
        with assert_raises_regexp(cfg.AitConfigMissing,
                                  'The parameter %s is missing from config.yaml'
                                  % 'inbound stream name'):
            server._create_stream(config, 'inbound')

    def test_duplicate_stream_name(self,
                                   server_init_mock,
                                   broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        a name that already belongs to another stream or plugin """
        server = AITServer()

        config = {'input': 'some_stream',
                  'name': 'myname',
                  'handlers': ['some-handler']}

        # Testing existing name in plugins
        server.plugins = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            server._create_stream(config, 'outbound')

        # Testing existing name in inbound_streams
        server.plugins = [ ]
        server.inbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            server._create_stream(config, 'inbound')

        # Testing existing name in outbound_streams
        server.inbound_streams = [ ]
        server.outbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            server._create_stream(config, 'inbound')

    def test_no_stream_input(self,
                             server_init_mock,
                             broker_class_mock):
        """ Tests that a ValueError is raised when creating a stream with
        no input specified in the config """
        server = AITServer()

        config = {'name': 'some_stream',
                  'handlers': ['some-handler']}

        with assert_raises_regexp(cfg.AitConfigMissing,
                                  'The parameter %s is missing from config.yaml'
                                  % 'inbound stream input'):
            server._create_stream(config, 'inbound')

    @mock.patch.object(ait.server.server.AITServer, '_create_handler')
    def test_successful_stream_creation(self,
                                        create_handler_mock,
                                        server_init_mock,
                                        broker_class_mock):
        """ Tests that streams are successfully created both with or without
        handlers """
        # Testing stream creating with handlers
        server = AITServer()
        server.broker = ait.server.broker.AITBroker()

        config = {'name': 'some_stream',
                  'input': 'some_input',
                  'handlers': ['some-handler']}
        created_stream = server._create_stream(config, 'inbound')
        assert type(created_stream) == ait.server.stream.ZMQInputStream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list

        # Testing stream creation without handlers
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'input': 'some_input'})
        created_stream = server._create_stream(config, 'inbound')
        assert type(created_stream) == ait.server.stream.ZMQInputStream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list


@mock.patch('ait.server.broker.AITBroker')
@mock.patch.object(ait.server.server.AITServer, '__init__', return_value=None)
class TestHandlerCreation(object):

    def test_no_handler_config(self,
                               server_init_mock,
                               broker_mock):
        """ Tests that a ValueError is raised when creating a handler with
        a config of None """
        server = AITServer()
        with assert_raises_regexp(ValueError,
                                  'No handler config to create handler from.'):
            server._create_handler(None)

    def test_handler_creation_with_no_configs(self,
                                              server_init_mock,
                                              broker_mock):
        """ Tests handler is successfully created when it has no configs """
        server = AITServer()

        config = {'name': 'ait.server.handlers.example_handler'}
        handler = server._create_handler(config)
        assert type(handler) == ait.server.handlers.example_handler.ExampleHandler
        assert handler.input_type is None
        assert handler.output_type is None

    def test_handler_creation_with_configs(self,
                                           server_init_mock,
                                           broker_mock):
        """ Tests handler is successfully created when it has configs """
        server = AITServer()

        config = {'name': 'ait.server.handlers.example_handler', 'input_type': 'int', 'output_type': 'int'}
        handler = server._create_handler(config)
        assert type(handler) == ait.server.handlers.example_handler.ExampleHandler
        assert handler.input_type == 'int'
        assert handler.output_type == 'int'

    def test_handler_that_doesnt_exist(self,
                                       server_init_mock,
                                       broker_mock):
        """ Tests that exception thrown if handler doesn't exist """
        server = AITServer()

        config = {'name': 'some_nonexistant_handler'}
        with assert_raises_regexp(ImportError, 'No module named %s' % config['name']):
            server._create_handler(config)


@mock.patch.object(ait.core.log, 'warn')
@mock.patch.object(ait.core.log, 'error')
@mock.patch('ait.server.broker.AITBroker')
@mock.patch.object(ait.server.server.AITServer, '__init__', return_value=None)
class TestPluginConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def test_no_plugins_listed(self,
                               server_init_mock,
                               broker_mock,
                               log_error_mock,
                               log_warn_mock):
        """ Tests that warning logged if no plugins configured """
        server = AITServer()

        yaml = """
                default:
                    server:
                        plugins:
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        server._load_plugins()

        log_warn_mock.assert_called_with(
            'No plugins specified in config.')


@mock.patch('ait.server.broker.AITBroker')
@mock.patch.object(ait.server.server.AITServer, '__init__', return_value=None)
class TestPluginCreation(object):

    def test_plugin_with_no_config(self,
                                   server_init_mock,
                                   broker_mock):
        """ Tests that error raised if plugin not configured """
        server = AITServer()

        config = None
        with assert_raises_regexp(ValueError,
                                  'No plugin config to create plugin from.'):
            server._create_plugin(config)

    def test_plugin_missing_name(self,
                                 server_init_mock,
                                 broker_mock):
        """ Tests that error raised if plugin has no name """
        server = AITServer()

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
        server = AITServer()
        server.broker = ait.server.broker.AITBroker()

        config = {'name': 'ait.server.plugins.example_plugin',
                  'outputs': 'some_stream'}
        server._create_plugin(config)

        log_warn_mock.assert_called_with('No plugin inputs specified for ait.server.plugins.example_plugin')

    @mock.patch.object(ait.core.log, 'warn')
    def test_plugin_missing_outputs(self,
                                    log_warn_mock,
                                    server_init_mock,
                                    broker_mock):
        """ Tests that warning logged if plugin has no inputs and
        plugin created anyways """
        server = AITServer()
        server.broker = ait.server.broker.AITBroker()

        config = {'name': 'ait.server.plugins.example_plugin',
                  'inputs': 'some_stream'}
        server._create_plugin(config)

        log_warn_mock.assert_called_with('No plugin outputs specified for ait.server.plugins.example_plugin')

    def test_plugin_name_already_in_use(self,
                                        server_init_mock,
                                        broker_mock):
        """ Tests that error raised if name already in use """
        server = AITServer()

        server.plugins = [FakeStream(name='ExamplePlugin')]
        config = {'name': 'example_plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ValueError,
                                  'Plugin name already exists. Please rename.'):
            server._create_plugin(config)

    def test_plugin_doesnt_exist(self,
                                 server_init_mock,
                                 broker_mock):
        """ Tests that error raised if plugin doesn't exist """
        server = AITServer()

        config = {'name': 'some_nonexistant_plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ImportError,
                                  'No module named some_nonexistant_plugin'):
            server._create_plugin(config)


def rewrite_and_reload_config(filename, yaml):
    with open(filename, 'wb') as out:
        out.write(yaml)

    ait.config.reload(filename=filename)


class FakeStream(object):

    def __init__(self, name, input_=None, handlers=None, zmq_args=None):
        self.name = name
