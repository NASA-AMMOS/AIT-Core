Application Programming Interface Module
========================================

The :mod:`ait.core.api` module provides an Application Programming Interface (API) to your instrument by bringing together the ``core.cmd`` and ``core.tlm`` modules in a complementary whole, allowing you to script instrument interactions. The two primary tools in the ``api`` module that you'll use for scripting instrument interactions are the :class:`ait.core.api.Instrument` class and the :func:`ait.core.api.wait` function.

Instrument
----------

The :class:`ait.core.api.Instrument` class brings together AIT's commanding and telemetry tools into a single interface. With this you can monitor multiple telemetry packet streams and send commands to your instrument.  Let's look at a few examples.

First we'll instantiate an instance of our Instrument with the default commanding and telemetry connections::

    my_instrument = ait.core.api.Instrument()

We can access telemetry via the ``tlm`` attribute. We'll assume that we have a packet called **1553_HS_Packet** defined in our **tlm.yaml** file::

    telem = my_instrument.tlm.1553_HS_Packet

    # print the number of 1553_HS_Packet packets we've received
    len(telem)

Let's suppose we have a telemetry field defined in **1553_HS_Packet** called **CmdsRcvd** which keeps track of how many commands the instrument has received. We could pull that out of the most recently received telemetry packet with::

    telem.CmdsRcvd

Let's send a command to our instrument. We'll assume we have a "no op" command defined as **AIT_NO_OP** in our **cmd.yaml** file. You can access the commanding functionality via the ``cmd`` attribute::

    my_instrument.cmd.send('AIT_NO_OP')

If our command required arguments we could specify them a number of ways::

    my_instrument.cmd.send('AIT_SET_OP_MODE PAYLOAD_SAFE')
    my_instrument.cmd.send('AIT_SET_OP_MODE', 'PAYLOAD_SAFE')
    my_instrument.cmd.send('AIT_SET_OP_MODE', mode='PAYLOAD_SAFE')
    

Wait
----

The :func:`ait.core.api.wait` function allows us to halt execution in a script until a specified number of seconds have passed or until a supplied condition evaluates to ``True``. 

Wait until 2 seconds have passed::

    wait(2)

Wait until telemetry tells us that two commands have been received::

    wait('my_instrument.tlm.1553_HS_Packet.CmdsRcvd == 2')

Expressions can be specified as a string (as above), a lambda, or as a function. All 3 of the following are equivalent::

    # Using a string
    wait('my_instrument.tlm.1553_HS_Packet.CmdsRcvd == 2')
    
    # Using a lambda expression
    wait(lambda: my_instrument.tlm.1553_HS_Packet.CmdsRcvd == 2)
    
    # Using a function
    def twoCmdsRcvd(): return my_instrument.tlm.1553_HS_Packet.CmdsRcvd == 2
    wait(twoCmdsRcvd)

Putting it all Together
-----------------------

Below we'll create an example script to do a simple test of the API to ensure that we can read telemetry from our instrument, send it a command, and react to changes in the telemetry.

.. code-block:: python

    #!/usr/bin/env python

    from ait.core import log
    from ait.core.api import Instrument, wait


    inst = Instrument()

    #
    # Wait (forever) until we have have at least two EHS packets.
    wait(lambda: len(inst.tlm.1553_HS_Packet) > 2)


    #
    # Send a command
    inst.cmd.send('AIT_NO_OP')


    #
    # The packet buffer may be accessed directly for the current
    # packet.  The current packet may also be accessed via subscript
    # zero.  For example, the following are equivalent:
    #
    #   inst.tlm.1553_HS_Packet.CmdCmdsRcvd == inst.tlm.1553_HS_Packet[0].CmdCmdsRcvd
    #
    # Older packets are accessed using increasing subscripts, e.g.
    # the penultimate received packet is accessed via:
    #
    #   inst.tlm.1553_HS_Packet[1].CmdCmdsRcvd
    #
    # Here we'll wait until telemetry tells us that it received our
    # command or we'll timeout (and raise an Exception) if we wait
    # 5 seconds and nothing happens.
    if wait('inst.tlm.1553_HS_Packet.CmdCmdsRcvd == inst.tlm.1553_HS_Packet[1].CmdCmdsRcvd + 1', _timeout=5):
        log.info('Command received')
    else:
        log.info('Timeout')
       
.. _api_telem_setup:

Getting Telemetry to Monitor
----------------------------

The API's Instrument interface provides users with an access point for monitoring telemetry in ground scripts. To facilitate this, the C&DH server sets up a special telemetry stream that emits data on a global message topic to which the API subscribes.

The input streams that send messages to this topic can be configured via the **server.api-telemetry-streams** field. This field should be a list of input stream names which output their messages in the Packet-UID-annotated format that the built-in :class:`PacketHandler` / :class:`CCSDSPacketHandler` handlers use.

.. code-block::

    server:
        api-telemetry-streams:
            - telem_testbed_stream

        inbound-streams:
            - stream:
                name: telem_testbed_stream
                input: telem_port_in_stream
                handlers:
                    - name: ait.server.handlers.PacketHandler
                      packet: 1553_HS_Packet

            
You should ensure that any custom handlers you write output their messages in the same format if you wish to use them with the API. Similarly, you must ensure that any streams specified in the **server.api-telemetry-streams** field output their data in the correct format. The server does not attempt to validate this when configuration is provided and message format issues will (very likely) cause problems when the API attempts to process them.

The server will do its best to detect all available input streams and use them as inputs to this topic if no configuration is provided via the **server.api-telemetry-streams** field. An input stream is considered valid in this case if its last handler is one of the handlers that outputs in the Packet-UID-annotated format.
