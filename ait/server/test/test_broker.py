import ait
from ait.core import cfg
import ait.server
from ait.server.broker import AitBroker
from ait.server.stream import Stream
from ait.server.handlers import *
from ait.server.plugins import *
import nose
from nose.tools import *
import mock


@mock.patch.object(ait.core.log, 'warn')
@mock.patch.object(ait.server.broker.AitBroker, 'create_stream')
class TestStreamConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def setUp(self):
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [ ]

    def test_no_inbound_streams(self,
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
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        ait.broker.load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid inbound telemetry stream configurations found. '
            'No telemetry will be received (or displayed).')
        # assert outbound stream is added successfully
        assert len(ait.broker.outbound_streams) == 1

    def test_no_outbound_streams(self,
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
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        ait.broker.load_streams()

        # assert warning is logged
        log_warn_mock.assert_called_with(
            'No valid outbound telemetry stream configurations found. '
            'No telemetry will be published.')
        # assert inbound stream is added successfully
        assert len(ait.broker.inbound_streams) == 1


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
        config = {'input': 'some_stream',
                  'handlers': ['some-handler']}

        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path.name'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    def test_duplicate_stream_name(self):
        """ Tests that a ValueError is raised when creating a stream with
        a name that already belongs to another stream or plugin """
        config = {'input': 'some_stream',
                  'name': 'myname',
                  'handlers': ['some-handler']}

        # Testing existing name in plugins
        ait.broker.plugins = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'outbound')

        # Testing existing name in inbound_streams
        ait.broker.plugins = [ ]
        ait.broker.inbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

        # Testing existing name in outbound_streams
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [FakeStream(name='myname')]
        with assert_raises_regexp(ValueError, 'Stream name already exists. Please rename.'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    def test_no_stream_input(self):
        """ Tests that a ValueError is raised when creating a stream with
        no input specified in the config """
        config = {'name': 'some_stream',
                  'handlers': ['some-handler']}

        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path.input'):
            ait.broker.create_stream(config, 'some_path', 'inbound')

    @mock.patch.object(ait.server.broker.AitBroker, 'create_handler')
    def test_successful_stream_creation(self, create_handler_mock):
        """ Tests that streams are successfully created both with or without
        handlers """
        # Testing stream creating with handlers
        config = {'name': 'some_stream',
                  'input': 'some_input',
                  'handlers': ['some-handler']}
        created_stream = ait.broker.create_stream(config, 'some_path', 'inbound')
        assert type(created_stream) == Stream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list

        # Testing stream creation without handlers
        config = cfg.AitConfig(config={'name': 'some_stream',
                                       'input': 'some_input'})
        created_stream = ait.broker.create_stream(config, 'some_path', 'inbound')
        assert type(created_stream) == Stream
        assert created_stream.name == 'some_stream'
        assert created_stream.input_ == 'some_input'
        assert type(created_stream.handlers) == list


class TestHandlerCreation(object):

    def test_no_handler_config(self):
        """ Tests that a ValueError is raised when creating a handler with
        a config of None """
        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path'):
            ait.broker.create_handler(None, 'some_path')

    def test_handler_creation_with_no_configs(self):
        """ Tests handler is successfully created when it has not configs """
        config = 'tm_trans_frame_decode_handler'
        handler = ait.broker.create_handler(config, 'some_path')
        assert type(handler) == tm_trans_frame_decode_handler.TmTransFrameDecodeHandler
        assert handler.input_type is None
        assert handler.output_type is None

    def test_handler_creation_with_configs(self):
        """ Tests handler is successfully created when it has configs """
        config = {'ccsds_packet_handler': {'input_type': 'int', 'output_type': 'int'}}
        handler = ait.broker.create_handler(config, 'some_path')
        assert type(handler) == ccsds_packet_handler.CcsdsPacketHandler
        assert handler.input_type == 'int'
        assert handler.output_type == 'int'

    def test_handler_that_doesnt_exist(self):
        """ Tests that exception thrown if handler doesn't exist """
        config = 'some_nonexistant_handler'
        with assert_raises_regexp(ImportError, 'No module named %s' % config):
            ait.broker.create_handler(config, 'some_path')


@mock.patch.object(ait.core.log, 'warn')
@mock.patch.object(ait.core.log, 'error')
class TestPluginConfigParsing(object):
    test_yaml_file = '/tmp/test.yaml'

    def setUp(self):
        ait.broker.plugins = [ ]

    def test_no_plugins_listed(self,
                               log_error_mock,
                               log_warn_mock):
        """ Tests that warning logged if no plugins configured """
        yaml = """
                default:
                    server:
                        plugins:
               """
        rewrite_and_reload_config(self.test_yaml_file, yaml)

        ait.broker.load_plugins()

        log_warn_mock.assert_called_with(
            'No valid plugin configurations found. No plugins will be added.')


class TestPluginCreation(object):

    def test_plugin_with_no_config(self):
        """ Tests that error raised if plugin not configured """
        config = None
        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path'):
            ait.broker.create_plugin(config, 'some_path')

    def test_plugin_missing_name(self):
        """ Tests that error raised if plugin has no name """
        config = {'inputs': 'some_inputs'}
        with assert_raises_regexp(ValueError,
                                  'The parameter %s is missing from config.yaml'
                                  % 'some_path.name'):
            ait.broker.create_plugin(config, 'some_path')

    @mock.patch.object(ait.core.log, 'warn')
    def test_plugin_missing_inputs(self, log_warn_mock):
        """ Tests that warning logged if plugin has no inputs and
        plugin created anyways """
        config = {'name': 'ait_gui_plugin'}
        ait.broker.create_plugin(config, 'some_path')

        log_warn_mock.assert_called_with('The parameter some_path.inputs is missing'
                                         ' from config.yaml (/tmp/test.yaml).')

    def test_plugin_name_already_in_use(self):
        """ Tests that error raised if name already in use """
        ait.broker.plugins = [ait_gui_plugin.AitGuiPlugin(None)]
        config = {'name': 'ait_gui_plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ValueError,
                                  'Plugin name already exists. Please rename.'):
            ait.broker.create_plugin(config, 'some_path')

    def test_plugin_doesnt_exist(self):
        """ Tests that error raised if plugin doesn't exist """
        config = {'name': 'some_nonexistant_plugin', 'inputs': 'some_inputs'}
        with assert_raises_regexp(ImportError,
                                  'No module named some_nonexistant_plugin'):
            ait.broker.create_plugin(config, 'some_path')


def rewrite_and_reload_config(filename, yaml):
    with open(filename, 'wb') as out:
        out.write(yaml)

    ait.config.reload(filename=filename)


class FakeStream(object):

    def __init__(self, name, input_=None, handlers=None, zmq_args=None):
        self.name = name
