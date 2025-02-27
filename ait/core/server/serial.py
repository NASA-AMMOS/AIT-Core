import datetime
import enum
import importlib
import inspect
import traceback

import msgpack  # type: ignore
from msgpack.exceptions import ExtraData  # type: ignore
from msgpack.exceptions import FormatError  # type: ignore
from msgpack.exceptions import StackError  # type: ignore

import ait
from ait.core import log


class EncodingType(enum.Enum):
    """
    Enum for encoding type: JSON, BYTES
    """

    JSON = enum.auto()
    BYTES = enum.auto()

    @classmethod
    def value_of(cls, str_value, default):
        """
        Class method that returns a Type enum based on string value.

        Params:
            value: Name associated with the enum
            default: Default value to be returned, can be None

        Returns:
            plugin.Type - Type enum instance
        """
        if str_value:
            for k, v in cls.__members__.items():
                if k.lower() == str_value.lower():
                    return v
        if default:
            return default
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{str_value}'")


class Utils(object):
    @staticmethod
    def chain_functions_until_value_changes(functions, init_val):
        """
        Chains a list of functions which take a value and
        return a result.  While the result matches the input
        value, the next function in the list will be invoked.
        When the result differs from the input, then that result
        is returned.
        If no change in result after all functions, the original
        value is returned.
        """
        for function in functions:
            result = function(init_val)
            if result != init_val:
                return result
        return init_val

    @staticmethod
    def get_full_classname(obj):
        """
        Returns the full classname associated with an object,
        with a special check for builtins.
        """
        clz = obj.__class__
        clz_mod = clz.__module__
        clz_name = clz.__name__
        if clz_mod is None or clz_mod == str.__class__.__module__:
            return clz_name
        return clz_mod + "." + clz_name

    @staticmethod
    def get_function(full_func_name):
        """
        Given a string indicating a module/class function,
        attempts to locate that function and return it.
        Else None is returned
        """

        # We expect at least one period in the string
        if "." not in full_func_name:
            return None

        rval_func = None
        module_name, *remaining = full_func_name.split(".")
        try:
            module_ = importlib.import_module(module_name)
            parent = module_
            child = module_

            # Crawl down the parts
            for step in remaining:
                parent = child
                if hasattr(parent, step):
                    child = getattr(parent, step)
                else:
                    child = None
                    break

            if child is not None:
                # Check that parent is a module or class
                # and the value is a method or function
                if (inspect.ismodule(parent) or inspect.isclass(parent)) and (
                    inspect.ismethod(child) or inspect.isfunction(child)
                ):
                    rval_func = child
        except (ImportError, AttributeError) as ex:
            log.error(f"Unable to locate function for '{full_func_name}': {ex}")
            log.error(traceback.format_exc())

        return rval_func


class SerialEntry(object):
    """
    Structure consisting of classname, encoding type, serializer and
    deserializer functions
    """

    # Special IDs that have default handling
    TYPE_ID_TUPLE = 1
    TYPE_ID_DATETIME = 2

    # Incrementing id counter
    unique_type_id_counter = 3

    def __init__(self, classname, enc_type, serializer: None, deserializer: None):
        """
        Constructor

        Params:
            classname: class name for the object
            enc_type: Encoding_Type enum value
            serializer: Serializer function, can be None
            deserializer: Deserializer function, can be None
            classname: serial configuration as read by ait.config

        Raises:
            ValueError:   if any of the required config values are missing
        """
        if classname is None or not classname:
            raise ValueError("classname cannot be None")
        if enc_type is None:
            raise ValueError("enc_type cannot be None")
        if not isinstance(enc_type, EncodingType):
            raise ValueError("enc_type must be of type EncodingType")

        self.classname = classname
        self.enc_type = enc_type
        self.serializer = serializer
        self.deserializer = deserializer
        self.id = SerialEntry.assign_id()

    @classmethod
    def assign_id(cls):
        new_id = cls.unique_type_id_counter
        cls.unique_type_id_counter += 1
        return new_id


class SerialRegistry(dict):
    """
    Registry of serial struct entry, mapping from classname
    and entry id to the struct
    """

    def __init__(self):
        dict.__init__(self)

    # Add serial entry to this registry.  Both the classname and id
    # associated with the entry will be lookup keys
    def add(self, entry):
        string_key = entry.classname
        numeric_key = entry.id
        if string_key and numeric_key:
            # Probably not needed but we want consistency across keys
            if string_key in self:
                raise ValueError(f"Duplicate string key found for {string_key}")
            if numeric_key in self:
                raise ValueError(f"Duplicate numeric key found for {numeric_key}")

            self[string_key] = entry
            self[numeric_key] = entry

    # Return a list of registered classnames
    def get_classnames(self):
        return [key for key in self.keys() if isinstance(key, str)]

    # Return a list of registered type ids
    def get_ids(self):
        return [key for key in self.keys() if isinstance(key, int)]


class SerialRegistryLoader(object):
    """
    Loads the serial registry from the AIT config YAML

    Format of config section:

    ait.server.serialization.handlers:
        - handler:
            class: full_class_name
            type: {json,bytes}
            encode: module(.class).function
            decode: module(.class).function
    """

    @staticmethod
    def load_registry():
        """
        Reads, parses and creates serial handlers specified in config.yaml.

        Handlers missing required fields will not be instantiated.
        """

        # Create initial empty registry
        registry = SerialRegistry()

        # Search for relevant config section
        handlers = ait.config.get("server.serialization.handlers", None)

        if handlers is not None:
            for index, handler in enumerate(handlers):
                handler_info = handler["handler"]
                try:
                    # Try to create new handler
                    handler = SerialRegistryLoader._create_handler(handler_info)

                    # If successful, add to the registry
                    if handler is not None:
                        registry.add(handler)
                except ValueError as ve:
                    log.error(
                        "Error occurred while creating serialization "
                        f"handler at index {index}: {ve}"
                    )
                    log.error(f"Handler config: {handler_info}")

        return registry

    @staticmethod
    def _create_handler(handler_dict):
        """
        Creates a SerialEntry config from AIT config.

        Params:
            record_dict: serial configuration as read by ait.config
        Returns:
            record:       a SerialEntry instance
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if handler_dict is None:
            raise ValueError("No serialization handler config.")

        if "class" not in handler_dict:
            raise ValueError("Serialization handler config missing 'class'")
        class_name = handler_dict["class"]

        if "type" not in handler_dict:
            raise ValueError(f"Serialization handler for '{class_name}' missing 'type'")
        type_name = handler_dict["type"]

        enc_type = EncodingType.value_of(type_name, None)
        if type is None:
            raise ValueError(
                f"Serialization handler for '{class_name}' has "
                f"unknown config type '{type_name}'.  Legal "
                "values are: json,bytes"
            )

        enc_func = None
        dec_func = None

        # Try to load encoder function if specified
        if "encode" in handler_dict:
            enc_func_name = handler_dict["encode"]
            try:
                enc_func = Utils.get_function(enc_func_name)
            except Exception:
                log.error(traceback.format_exc())

            if enc_func is None:
                msg = (
                    f"Unable to load encoder function '{enc_func_name}' "
                    f"for type '{class_name}'"
                )
                raise ValueError(msg)

        # Try to load decoder function if specified
        if "decode" in handler_dict:
            dec_func_name = handler_dict["decode"]
            try:
                dec_func = Utils.get_function(dec_func_name)
            except Exception:
                log.error(traceback.format_exc())

            if dec_func is None:
                msg = (
                    f"Unable to load decoder function '{dec_func_name}' "
                    f"for type '{class_name}'"
                )
                raise ValueError(msg)

        # Construct entry instance
        entry = SerialEntry(class_name, enc_type, enc_func, dec_func)

        return entry


class SerialHooks(object):
    KEY_SERIALIZE_ID = "__ait_serial_id__"
    KEY_AS_JSON = "__ait_as_json__"

    KEY_CLASSNAME = "__ait_classname__"

    # If we want to hack around Pickle-method __reduce__()?
    KEY_CONST_NAME = "__ait_constructor__"
    KEY_CONST_ARGS = "__ait_construction_args__"

    def __init__(self, serial_registry):
        self._registry = serial_registry

    @staticmethod
    def encode_datetime_exttype(dt):
        if isinstance(dt, datetime.datetime):
            return msgpack.ExtType(
                SerialEntry.TYPE_ID_DATETIME,
                dt.isoformat(timespec="microseconds").encode(),
            )
        return None

    @staticmethod
    def decode_datetime_exttype(data):
        return datetime.datetime.fromisoformat(data.decode())

    @staticmethod
    def encode_tuple_exttype(tup, enc_func):
        if isinstance(tup, tuple):
            packed = msgpack.packb(
                list(tup), strict_types=True, use_bin_type=True, default=enc_func
            )
            return msgpack.ExtType(SerialEntry.TYPE_ID_TUPLE, packed)
        return None

    @staticmethod
    def decode_tuple_exttype(data, ext_func, obj_func):
        return tuple(
            msgpack.unpackb(data, raw=False, ext_hook=ext_func, object_hook=obj_func)
        )

    def encode_entry_point(self, obj):
        """
        Encode an object for serialization

        If the object's class has been registered in the config
        YAML serial section with a serializer function, then that
        function will be called foe encoding. If the mapping is of
        encoding type JSON, then a specialize JSON dict with encoded
        result is returned.
        If the encoding is BYTES, then the encoded result is wrapped
        in a msgpack ExtType.

        If nothing is registered, then the object is checked for a toJSON()
        method.  If found, then the result of that method will be returned.

        There is special handling for tuple and datetime to preserve those.
        """

        # By default, encoded is the same as original object
        encoded = obj

        if isinstance(obj, datetime.datetime):
            encoded = self.encode_datetime_exttype(obj)
        elif isinstance(obj, tuple):
            # Need to pass this method to handle nested objects
            encoded = self.encode_tuple_exttype(obj, self.encode_entry_point)
        else:
            # lookup registry via full classname
            full_classname = Utils.get_full_classname(obj)

            record = self._registry.get(full_classname)

            # Check if explicit mapping provided
            if record and record.serializer:
                if record.enc_type == EncodingType.BYTES:
                    # encoded contains ExtType with binary data
                    encoded = self.encode_registry_ext_bytes(record.id, obj)
                elif record.enc_type == EncodingType.JSON:
                    # encoded is Json dict with json data
                    serialized = record.serializer(obj)
                    encoded = {
                        SerialHooks.KEY_SERIALIZE_ID: record.id,
                        SerialHooks.KEY_AS_JSON: serialized,
                    }
            elif hasattr(obj, "toJSON") and callable(obj.toJSON):
                # One-way serialization?
                # encoded is Json with no way of mapping back to object
                encoded = obj.toJSON()

            # Todo (maybe?)
            # Check if Pickle-related functions are found?
            # elif hasattr(obj, '__reduce__') and callable(obj, '__reduce__'):
            #    # Leverage pre-existing Pickling behavior
            #    (obj_class, obj_tup) = obj.__reduce__()
            #    ...

        return encoded

    def encode_registry_ext_bytes(self, code, obj):
        """
        Encode an ext type, where code and data are provided directly.
        This will usually be called by the encode_entry method
        """

        encoded = obj
        serial_entry = self._registry.get(code)

        # Check if explicit mapping provided
        if not serial_entry:
            raise ValueError(
                f"The is no entry registered serialization handler for code {code}"
            )

        if serial_entry.serializer:
            if serial_entry.enc_type != EncodingType.BYTES:
                raise ValueError(
                    "Cannot serialize entry as ExtType, encoding type is not bytes"
                )
            serialized = serial_entry.serializer(obj)

            encoded = msgpack.ExtType(code, serialized)
            return encoded
        return None

    def decode_entry_point(self, obj):
        """
        Decode an encoded object for deserialization

        If object is ExtType, then the ExtType's type value is
        used for the registry lookup.
        If object is a dictionary containing special AIT keys,
        then those will drive the decoding process.
        """

        # By default, the original object is returned
        decoded = obj

        if isinstance(obj, msgpack.ExtType):
            # Forward to the ext type decoder
            decoded = self.decode_exttype(obj.code, obj.data)
        elif (
            isinstance(obj, dict)
            and SerialHooks.KEY_SERIALIZE_ID in obj
            and SerialHooks.KEY_AS_JSON in obj
        ):
            # Use registry to decode JSON to object
            serial_id = obj[SerialHooks.KEY_SERIALIZE_ID]
            encoded_as_json = obj[SerialHooks.KEY_AS_JSON]
            serial_entry = self._registry.get(serial_id)
            if serial_entry:
                if serial_entry.enc_type != EncodingType.JSON:
                    raise ValueError(
                        "Can only decode JSON type, but serial "
                        f"entry type is '{serial_entry.enc_type}'"
                    )
                if serial_entry.deserializer:
                    try:
                        decoded = serial_entry.deserializer(encoded_as_json)
                    except Exception as ex:
                        raise ValueError(f"Unable to decode data: {ex}")
        return decoded

    def decode_exttype(self, code, data):
        """
        Decodes ext type, with special cases for datetime and
        tuples.  Otherwise, the serialization registry is used
        """
        if code == SerialEntry.TYPE_ID_DATETIME:
            return self.decode_datetime_exttype(data)
        elif code == SerialEntry.TYPE_ID_TUPLE:
            return self.decode_tuple_exttype(
                data, self.decode_exttype, self.decode_entry_point
            )
        else:
            return self.decode_registry_ext_bytes(code, data)

    def decode_registry_ext_bytes(self, code, data):
        """
        Decode an ext type, where code and data are provided directly.

        This can either be called by decode_entry, but will most likely
        be invoked by msgpack

        Params:
            code:   (required) Specifies exttype id
            data:   (required) Data to be decoded/deserialized
        Raises:
            ValueError:  If data type mismatch or deserialization error
        """
        decoded = data
        serial_entry = self._registry.get(code)
        if serial_entry:
            if serial_entry.enc_type != EncodingType.BYTES:
                raise ValueError(
                    "Can only decode bytes type, but serial "
                    f"entry type is '{serial_entry.enc_type}'"
                )
            if serial_entry.deserializer:
                try:
                    decoded = serial_entry.deserializer(data)
                except Exception as ex:
                    raise ValueError(f"Unable to decode data: {ex}")
            else:
                pass  # This is when class serializes one-way
        else:
            raise ValueError(f"Cannot decode unrecognized ext-type id '{code}'")
        return decoded


class Serializer:
    def __init__(self):
        # Load the serial registry
        self.registry = SerialRegistryLoader.load_registry()

        # only print if non-zero
        if len(self.registry) > 0:
            log.info(f"Serialization registry size: {len(self.registry)}")

        # Create Hooks instance which handles the extra magic
        self.hooks = SerialHooks(self.registry)

    def serialize(self, obj):
        """
        Serializes obj
        If successful, a serialized form will be returned.
        Otherwise, None will be returned.
        """
        packed = None
        try:
            packed = msgpack.packb(
                obj, default=self.hooks.encode_entry_point, strict_types=True
            )
        except (ValueError, ExtraData, FormatError, StackError):
            log.info("Unable to serialize data")
            log.debug(f"Data: {obj}")
        return packed

    def deserialize(self, obj):
        """
        Deserializes the serialized data.
        If successful, an object will be returned, else the original.
        """
        unpacked = obj
        try:
            # Call msgpack, passing the object hook and ext hook to handle
            # the various types
            unpacked = msgpack.unpackb(
                obj,
                object_hook=self.hooks.decode_entry_point,
                ext_hook=self.hooks.decode_exttype,
            )
        except (ValueError, ExtraData, FormatError, StackError) as err:
            log.info(f"Unable to deserialize data.  Error: {err}")
            log.debug(f"Data: {obj}")
        return unpacked
