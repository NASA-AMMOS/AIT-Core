class Handler(object):

    def __init__(self, name, input_type=None, output_type=None):
        self.name = name
        self.input_type = input_type
        self.output_type = output_type

    def __repr__(self):
        return '<handler.%s' % (self.__class__.__name__)

    def validate_input(self, input_):
        if self.input_type:
            try:
                converted = eval("%s(%s)" % (self.input_type, input_))
            except Exception as e:
                raise(e)

            return converted

        return input_

    def execute_handler(self, input_):
        try:
            checked_input = self.validate_input(input_)
        except Exception as e:
            raise ValueError('Input is not of valid type: ', e)

        return self.handle(checked_input)

    def handle(self, input_):
        raise NotImplementedError((
            'This handle method must be implemented by a custom handler class ' +
            'that inherits from this abstract Handler. This abstract Handler ' +
            'class should not be instantiated.'))


class CcsdsPacketHandler(Handler):

    def __init__(self, name, input_type, output_type=None):
        super(CcsdsPacketHandler, self).__init__(name, input_type, output_type)

    def handle(self, input_):
        return input_ + 5


class TmTransFrameDecodeHandler(Handler):

    def __init__(self, name, input_type, output_type=None):
        super(TmTransFrameDecodeHandler, self).__init__(name, input_type, output_type)

    def handle(self, input_):
        return input_ + 5
