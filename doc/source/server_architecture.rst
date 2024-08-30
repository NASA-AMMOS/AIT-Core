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
* Plugins can be configured to run in separate processes.  The plugin configuration includes an optional attribute **process_id**.  When the attribute is assigned a value, the server will spawn a new process for the plugin.  If multiple plugins specify the same value, then they will all run together in that process.  By default, plugins run in the same process as the AIT Server.

If you would like to add a plugin, it must inherit from :mod:`ait.core.server.plugin.Plugin` and implement the abstract `process` method which is called whenever the plugin receives a message from any of its inbound streams.

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


Example configuration segment utilizing the **process_id** attribute:

.. code-block:: none

    plugins:
        - plugin:
            name: ait.gui.AITGUIPlugin
            process_id: ait_plugin_process_alpha
            inputs:
                ...


AIT provides a number of default plugins. Check the `Plugins API documentation <./ait.core.server.plugins.html>`_ for available plugins.


Streams
^^^^^^^
- Streams must be listed under either **inbound-streams** or **outbound-streams**, and must have a **name**.
- **Inbound streams** can have an integer port or inbound streams as their **input**. Inbound streams can have multiple inputs. A port input should always be listed as the first input to an inbound stream.

    - The server sets up an input stream that emits properly formed telemetry packet messages over a globally configured topic. This is used internally by the ground script API for telemetry monitoring. The input streams that pass data to this stream must output data in the Packet UID annotated format that the core packet handlers use. The input streams used can be configured via the **server.api-telemetry-streams** field. If no configuration is provided the server will default to all valid input streams if possible. See :ref:`the Ground Script API documentation <api_telem_setup>` for additional information.

- **Outbound streams** can have plugins or outbound streams as their **input**. Outbound streams can have multiple inputs.

   - Outbound streams also have the option to **output** to an integer port (see :ref:`example config below <Stream_config>`).

   - The server exposes an entry point for commands submitted by other processes. During initialization, this entry point will be connected to a single outbound stream, either explicitly declared by the stream (by setting the **command-subscriber** field; see :ref:`example config below <Stream_config>`), or decided by the server (select the first outbound stream in the configuration file).

- Streams can have any number of **handlers**. A stream passes each received *packet* through its handlers in order and publishes the result.
- There are several stream classes that inherit from the base stream class. These child classes exist for handling the input and output of streams differently based on whether the inputs/output are ports or other streams and plugins. The appropriate stream type will be instantiated based on whether the stream is an inbound or outbound stream and based on the inputs/output specified in the stream's configs. If the input type of an inbound stream is an integer, it will be assumed to be a port. If it is a string, it will be assumed to be another stream name or plugin. Only outbound streams can have an output, and the output must be a port, not another stream or plugin.

.. _Stream_config:

Example configuration:

.. code-block:: none

    inbound-streams:
        - stream:
            name: log_stream
            input:
                - 3077

        - stream:
            name: telem_port_in_stream
            input:
                - 3076
            handlers:
                - my_custom_handlers.TestbedTelemHandler

        - stream:
            name: telem_testbed_stream
            input:
                - telem_port_in_stream
            handlers:
                - name: ait.server.handlers.PacketHandler
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
            command-subscriber: True

        - stream:
            name: command_port_out_stream
            input:
                - command_testbed_stream
                - command_flightlike_stream
            output:
                - 3075


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

        api-telemetry-streams:
            - telem_testbed_stream

        inbound-streams:
            - stream:
                name: log_stream
                input:
                    - 3077

            - stream:
                name: telem_port_in_stream
                input:
                    - 3076
                handlers:
                    - my_custom_handlers.TestbedTelemHandler

            - stream:
                name: telem_testbed_stream
                input:
                    - telem_port_in_stream
                handlers:
                    - name: ait.server.handlers.PacketHandler
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
                output:
                    - 3075



Notes on Security
-----------------

AIT provides a light-weight implementation and configuration to make installation and setup straightforward for new users.
However, there are real-world security considerations that projects should take into account as part of their adaptation.
While many concerns are general, actual implementation details are expected to vary per project.
As such, those specifics should be discussed with your security and operations teams.


Network Security
^^^^^^^^^^^^^^^^

AIT uses ZeroMQ as the underlying messaging library with no security mechanisms enabled by default.
While ZeroMQ port-based input streams are supported, we recommend that adaptations not expose unprotected ports.  Instead consider alternate mechanisms, such as Plugins or network service, which publish messages to ZeroMQ.
For further protection that includes authentication and encryption, we recommend utilizing CurveZMQ (http://curvezmq.org/), which provides security protocols for ZeroMQ.


Configuration Security
^^^^^^^^^^^^^^^^^^^^^^

AIT uses configurations files that provide details for telemetry, commands, databases, and much more.
These configuration files, if left unsecured, could provide an entry point for bad-actors to introduce exploits.
As such, we highly recommend that all configuration files and working directories be secured from unauthorized edits or replacement.


