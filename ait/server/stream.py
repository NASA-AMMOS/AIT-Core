import ait.core
from ait.core import cfg


class Stream(object):
    VALID_INPUTS = [ ]

    def __init__(self, s, index):
        self.config_path = 'server.%s-streams[%d].stream' % (self._type(), index)
        stream = cfg.AitConfig(config=s).get('stream')

        if stream is None:
            msg = cfg.AitConfigMissing(self.config_path).args[0]
            raise ValueError(msg)

        self.name = stream.get('name', '<unnamed>')
        stream_input = stream.get('input', None)

        if stream_input is None:
            msg = cfg.AitConfigMissing(self.config_path + '.input').args[0]
            raise ValueError(msg)

        # choosing first input type for now
        self.input_type = stream_input._config.keys()[0]

        if self.input_type not in self.VALID_INPUTS:
            msg = '%s\'s input type "%s" is not valid.' % (self.config_path, self.input_type)
            raise ValueError(msg)
        else:
            self.input = stream_input.get(self.input_type)

    def _type(self):
        return self.__class__.__name__.split('Stream')[0].lower()

    def __repr__(self):
        return '<stream.%s name=%s>' % (self.__class__.__name__, self.name)

    def publish(self):
        pass

    def validate_workflow(self):
        pass


class InboundStream(Stream):
    VALID_INPUTS = ['port', 'stream']

    def __init__(self, stream, index):
        super(InboundStream, self).__init__(stream, index)


class OutboundStream(Stream):
    VALID_INPUTS = ['plugin', 'stream']

    def __init__(self, stream, index):
        super(OutboundStream, self).__init__(stream, index)
