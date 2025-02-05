# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
#
# Copyright 2025, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.
import gevent.monkey

gevent.monkey.patch_all()

import datetime
import importlib
import os
import struct

import ait
from ait.core.server import serial
from ait.core import log

import pytest


class Thing(object):
    """
    Common superclass which consists of an int and str field
    """

    def __init__(self, int_arg=0, str_arg=""):
        self.int_arg = int_arg
        self.str_arg = str_arg

    def __eq__(self, other):
        if not isinstance(other, Thing):
            return False

        return self.int_arg == other.int_arg and self.str_arg == other.str_arg


class JsonThing(Thing):
    """
    Json extension
    """

    def __init__(self, int_arg=0, str_arg=""):
        super().__init__(int_arg, str_arg)


class BytesThing(Thing):
    """
    Bytes extension
    """

    def __init__(self, int_arg=0, str_arg=""):
        super().__init__(int_arg, str_arg)


class JsonOnewayThing(Thing):
    """
    Json extension, but only for encode
    """

    def __init__(self, int_arg=0, str_arg=""):
        super().__init__(int_arg, str_arg)


class BytesOnewayThing(Thing):
    """
    Bytes extension
    """

    def __init__(self, int_arg=0, str_arg=""):
        super().__init__(int_arg, str_arg)


class UnregisteredThing(Thing):
    """
    Bytes extension
    """

    def __init__(self, int_arg=0, str_arg=""):
        super().__init__(int_arg, str_arg)


def encode_thing_json(thing):
    """
    Encodes a Thing as JSON dict
    """
    as_dict = {"thing_a": thing.int_arg, "thing_b": thing.str_arg}
    return as_dict


def decode_thing_json(as_json):
    """
    Decodes a JSON dict to JsonThing
    """
    if "thing_a" in as_json and "thing_b" in as_json:
        return JsonThing(as_json["thing_a"], as_json["thing_b"])
    return None


def encode_thing_bytes(thing):
    """
    Encodes a Thing as bytes
    """
    int_val = thing.int_arg
    str_val = thing.str_arg

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


def decode_thing_bytes(as_bytes):
    """
    Decodes bytes to BytesThing
    """
    try:
        # first 4 bytes are the integer
        decoded_integer = struct.unpack(">i", as_bytes[:4])[0]

        decoded_string = as_bytes[4:].decode("utf-8")
        return BytesThing(decoded_integer, decoded_string)

    except struct.error as e:
        print(f"Struct error: {e}")
        return None
    except UnicodeDecodeError as e:
        print(f"Unicode decode error: {e}")
        return None


def test_datetime(serializer):
    """
    Test case for serializing datetime instances
    """
    in_dt = datetime.datetime.now()

    encoded = serializer.serialize(in_dt)

    # test if encoded is bytes?
    assert type(encoded) is bytes

    decoded = serializer.deserialize(encoded)

    assert isinstance(decoded, datetime.datetime)
    assert in_dt == decoded


def test_tuple(serializer):
    """
    Test case for serializing tuples - which are normally returned
    as lists by msgpack without special handling.
    """
    input_tup = (1, 2.3, "hi")

    encoded = serializer.serialize(input_tup)

    # test if encoded is bytes?
    assert encoded is not None

    decoded = serializer.deserialize(encoded)
    assert type(decoded) is tuple
    assert input_tup == decoded

    nested_tup = ("a", 1.21, input_tup)
    encoded = serializer.serialize(nested_tup)
    assert encoded is not None
    assert type(encoded) is bytes

    decoded = serializer.deserialize(encoded)
    assert type(decoded) is tuple
    assert nested_tup == decoded


def test_json(serializer):
    """
    Test case for class that serializes to JSON and deserializes
    back to the original class
    """
    input_obj = JsonThing(121, "Gigawatts")

    encoded = serializer.serialize(input_obj)

    # test if encoded is bytes?
    assert encoded is not None
    assert encoded != input_obj
    assert type(encoded) is bytes

    decoded = serializer.deserialize(encoded)
    assert decoded != encoded
    assert type(decoded) is JsonThing
    assert input_obj == decoded


def test_json_oneway(serializer):
    """
    Test case for class that serializes to JSON but has no
    deserializer
    """
    input_obj = JsonOnewayThing(99, "Bottles of beer on the wall")

    encoded = serializer.serialize(input_obj)
    assert encoded is not None
    assert encoded != input_obj
    assert type(encoded) is bytes

    # decoded should be the 'JSON' dict
    decoded = serializer.deserialize(encoded)
    assert type(decoded) is dict
    assert input_obj != decoded


def test_bytes(serializer):
    """
    Test case for class that serializes to bytes and deserializes
     back to the original class
    """
    input_obj = BytesThing(314, "Pi in the sky")

    encoded = serializer.serialize(input_obj)

    # test if encoded is bytes?
    assert encoded is not None
    assert type(encoded) is bytes

    decoded = serializer.deserialize(encoded)
    assert type(decoded) is BytesThing
    assert input_obj == decoded


def test_bytes_oneway(serializer):
    """
    Test case for class that serializes to bytes but has no
    deserializer
    """
    input_obj = BytesOnewayThing(1001, "Nights")

    encoded = serializer.serialize(input_obj)

    assert encoded is not None
    assert type(encoded) is bytes

    decoded = serializer.deserialize(encoded)
    assert type(decoded) is bytes
    assert input_obj != decoded


def test_unregistered_class_throws_ex(serializer):
    """
    Test case for class that is not registered, so TypeError is
    expected.
    """
    input_obj = UnregisteredThing(101, "Dalmatians")
    with pytest.raises(TypeError):
        encoded = serializer.serialize(input_obj)


def rewrite_and_reload_config(filename, yaml):
    with open(filename, "wt") as out:
        out.write(yaml)

    ait.config.reload(filename=filename)


@pytest.fixture(scope="module")
def serializer():
    """
    This fixture runs once before all tests in the module are executed.
    """

    yaml = """
    default:
        server:
            serialization:
                handlers:
                    - handler:
                        class: tests.ait.core.server.test_serial.JsonThing
                        type: json
                        encode: tests.ait.core.server.test_serial.encode_thing_json
                        decode: tests.ait.core.server.test_serial.decode_thing_json

                    - handler:
                        class: tests.ait.core.server.test_serial.JsonOnewayThing
                        type: json
                        encode: tests.ait.core.server.test_serial.encode_thing_json

                    - handler:
                        class: tests.ait.core.server.test_serial.BytesThing
                        type: bytes
                        encode: tests.ait.core.server.test_serial.encode_thing_bytes
                        decode: tests.ait.core.server.test_serial.decode_thing_bytes

                    - handler:
                        class: tests.ait.core.server.test_serial.BytesOnewayThing
                        type: bytes
                        encode: tests.ait.core.server.test_serial.encode_thing_bytes

    """

    # Setup config
    test_yaml_file = "/tmp/test.yaml"
    rewrite_and_reload_config(test_yaml_file, yaml)

    # Instantiate serializer with config
    our_serial = serial.Serializer()

    # Provide serializer to test functions
    yield our_serial

    # module-level teardown code here
    if os.path.exists(test_yaml_file):
        os.remove(test_yaml_file)
