from ait.server.handler import Handler


class ExampleHandler(Handler):

    def __init__(self, input_type=None, output_type=None, **kwargs):
        super(ExampleHandler, self).__init__(input_type, output_type)

    def handle(self, input_data):
        pass
