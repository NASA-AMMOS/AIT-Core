AIT Server Serialization
========================

Serialization
-------------

Generally, serialization is the process of converting data structures (objects, arrays, primitives, etc.) into a format suitable for transmission or storage.

The AIT server uses ZeroMQ_ (0MQ), a high-performance asynchronous messaging library, to pass serialized messages between streams, handlers and plugins.
While 0MQ primarily deals with the transport of messages as raw bytes, it does not provide built-in serialization mechanisms.

Earlier versions of AIT leveraged Python's built-in Pickle_ library to perform serialization of messages.
While Pickle is convenient, it also carries significant security risks, mainly possible arbitrary code execution.

As a result, Pickle was replaced with MessagePack_, a binary-based format designed for high performance and compact size.
MessagePack aims to be as fast as JSON but more compact, making it suitable for efficient data exchange.

For Python, MessagePack primarily focuses on serializing basic Python data types like integers, floats, strings, booleans, lists, dictionaries and None.
AIT extends support to also include tuples and datetimes (without timezones).

In the case of arbitrary classes, however, MessagePack provides no built-in support.
As such, AIT provides a mechanism to support arbitrary classes as needed by projects.
The approach extends the AIT server configuration to include mappings of specific classes to serialization and deserialization functions.
For each class, the serialized format can be either raw bytes or a JSON structure of supported primitives.


.. code-block:: none

    server:
        ...
        serialization:
            handlers:
                - handler:
                    class: <package>.<module>.<ClassName>
                    type: json|bytes
                    encode: <package>.<module>(.class).<function>
                    decode: <package>.<module>(.class).<function>


The encode function should accept a single argument of a class instance and return an object as indicated by ``type`` value.

The decode function should accept a single argument indicated by ``type``, and return a class instance if successful, else None.

Examples
--------

This section provides some quick examples for serializing classes via json and bytes.

JSON
^^^^

Below is the definition of a simple class containing an int and string field.
For this example, we assume the class is defined in a source file named 'message.py' under the 'example' package.


.. code-block:: none

    class StructJ(object):

        def __init__(self, int_arg=0, str_arg=''):
            self.int_arg = int_arg
            self.str_arg = str_arg


In the same file are two functions, one which serializes and the other which deserializes.


.. code-block:: none

    def encode_json_struct(structj):
        """
        Encodes as JSON dict
        """
        as_dict = { 'a': structj.int_arg, 'b': structj.str_arg }
        return as_dict


    def decode_json_struct(as_json):
        """
        Decodes a JSON dict to StructJ
        """
        if 'a' in as_json and 'b' in as_json:
            return StructJ(as_json['a'], as_json['b'])
        return None


The AIT configuration YAML would be updated to include a *'serialization'* section under the *'server'* tag, with handler for StructJ:

.. code-block:: none

    default:
        server:
            ...
            serialization:
                handlers:
                    - handler:
                        class: example.message.StructJ
                        type: json
                        encode: example.message.encode_json_struct
                        decode: example.message.decode_json_struct


Bytes
^^^^^

The next example closely mirrors the JSON case, but serializes to and from bytes.

.. code-block:: none

    class StructB(object):

        def __init__(self, int_arg=0, str_arg=''):
            self.int_arg = int_arg
            self.str_arg = str_arg

Note that StructB is identical to the previous StructJ, but has a different name to separate the handler mapping in the config.
What this entails is that for a given class, at most one handler can be registered, either of type 'bytes' or 'json'.

In the same file are two functions, one which serializes and the other which deserializes, but this time with bytes.

.. code-block:: none

    def encode_struct_bytes(structb):
        """
        Encodes a StructB as bytes
        """
        int_val = structb.int_arg
        str_val = structb.str_arg

        try:
            # Encode the integer using struct (for consistent byte representation)
            int_bytes = struct.pack(">i", int_val)  # ">i" for big-endian integer

            # Encode the string to UTF-8 bytes
            str_bytes = str_val.encode("utf-8")

            # Combine the encoded bytes
            combined_bytes = int_bytes + str_bytes
            return combined_bytes

        except struct.error as e:
            print(f"Struct error: {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"Unicode decode error: {e}")
            return None


    def decode_struct_bytes(as_bytes):
        """
        Decodes bytes to StructB
        """
        try:
            decoded_integer = struct.unpack(">i", as_bytes[:4])[0]  # first 4 bytes are the integer
            decoded_string = as_bytes[4:].decode("utf-8")
            return StructB(decoded_integer, decoded_string)
        except struct.error as se:
            print(f"Struct error: {se}")
            return None
        except UnicodeDecodeError as ude:
            print(f"Unicode decode error: {ude}")
            return None

The AIT configuration YAML would be updated to include a *'serialization'* section under the *'server'* tag, with handler for StructB:

.. code-block:: none

    default:
        server:
            ...
            serialization:
                handlers:
                    - handler:
                        class: example.message.StructB
                        type: bytes
                        encode: example.message.encode_struct_bytes
                        decode: example.message.decode_struct_bytes


Final Notes
-----------

For most standard situations, the default AIT serialization framework, without any special class-handling, should be sufficient.

It is mainly for projects which require passing messages using specific classes that need to be concerned about the handlers.


.. _MessagePack: https://github.com/msgpack/msgpack-python

.. _Pickle: https://docs.python.org/3/library/pickle.html

.. _ZeroMQ: https://github.com/zeromq/pyzmq
