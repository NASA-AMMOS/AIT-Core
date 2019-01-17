from ait.server.handler import Handler


class TmTransFrameDecodeHandler(Handler):

    def __init__(self, input_type, output_type=None):
        super(TmTransFrameDecodeHandler, self).__init__(input_type, output_type)

    def handle(self, input_data):
        return input_data + 5
