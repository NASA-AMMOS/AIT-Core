import ait.core.log
from .client import PortInputClient
from .client import PortOutputClient
from .client import TCPInputClient
from .client import TCPInputServer
from .client import ZMQInputClient


class Stream:
    """
    This is the base Stream class that all streams will inherit from.
    It calls its handlers to execute on all input messages sequentially,
    and validates the handler workflow if handler input and output
    types were specified.
    """

    def __init__(self, name, inputs, handlers, zmq_args=None, **kwargs):
        """
        Params:
            name:       string name of stream (should be unique)
            inputs:     list of inputs to stream.
                        if input is int, port number to receive messages on
                        if input is string, stream or plugin name to receive
                            messages from
            handlers:   list of handlers (empty list if no handlers for stream)
            zmq_args:   (optional) dict containing the follow keys:
                            zmq_context
                            zmq_proxy_xsub_url
                            zmq_proxy_xpub_url
                        Defaults to empty dict here. Default values
                        assigned during instantiation of parent class.
            **kwargs:   (optional) Depends on requirements of child class
        Raises:
            ValueError: if workflow is not found to be valid based on handlers'
                        provided input and output types
        """
        self.name = name
        self.inputs = inputs if inputs is not None else []
        self.handlers = handlers

        if zmq_args is None:
            zmq_args = {}

        if not self.valid_workflow():
            raise ValueError(
                "Sequential workflow inputs and outputs "
                + "are not compatible. Workflow is invalid."
            )

        # This calls __init__ on subclass of ZMQClient
        if "output" in kwargs:
            super(Stream, self).__init__(
                input=self.inputs, output=kwargs["output"], **zmq_args
            )
        else:
            super(Stream, self).__init__(input=self.inputs, **zmq_args)

    def __repr__(self):
        return "<{} name={}>".format(
            str(type(self)).split(".")[-1].split("'")[0], self.name
        )

    def process(self, input_data, topic=None):
        """
        Invokes each handler in sequence.
        Publishes final output data.
        Terminates all handler calls and does not publish data if None is received from a single handler.

        Params:
            input_data:  message received by stream
            topic:       name of plugin or stream message received from,
                         if applicable
        """
        for handler in self.handlers:
            output = handler.handle(input_data)
            if output:
                input_data = output
            else:
                msg = (
                    type(handler).__name__
                    + " returned no data and caused the handling process to end."
                )
                ait.core.log.info(msg)
                return
        self.publish(input_data)

    def valid_workflow(self):
        """
        Return true if each handler's output type is the same as
        the next handler's input type. Return False if not.

        Returns:    boolean - True if workflow is valid, False if not
        """
        for ix, handler in enumerate(self.handlers[:-1]):
            next_input_type = self.handlers[ix + 1].input_type

            if handler.output_type is not None and next_input_type is not None:
                if handler.output_type != next_input_type:
                    return False

        return True


def input_stream_factory(name, inputs, handlers, zmq_args=None):
    """
    This factory preempts the creating of streams directly.  It accepts
    the same args as any given stream class and then based primarily on the
    values in 'inputs' decides on the appropriate stream to instantiate and
    then returns it.
    """
    stream = None

    # Stream specs in the form:
    # - stream:
    #     name: telem_stream_udp_server
    #     input:
    #         - 24000
    # - stream:
    #     name: telem_stream_zmq_server
    #     input:
    #         - foo_zmq
    if len(inputs) == 1:
        if type(inputs[0]) is int and 1024 <= inputs[0] <= 65535:
            stream = PortInputStream(name, inputs, handlers, zmq_args=zmq_args)
        elif type(inputs[0]) is str:
            stream = ZMQStream(name, inputs, handlers, zmq_args=zmq_args)
        else:
            raise ValueError(
                "Input stream specification with 1 arg must be [ {port_num|str} ]"
            )

    # Stream specs in the form:
    # - stream:
    #     name: telem_stream_udp_server
    #     input:
    #         - 'UDP'
    #         - 'server'
    #         - 24000
    # - stream:
    #     name: telem_stream_tcp_server
    #     input:
    #         - 'TCP'
    #         - 'server'
    #         - 24000
    # - stream:
    #     name: telem_stream_tcp_client
    #     input:
    #         - 'TCP'
    #         - '1.2.3.4'
    #         - 24000
    elif len(inputs) == 3:
        if type(inputs[0]) is str and inputs[0].upper() == "TCP":
            if type(inputs[1]) is str and inputs[1].lower() == "server":
                if type(inputs[2]) is int and 1024 <= inputs[2] <= 65535:
                    stream = TCPInputServerStream(name, inputs[1:], handlers, zmq_args)
                else:
                    raise ValueError(
                        "Input stream specification with 3 args must be [ {'TCP'|'UDP'}, {'server'|ip_address}, {port_num} ]"
                    )
            elif type(inputs[1]) is str and inputs[1].lower() != "server":
                if type(inputs[2]) is int and 1024 <= inputs[2] <= 65535:
                    stream = TCPInputClientStream(name, inputs[1:], handlers, zmq_args)
                else:
                    raise ValueError(
                        "Input stream specification with 3 args must be [ {'TCP'|'UDP'}, {'server'|ip_address}, {port_num} ]"
                    )
            else:
                raise ValueError(
                    "Input stream specification with 3 args must be [ {'TCP'|'UDP'}, {'server'|ip_address}, {port_num} ]"
                )
        elif type(inputs[0]) is str and inputs[0].upper() == "UDP":
            if type(inputs[1]) is str and inputs[1].lower() == "server":
                if type(inputs[2]) is int and 1024 <= inputs[2] <= 65535:
                    stream = PortInputStream(
                        name, inputs[2:], handlers, zmq_args=zmq_args
                    )
                else:
                    raise ValueError(
                        "Input stream specification with 3 args must be [ {'TCP'|'UDP'}, {'server'|ip_address}, {port_num} ]"
                    )
            else:
                raise NotImplementedError("UDP client not supported atm")
        else:
            raise ValueError(
                "Input stream specification with 3 args must be [ {'TCP'|'UDP'}, {'server'|ip_address}, {port_num} ]"
            )
    else:
        raise ValueError("Input stream specification must contain either 1 or 3 args")

    if stream is None:
        raise ValueError("Input stream specification invalid")
    return stream


class PortInputStream(Stream, PortInputClient):
    """
    This stream type listens for messages from a UDP port and publishes to a ZMQ socket.
    """

    def __init__(self, name, inputs, handlers, zmq_args=None):
        super(PortInputStream, self).__init__(name, inputs, handlers, zmq_args)


class TCPInputServerStream(Stream, TCPInputServer):
    """
    This stream type listens for messages from a TCP port and publishes to a ZMQ socket.
    """

    def __init__(self, name, inputs, handlers, zmq_args=None):
        super(TCPInputServerStream, self).__init__(name, inputs, handlers, zmq_args)


class TCPInputClientStream(Stream, TCPInputClient):
    """
    This stream type connects to a TCP server and publishes to a ZMQ socket.
    """

    def __init__(self, name, inputs, handlers, zmq_args=None):
        super(TCPInputClientStream, self).__init__(name, inputs, handlers, zmq_args)


class ZMQStream(Stream, ZMQInputClient):
    """
    This stream type listens for messages from another stream or plugin and publishes
    to a ZMQ socket.
    """

    def __init__(self, name, inputs, handlers, zmq_args=None):
        super(ZMQStream, self).__init__(name, inputs, handlers, zmq_args)


class PortOutputStream(Stream, PortOutputClient):
    """
    This stream type listens for messages from another stream or plugin and
    publishes to a UDP port.
    """

    def __init__(self, name, inputs, output, handlers, zmq_args=None):
        super(PortOutputStream, self).__init__(
            name, inputs, handlers, zmq_args, output=output
        )
