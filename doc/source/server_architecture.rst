AIT Server Introduction
========================

The core of AIT is a "server", :mod:`ait.core.server`, which manages the processing of telemetry, logging, and command messages. The server manages relationships between the following components: 

* **inbound streams**   - inbound streams manage incoming data being recieved by AIT, for example telemtry messages coming into a port.
* **outbound streams**   - outbound streams manage outgoing data being published by AIT, for example command messages being published to a port.
* **handlers**   - handlers do the processing of data for inbound and outbound streams. When a message is received on an inbound stream for instance, a handler can handle the processing that needs to be done on the message before it is passed off to outbound streams or plugins.
* **plugins**       - plugins provide functionality that consume data from inbound streams, do something with it, and provide data to outbound streams. The AIT GUI is a plugin.

The AIT Server uses the messaging library ZeroMQ to manage the passing of data between streams and plugins.

Streams, Plugins and Handlers
-----------------------------

Data will generally flow through the components as follows:

-> Inbound Stream -> (Handlers) -> Plugin -> Outbound Stream -> (Handlers) ->

* Plugins can have any number of inbound streams as inputs and any number of outbound streams as outputs. 
* Inbound streams can have either integer ports or other inbound stream names as inputs.
* Outbound streams can have either plugin or inbound stream names as inputs. They can output to other outbound streams or to an integer port.
* Streams can have any number of handlers that will be executed in sequence.

In order to accomplish parallel processing paths with handlers, multiple streams that each contain a handler to be executed in parallel should be created and given the same input stream, so that when the original input stream receives a message it will pass it onto all streams subscribed to it, which will each execute their own handlers independently and concurrently.

To customize the functionality of AIT, users may add custom handlers and plugins, and customize their configurations.

All streams and plugins inherit from the base class :mod:`ait.core.server.client.ZMQClient` which handles the necessary ZeroMQ functionality. If you would like to add a plugin, it must inherit from :mod:`ait.core.server.plugin.Plugin` and implement the abstract `process` method which is called whenever the plugin receives a message from any of its inbound streams.

There are several stream types that are instantiated based on the stream's configs. The AIT Server will check if the input or output types of streams are integers, and automatically instantiate the appropriate stream type.

If you would like to create a custom handler, it must inherit from :mod:`ait.core.server.handler.Handler` and implement the `handle` method which is called whenever the stream it is attached to receives a message. 


Configuring the server
----------------------

AIT uses `**config.yaml** <https://ait-core.readthedocs.io/en/master/configuration_intro.html>` to load configuration data for the server.

Here is an example of the **server** portion of **config.yaml**:

.. code-block:: none

    server:
        plugins:
            - plugin:
                name: ait.server.plugins.ait_gui_plugin
                inputs: 
                    - log_stream
                    - telem_stream

        inbound-streams:
            - stream:
                name: log_stream
                input: 3077

            - stream:
                name: telem_stream
                input: 3076
                handlers:
                    - name: ait.server.handlers.ait_packet_handler
                      packet: 1553_HS_Packet

        outbound-streams:
            - stream:
                name: command_stream
                input: AitGuiPlugin
                output: 3075

Plugins
^^^^^^^
* A plugin **name** is required, and should be formatted like **<package>.<module>.<ClassName>**. The server will use this to import and instantiate the plugin.
* A plugin can have any number of inputs.
* Plugins can have any other arguments you would like. These arguments will be made class attributes when the plugin is instantiated.

Streams
^^^^^^^
* Streams must be listed under either **inbound-streams** or **outbound-streams**, and must have a **name** and exactly one **input**.
* A stream can have any number of handlers. 

Handlers
^^^^^^^^
* A handler **name** is required, and should be formatted like **<package>.<module>.<ClassName>**. The server will use this to import and instantiate the handler.
* Handlers can have any other arguments you would like. These arguments will be made class attributes when the handler is instantiated.

