class Handler(object):

    def __init__(self, input_type=None, output_type=None):
        self.input_type = input_type
        self.output_type = output_type

    def __repr__(self):
        return '<handler.%s' % (self.__class__.__name__)

    def validate_input(self, input_data):
        if self.input_type:
            try:
                converted = eval("%s(%s)" % (self.input_type, input_data))
            except Exception as e:
                raise(e)

            return converted

        return input_data

    def execute_handler(self, input_data):
        try:
            checked_input = self.validate_input(input_data)
        except Exception as e:
            raise ValueError('Input is not of valid type: ', e)

        return self.handle(checked_input)

    def handle(self, input_data):
        raise NotImplementedError((
            'This handle method must be implemented by a custom handler class ' +
            'that inherits from this abstract Handler. This abstract Handler ' +
            'class should not be instantiated.'))
