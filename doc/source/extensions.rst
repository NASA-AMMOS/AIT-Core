Core Library Extensions
=======================

AIT allows users to easily overwrite core library classes used in telemetry handling, commanding, EVR processing, and limit checking to meet project specific use cases. Below we'll look at how  we could create an extension to modify the default command encoding behavior in the toolkit.

Preface
-------

AIT needs to be able to find your extension and import it in order for everything to work as expected. For this example we will be including the new module along with the core AIT code for convenience. Generally users will use the **PYTHONPATH** environment variable to locate their new classes since AIT is normally installed as a standalone package without checking out the code base. We'll leave it up to the reader to determine what works better for their use cases but we tend to recommend not working out of a code checkout only for extensions.

Creating our Extension
----------------------

Let's create a new class that overrides the default command encoding behavior. For this example we're creating a new module called **newCmd** alongside the core AIT modules.

.. code::

    from ait.core import cmd, log

    class NewCmd(cmd.Cmd):
        def encode(self):
            log.info('We are encoding this command from our custom extension')
            return super(NewCmd, self).encode()

Notice that our **NewCmd** class inherits from the `core Cmd class <https://ait-core.readthedocs.io/en/latest/ait.core.cmd.html#ait.core.cmd.Cmd>`_. All we're changing in this example is the addition of the log message. Next we need to tell AIT to use our custom class instead of the built-in. In our **config.yaml** file we'll add a new section for extensions to do just that.

.. code::

    extensions:
        ait.core.cmd.Cmd: ait.core.newCmd.NewCmd

.. note::

   As mentioned previously, we're keeping the **newCmd** module alongside the core AIT library files for convenience. As such, our custom module path (**ait.core.newCmd.NewCmd**) references AIT core pathing. If we had our **PYTHONPATH** environment variable pointing to a folder containing our custom extensions instead our module path would look different (**newCmd.NewCmd**).

Testing our Extension
---------------------

Let's see if our new extension is working as we expect.

>>> import ait.core.cmd as cmd
<timestamp> | INFO     | Replacing ait.core.cmd.Cmd with custom extension: ait.core.newCmd.NewCmd
>>> cmdDict = cmd.getDefaultDict()
>>> no_op = cmdDict.create('NO_OP')
>>> no_op.encode()
<timestamp> | INFO     | We are encoding this command from our custom extension
...

Looks like it's working as we expect!

What else can we extend?
------------------------

AIT lets you add extensions for any class found in the `core.cmd <https://ait-core.readthedocs.io/en/latest/ait.core.cmd.html>`_, `core.tlm <https://ait-core.readthedocs.io/en/latest/ait.core.tlm.html>`_, `core.evr <https://ait-core.readthedocs.io/en/latest/ait.core.evr.html>`_, `core.limits <https://ait-core.readthedocs.io/en/latest/ait.core.limits.html>`_, and `core.seq <https://ait-core.readthedocs.io/en/latest/ait.core.seq.html>`_ modules.
