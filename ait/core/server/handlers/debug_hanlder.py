import ait.core.log
from ait.core.server.handler import Handler


class DebugHandler(Handler):
    def __init__(self, input_type=None, output_type=None, **kwargs):
        super(DebugHandler, self).__init__(input_type, output_type)
        self.handler_name = kwargs.get("handler_name", "DebugHandler")

    def handle(self, input_data):
        ait.core.log.info(f"{self.handler_name} received {len(input_data)} bytes")
        return input_data
