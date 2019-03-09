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
            name: ait.server.plugins.ait_gui_plugin.AITGUIPlugin
            inputs: 
                - log_stream
                - telem_stream
            outputs:
                - command_stream
            other_parameter: anything_you_need


Streams
^^^^^^^
* Streams must be listed under either **inbound-streams** or **outbound-streams**, and must have a **name**.
* Inbound streams can have either an integer port or another inbound stream name as their input. Inbound streams must have exactly one **input**.
* Outbound streams can have plugins or other streams as their input. If a plugin is specifying an outbound stream as its output, than that stream does not need to specify the plugin as its input.
* Outbound streams also have the option to **output** to an integer port (see :ref:`example config below <Stream_config>`).
* Streams can have any number of **handlers** that will be executed in sequence.
* There are several stream types that are instantiated based on the stream's configs. The AIT Server will check if the input or output types of streams are integers, and automatically instantiate the appropriate stream type.

.. _Stream_config:
Example configuration:

.. code-block:: none

    inbound-streams:
        - stream:
            name: log_stream
            input: 3077

        - stream:
            name: telem_stream
            input: 3076
            handlers:
                - name: ait.server.handler.PacketHandler
                  packet: 1553_HS_Packet

    outbound-streams:
        - stream:
            name: command_stream
            output: 3075


Handlers
^^^^^^^^
* A handler **name** is required, and should be formatted like **<package>.<module>.<ClassName>**. The server will use this to import and instantiate the handler.
* Handlers can have any other arguments you would like. These arguments will be made class attributes when the handler is instantiated.
* If you would like to create a custom handler, it must inherit from :mod:`ait.core.server.handler.Handler` and implement the `handle` method which is called whenever the stream it is subscribed to receives a message. 

See example configuration :ref:`above <Stream_config>`.

Parallel Processing
^^^^^^^^^^^^^^^^^^^
In order to accomplish parallel processing paths with handlers, multiple streams that each contain a handler to be executed in parallel should be created and given the same input stream, so that when the original input stream receives a message it will pass it onto all streams subscribed to it, which will each execute their own handlers independently and concurrently.

For example, the following configuration uses **parallel_stream_1** and **parallel_stream_2**, which both have the same input stream, in order to execute **parallel_handler_1** and **parallel_handler_2** in parallel.

.. code-block:: none

    inbound-streams:
        - stream:
            name: log_stream
            input: 3077

        - stream:
            name: parallel_stream_1
            input: log_stream
            handlers:
                - name: parallel_handler_1


        - stream:
            name: parallel_stream_2
            input: log_stream
            handlers:
                - name: parallel_handler_2


Configuring the server
----------------------

AIT uses :ref:`config.yaml <Config_Intro>` to load configuration data for the server.

Here is an example of how the **server** portion of **config.yaml** should look:

.. code-block:: none

    server:
        plugins:
            - plugin:
                name: ait.server.plugins.ait_gui_plugin.AITGUIPlugin
                inputs: 
                    - log_stream
                    - telem_stream
                outputs:
                    - command_stream

        inbound-streams:
            - stream:
                name: log_stream
                input: 3077

            - stream:
                name: telem_stream
                input: 3076
                handlers:
                    - name: ait.server.handler.PacketHandler
                      packet: 1553_HS_Packet

        outbound-streams:
            - stream:
                name: command_stream
                output: 3075
