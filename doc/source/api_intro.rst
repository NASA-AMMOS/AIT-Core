Application Programming Interface Module
========================================

The :mod:`bliss.core.api` module provides an Application Programming Interface (API) to your instrument by bringing together the ``core.cmd`` and ``core.tlm`` modules in a complementary whole, allowing you to script instrument interactions. The two primary tools in the ``api`` module that you'll use for scripting instrument interactions are the :class:`bliss.core.api.Instrument` class and the :func:`bliss.core.api.wait` function.

Instrument
----------

The :class:`bliss.core.api.Instrument` class brings together AIT's commanding and telemetry tools into a single interface. With this you can monitor multiple telemetry packet streams and send commands to your instrument.  Let's look at a few examples.

First we'll instantiate an instance of our Instrument with the default commanding and telemetry connections::

    my_instrument = bliss.core.api.Instrument()

We can access telemetry via the ``tlm`` attribute. We'll assume that we have a packet called **BLISS_EHS** defined in our **tlm.yaml** file::

    telem = my_instrument.tlm.BLISS_EHS

    # print the number of BLISS_EHS packets we've received
    len(telem)

Let's suppose we have a telemetry field defined in **BLISS_EHS** called **CmdsRcvd** which keeps track of how many commands the instrument has received. We could pull that out of the most recently received telemetry packet with::

    telem.CmdsRcvd

Let's send a command to our instrument. We'll assume we have a "no op" command defined as **BLISS_NO_OP** in our **cmd.yaml** file. You can access the commanding functionality via the ``cmd`` attribute::

    my_instrument.cmd.send('BLISS_NO_OP')

If our command required arguments we could specify them a number of ways::

    my_instrument.cmd.send('BLISS_SET_OP_MODE PAYLOAD_SAFE')
    my_instrument.cmd.send('BLISS_SET_OP_MODE', 'PAYLOAD_SAFE')
    my_instrument.cmd.send('BLISS_SET_OP_MODE', mode='PAYLOAD_SAFE')
    

Wait
----

The :func:`blis.core.api.wait` function allows us to halt execution in a script until a specified number of seconds have passed or until a supplied condition evaluates to ``True``. 

Wait until 2 seconds have passed::

    wait(2)

Wait until telemetry tells us that two commands have been received::

    wait('my_instrument.tlm.BLISS_EHS.CmdsRcvd == 2')

Expressions can be specified as a string (as above), a lambda, or as a function. All 3 of the following are equivalent::

    # Using a string
    wait('my_instrument.tlm.BLISS_EHS.CmdsRcvd == 2')
    
    # Using a lambda expression
    wait(lambda: my_instrument.tlm.BLISS_EHS.CmdsRcvd == 2)
    
    # Using a function
    def twoCmdsRcvd(): return my_instrument.tlm.BLISS_EHS.CmdsRcvd == 2
    wait(twoCmdsRcvd)

Putting it all Together
-----------------------

Below we'll create an example script to do a simple test of the API to ensure that we can read telemetry from our instrument, send it a command, and react to changes in the telemetry.

.. code-block:: python

    #!/usr/bin/env python

    from bliss.core import log
    from bliss.core.api import Instrument, wait


    inst = Instrument()

    #
    # Wait (forever) until we have have at least two EHS packets.
    wait(lambda: len(inst.tlm.BLISS_EHS) > 2)


    #
    # Send a command
    inst.cmd.send('BLISS_NO_OP')


    #
    # The packet buffer may be accessed directly for the current
    # packet.  The current packet may also be accessed via subscript
    # zero.  For example, the following are equivalent:
    #
    #   inst.tlm.BLISS_EHS.CmdCmdsRcvd == inst.tlm.BLISS_EHS[0].CmdCmdsRcvd
    #
    # Older packets are accessed using increasing subscripts, e.g.
    # the penultimate received packet is accessed via:
    #
    #   inst.tlm.BLISS_EHS[1].CmdCmdsRcvd
    #
    # Here we'll wait until telemetry tells us that it received our
    # command or we'll timeout (and raise an Exception) if we wait
    # 5 seconds and nothing happens.
    if wait('inst.tlm.BLISS_EHS.CmdCmdsRcvd == inst.tlm.BLISS_EHS[1].CmdCmdsRcvd + 1', timeout=5):

        log.info('Command received')
    else:
        log.info('Timeout')
       
