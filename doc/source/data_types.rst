AIT Data Types
==============

AIT provides a number of built in data types and functionality for extending the toolkit with your own custom types. The default data types provided aim to cover the majority of the basic types you would expect to find in a packet of data. These so-called **Primitive Types** are all built on top of `ait.core.dtype.PrimitiveType`. More complicated type fields can be built on top of `PrimitiveType` by inheriting from it and implementing custom encode and decode functionality. Types such as `ait.core.dtype.CMD16` do exactly this.

Built-in Types
--------------

AIT provides a variety of primitive types that cover the many of fields encountered in data packets. These are defined in **ait.core.dtype.PrimitiveTypes**.

.. code-block:: python

   [
        'I8',
        'LSB_D64',
        'LSB_F32',
        'LSB_I16',
        'LSB_I32',
        'LSB_I64',
        'LSB_U16',
        'LSB_U32',
        'LSB_U64',
        'MSB_D64',
        'MSB_F32',
        'MSB_I16',
        'MSB_I32',
        'MSB_I64',
        'MSB_U16',
        'MSB_U32',
        'MSB_U64',
        'U8'
   ]

AIT also provides some **Complex Types** that are built on top of various primitive types. The default types provided tie in with AIT's Command and EVR types as well as some CCSDS time formats.

.. code-block:: python

   [
        'CMD16',
        'EVR16',
        'TIME8',
        'TIME32',
        'TIME40',
        'TIME64'
   ]

Custom Types
------------

If the default AIT types aren't meeting your needs you can define custom types and integrate them with the toolkit via the :doc:`Extensions <extensions>` mechanism.

Consider the following example which creates a custom 24-bit MSB type.

.. code-block:: python

   from typing import Optional

   from ait.core import dtype

   class MyCustomTypes(dtype.CustomTypes):
       def get(self, typename: str) -> Optional[dtype.PrimitiveType]:
            if typename == 'My24BitMSB':
               return My24BitMSB()

           return None


   class My24BitMSB(dtype.PrimitiveType):
       def __init__(self):
           # Current implementation requires that you pass a valid type here
           # even if it's not accurate. Manually overwrite stuff after the call
           # so it's correct. I.e., this isn't actually an MSB_U32!
           super(My24BitMSB, self).__init__('MSB_U32')
           self._nbits = 24
           self._nbytes = 3

       def encode(self, value: int):
           return (value & 0xFFFFFF).to_bytes(3, byteorder='big')

       def decode(self, bytes, raw=False):
           return int.from_bytes(bytes[:3], byteorder='big')

To add a custom type you must extend **dtype.CustomTypes** with your own implementation and return an instance of your custom types. The above would be added as extension by placing the following in your **config.yaml** file. As always with extensions, the module containing the relevant class must be findable by Python.

.. code-block:: yaml

   default:
       extensions:
          ait.core.dtype.CustomTypes: yourmodule.MyCustomTypes
