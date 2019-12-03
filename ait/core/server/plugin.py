from abc import ABCMeta, abstractmethod

import gevent
import gevent.monkey; gevent.monkey.patch_all()

import ait.core
from .client import ZMQInputClient

class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    __metaclass__ = ABCMeta

    def __init__(self, inputs, outputs, zmq_args={}, **kwargs):
        """
        Params:
            inputs:     names of inbound streams plugin receives data from
            outputs:    names of outbound streams plugin sends its data to
            zmq_args:   dict containing the follow keys:
                            zmq_context
                            zmq_proxy_xsub_url
                            zmq_proxy_xpub_url
                        Defaults to empty dict. Default values
                        assigned during instantiation of parent class.
            **kwargs:   (optional) Dependent on requirements of child class.
        """
        self.name = type(self).__name__
        self.inputs = inputs
        self.outputs = outputs

        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(**zmq_args)

    def __repr__(self):
        return '<Plugin name={}>'.format(self.name)

    @abstractmethod
    def process(self, input_data, topic=None):
        """
        Not implemented by base Plugin class.
        This process method must be implemented by any custom plugin class
        that inherits from this base Plugin.

        Params:
            input_data:  Message received from any of the plugin's input streams.
            topic:       Name of stream that message was received from.
        """
        pass
