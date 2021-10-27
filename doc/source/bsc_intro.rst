Binary Stream Capture Introduction
==================================

The Binary Stream Capture (BSC) module provides tools for monitoring and capturing networking traffic and persisting it into PCap files. BSC can monitor  UDP, TCP, and raw Ethernet traffic and is configurable via YAML. BSC also provides a RESTful interface for the manipulation and instantiation of data handlers.

To initialize BSC, run the ``ait-bsc`` utility script::

    $ ait-bsc

If you want to customize BSC before you start it you can do so via a YAML file. By default this config file will be called ``bsc.yaml``. There are two main components of the configuration: The first is the ``capture_manager`` configuration. This sets high level configuration for the system that manages logging tasks as well as the webserver that handles the REST endpoints. The second is ``handler`` configuration which specifies tasks that will log specific connections.

----

Capture Manager Configuration
-----------------------------

The capture manager defaults are fairly sane. However, you will most likely want to adjust the location where log files are saved at the minimum.

.. code-block:: yaml

    capture_manager:
        root_log_directory: /tmp

        manager_server:
            host: localhost
            port: 8080

root_log_directory:
    Specifies the path that should be treated as the root directory for writing log files. Each of the handlers can nest their log data under this directory in customized folders, but all BSC log files will be children of this root folder.

The ``manager_server`` settings are used to control where the RESTful endpoint webserver runs. In general, you'll only need to adjust the ``port`` setting to deal with potential clashes with other services that you may be running.

----

Handler Configuration
---------------------

The handler configuration section allows you to set up one or more handlers to be run when BSC is initialized.

.. code-block:: yaml

    handlers:
        - name: test1
          conn_type: udp
          address: ['', 8500]
          path: additional_dir/test/%j
          file_name_pattern: %Y-%m-%d-randomUDPtestData-{name}.pcap
          rotate_log: True
          rotate_log_index: day
          rotate_log_delta: 1

You only need to provide a few of the available configuration options and BSC will handle the remaining options.

name:
    A unique name for the capture handler.

conn_type:
    The type of connection that the handler should make to the specified address. This can be one of **udp**, **tcp**, or **ethernet** for reading raw ethernet frames.

address:
    The address to which the handler should attempt to connect and monitor. The value for *conn_type* affects the format that you'll specify here. For a **upd** handler the address will be of the form ``['', <port number]``. For a **tcp** handler the address will be of the form ``[<host>, <port>]``. For an **ethernet** handler the address will be of the form ``[<ethernet interface name>, <protocol number]``.

If you want additional customization options you can also customize the path and file name for the output PCap file, specify whether the log file should be rotated and with what frequency, and set custom pre-write data manipulations to run on a handler.

rotate_log (optional):
    Set this to ``True`` if you want the log to be rotated.

rotate_log_index (optional):
    If *rotate_log* is set to ``True`` this controls the time frame of log rotations. By default this is set to ``day``. You can look at the :class:`ait.core.bsc.SocketStreamCapturer` documentation for a list of valid options.

rotate_log_delta (optional):
    If *rotate_log* is ``True``, this controls the *rotate_log_index* delta between the current time at log rotation check versus the time the log file was open necessary to trigger a rotation. This defaults to ``1``.

path (optional):
    Additional nesting path information that will be applied to the Capture Managers root log directory value when writing a log file for this handler. If you have a custom nesting for your log files you can use this attribute to help achieve that. The final path that is created is run through ``strftime`` and ``format`` with the handler's metadata as the parameters so you can customize as you see appropriate.

file_name_pattern (optional):
    A custom file name pattern to use for this handler. Note that the final log file path is run through ``strftime`` and ``format`` with the handler's metadata as the parameters.

pre_write_transforms (optional):
    A list of **callables** that should be run on this handler's data prior to write.

    .. note::

        At the moment you can only specify functions that are global to the ``ait.core.bsc`` module. This will be changed in the future.

----

REST API
--------

The BSC service provides REST services for starting, stopping, and manipulating capture handlers.

.. http:get:: /

   Returns a JSON object containing the configuration information for all active capture handlers. The configuration is grouped by address.

   **Example Request**:

   .. code-block:: bash

      curl http://localhost:8080/

   **Example Response**:

   .. code-block:: javascript

      {
          ['', 8500]: [
              {
                  conn_type: "udp",
                  handler: {
                      pre_write_transforms: [],
                      file_name_pattern: "%Y-%m-%d-randomUDPtestData-{name}.pcap",
                      rotate_log: true,
                      name: "test1",
                      log_dir: "/tmp/additional_dir/test/%j"
                  },
                  log_file_path: "/tmp/additional_dir/test/211/2016-07-29-randomUDPtestData-test1.pcap",
                  address: ["", 8500]
              },
              {
                  conn_type: "udp",
                  handler: {
                      pre_write_transforms: [],
                      rotate_log: true,
                      name: "test2",
                      log_dir: "/tmp"
                  },
                  log_file_path: "/tmp/2016-07-29-19-42-17-test2.pcap",
                  address: ["", 8500]
              }
          ],
          ['', 8125]: [
              {
                  conn_type: "udp",
                  handler: {
                      pre_write_transforms: [],
                      rotate_log: true,
                      name: "test3",
                      log_dir: "/tmp"
                  },
                  log_file_path: "/tmp/2016-07-29-19-42-17-test3.pcap",
                  address: ["", 8125]
              }
          ]
      }

.. http:get:: /stats

   Return capture stats for all handlers.

   **Example Request**:

   .. code-block:: bash

      curl http://localhost:8080/stats

   **Example Response**:

   .. code-block:: javascript

      {
          ['', 8500]: [
              {
                  approx_data_rate: "0.0 bytes/second",
                  reads: 0,
                  name: "test1",
                  data_read_length: "0 bytes"
              },
              {
                  approx_data_rate: "0.0 bytes/second",
                  reads: 0,
                  name: "test2",
                  data_read_length: "0 bytes"
              }
          ],
          ['', 8125]: [
              {
                  approx_data_rate: "1.66666666667 bytes/second",
                  reads: 1,
                  name: "test3",
                  data_read_length: "5 bytes"
              }
          ]
      }

   .. note::

      The approximate data is calculated using the last log rotation time compared to the current time. As such it is not accurate if the hanlder isn't reading data regularly.

.. http:post:: /<name>/start

   Create a new handler called *name*.

   **Handler Attributes**:

   See the `Handler Configuration`_ section for details on what can be included here. Note that the *address* field is split into two components (loc and port) for the REST service. The below options are required for proper functionality!

   port:
       The port/protocol for the connection.

   conn_type:
       The type of connection the handler will make. One of *udp*, *ethernet*, or *tcp*.

   **Example Post Data**:

   .. code-block:: javascript

      {
         'loc': '',
         'port': 8125,
         'conn_type': 'udp'
      }

   **Example Request**:

   .. code-block:: bash

      curl --form "port=8125" --form "conn_type=udp" http://localhost:8080/mytesthandler/start

.. http:delete:: /<name>/stop

   Stop all handlers that match a given *name*.

   **Example Request**:

   .. code-block:: bash

      curl -X DELETE http://localhost:8080/mytesthandler/stop

   .. warning::

      There isn't a requirement that handlers have unique names. As such, if multiple handlers have the same name they will all be terminated!

.. http:get:: /<name>/config

   Returns a configuration dictionary for handlers with a given *name*.

   **Example Request**:

   .. code-block:: bash

      curl http://localhost:8080/mytesthandler/config

   **Example Response**:

   .. code-block:: javascript

      [
          {
              conn_type: "udp",
              handler: {
                  pre_write_transforms: [],
                  file_name_pattern: "%Y-%m-%d-randomUDPtestData-{name}.pcap",
                  rotate_log: true,
                  name: "mytesthandler",
                  log_dir: "/tmp/additional_dir/test/%j"
              },
              log_file_path: "/tmp/additional_dir/test/211/2016-07-29-randomUDPtestData-test1.pcap",
              address: ["", 8500]
          }
      ]

   .. note::

      There isn't a requirement that handlers have unique names. As such, if multiple handlers have the same name you will receive muliple handler's configuration dictionaries.

.. http:POST:: /<name>/rotate

   Trigger log rotation for a given handler name.

   **Example Request**:

   .. code-block:: bash

      curl -X POST http://localhost:8080/mytesthandler/rotate

   .. warning::

      Note that if the file name pattern provided isn't sufficient for a rotation to occur with a new unique file name you will not see a log rotation . Be sure to timestamp your files in such a way to ensure that this isn't the case! The default file name pattern includes year, month, day, hours, minutes, and seconds to make sure this works as expected.

----

Convenience Scripts
-------------------

Create Handler
^^^^^^^^^^^^^^

The **ait-bsc-create-handler** bin script provides a wrapper around the BSC REST endpoint for creating a log handler. It requires a name for the new handler, a hostname/interface name, port/protocol number, and the connection time (one of 'udp', 'tcp', or 'ethernet').

**Example:**

.. code-block:: bash

   ait-bsc-create-handler new_handler '' 8123 udp

Stop Handler
^^^^^^^^^^^^

The **ait-bsc-stop-handler** bin script provides a wrapper around the BSC REST endpoint for stopping a log handler. It requires the handlers name that you wish to stop.

**Example:**

.. code-block:: bash

   ait-bsc-stop-handler new_handler
