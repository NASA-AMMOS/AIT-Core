AIT Server Introduction
========================

The core of AIT is a "server", :mod:`ait.core.server`, which manages the processing of telemetry, logging, and command messages. The server manages relationships between the following components: 

* **Inbound streams**   - Inbound streams manage incoming data being received by AIT. For example, telemetry messages coming into a port.
* **Outbound streams**   - Outbound streams manage outgoing data being published by AIT. For example, command messages being published to a port.
* **Handlers**   - Handlers do the processing of data for inbound and outbound streams. When a message is received on an inbound stream for instance, a handler can handle the processing that needs to be done on the message before it is passed off to outbound streams or plugins.
* **Plugins**       - Plugins provide functionality that consume data from inbound streams, do something with it, and provide data to outbound streams. The AIT GUI is a plugin.

The AIT Server uses the messaging library ZeroMQ to manage the passing of data between streams and plugins.

Streams, Plugins and Handlers
-----------------------------

Data will generally flow through the components as follows:

-> Inbound Stream -> (Handlers) -> Plugin -> Outbound Stream -> (Handlers) ->


Plugins
^^^^^^^
* Plugins can have any number of inbound streams as inputs and any number of outbound streams as outputs. 
* A plugin **name** is required, and should be formatted like **<package>.<module>.<ClassName>**. The server will use this to import and instantiate the plugin.
* Plugins can have any other arguments you would like. These arguments will be made class attributes when the plugin is instantiated.
* If you would like to add a plugin, it must inherit from :mod:`ait.core.server.plugin.Plugin` and implement the abstract `process` method which is called whenever the plugin receives a message from any of its inbound streams.

Example configuration: 

.. code-block:: none

    plugins:
        - plugin:
            name: ait.gui.AITGUIPlugin
            inputs: 
                - log_stream
                - telem_stream
            outputs:
                - command_stream
            other_parameter: anything_you_need

AIT provides a number of default plugins. Check the `Plugins API documentation <./ait.core.server.plugins.html>`_ for available plugins.


Streams
^^^^^^^
- Streams must be listed under either **inbound-streams** or **outbound-streams**, and must have a **name**.
- Inbound streams can have an integer port or inbound streams as their **input**. Inbound streams can have multiple inputs. A port input should always be listed as the first input to an inbound stream.
- Outbound streams can have plugins or outbound streams as their **input**. Outbound streams can have multiple inputs.

   - Outbound streams also have the option to **output** to an integer port (see :ref:`example config below <Stream_config>`).

- Streams can have any number of **handlers**. A stream passes each received *packet* through its handlers in order and publishes the result.
- There are several stream classes that inherit from the base stream class. These child classes exist for handling the input and output of streams differently based on whether the inputs/output are ports or other streams and plugins. The appropriate stream type will be instantiated based on whether the stream is an inbound or outbound stream and based on the inputs/output specified in the stream's configs. If the input type of an inbound stream is an integer, it will be assumed to be a port. If it is a string, it will be assumed to be another stream name or plugin. Only outbound streams can have an output, and the output must be a port, not another stream or plugin.

.. _Stream_config:
Example configuration:

.. code-block:: none

    inbound-streams:
        - stream:
            name: log_stream
            input: 3077

        - stream:
            name: telem_port_in_stream
            input: 3076
            handlers:
                - my_custom_handlers.TestbedTelemHandler

        - stream:
            name: telem_testbed_stream
            input: telem_port_in_stream
            handlers:
                - name: ait.server.handler.PacketHandler
                  packet: 1553_HS_Packet

    outbound-streams:
        - stream:
            name: command_testbed_stream
            handlers:
                - name: my_custom_handlers.TestbedCommandHandler

        - stream:
            name: command_flightlike_stream
            handlers:
                - name: my_custom_handlers.FlightlikeCommandHandler

        - stream:
            name: command_port_out_stream
            input:
                - command_testbed_stream
                - command_flightlike_stream
            output: 3075


Handlers
^^^^^^^^
* A handler **name** is required, and should be formatted like **<package>.<module>.<ClassName>**. The server will use this to import and instantiate the handler.
* Handlers can have any other arguments you would like. These arguments will be made class attributes when the handler is instantiated.
* If you would like to create a custom handler, it must inherit from :mod:`ait.core.server.Handler` and implement the `handle` method which is called whenever the stream it is subscribed to receives a message. 

See example configuration :ref:`above <Stream_config>`.

Configuring the server
----------------------

AIT uses :ref:`config.yaml <Config_Intro>` to load configuration data for the server.

Here is an example of how the **server** portion of **config.yaml** should look:

.. code-block:: none

    server:
        plugins:
            - plugin:
                name: ait.gui.AITGUIPlugin
                inputs: 
                    - log_stream
                    - telem_testbed_stream
                outputs:
                    - command_testbed_stream

        inbound-streams:
            - stream:
                name: log_stream
                input: 3077

            - stream:
                name: telem_port_in_stream
                input: 3076
                handlers:
                    - my_custom_handlers.TestbedTelemHandler

            - stream:
                name: telem_testbed_stream
                input: telem_port_in_stream
                handlers:
                    - name: ait.server.handler.PacketHandler
                      packet: 1553_HS_Packet

        outbound-streams:
            - stream:
                name: command_testbed_stream
                handlers:
                    - name: my_custom_handlers.TestbedCommandHandler

            - stream:
                name: command_flightlike_stream
                handlers:
                    - name: my_custom_handlers.FlightlikeCommandHandler

            - stream:
                name: command_port_out_stream
                input:
                    - command_testbed_stream
                    - command_flightlike_stream
                output: 3075
