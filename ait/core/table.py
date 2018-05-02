# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2014, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
AIT Table Converter

The ait.core.table module provides the dictionary for translating tables.
"""

import cPickle
import os
import yaml
import struct
import binascii
import array
import hashlib

from ait.core import dtype, log, util


class FSWColDefn (object):
    """FSWColDefn - Argument Definition

    Argument Definitions encapsulate all information required to define
    a single column.  This includes the column name, its
    description, units, type, byte position within a command, name-value
    enumerations, and allowed value ranges.  Name, type, and byte
    position are required.  All others are optional.
    """
    __slots__ = [
        "name", "_format", "_type", "_units", "_items", "_enum", "_bytes"
    ]

    def __init__ (self, *args, **kwargs):
        """Creates a new Column Definition.
        """
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))


    def __repr__ (self):
        return util.toRepr(self)

    @property
    def enum(self):
        """The argument enumeration."""
        return self._enum

    @enum.setter
    def enum(self, value):
        self._enum = None
        if value is not None:
            self._enum = value

    @property
    def values (self):
        """The argument values."""
        return self._values

    @values.setter
    def values (self, value):
        self._values = value if value is not None else { }

    @property
    def format (self):
        """The argument format."""
        return self._format

    @format.setter
    def format (self, value):
        self._format = value if value is not None else ''

    @property
    def type (self):
        """The argument type."""
        return self._type

    @type.setter
    def type (self, value):
        self._type = value if value is not None else ''

    @property
    def items (self):
        """The argument items."""
        return self._items

    @items.setter
    def items (self, value):
        self._items = None
        if value is not None:
            self._items = value

    @property
    def units (self):
        """The argument units.
        """
        return self._units

    @units.setter
    def units (self, value):
        self._units = value if value is not None else ''

    @property
    def bytes (self):
        """The argument bytes."""
        return self._bytes

    @bytes.setter
    def bytes (self, value):
        self._bytes = None
        if value is not None:
            self._bytes = value



class FSWTab (object):
    """Table object that contains column definitions

    Commands reference their Command Definition and may contain arguments.
    """
    def __init__ (self, defn, *args):
        """Creates a new Command based on the given command definition
        and command arguments.
        """
        self.defn = defn
        self.args = args


    def __repr__ (self):
        return self.defn.name + " " + " ".join([str(a) for a in self.args])

    @property
    def coldefns (self):
        """The table column definitions."""
        return self.defn.coldefns

    @property
    def fswheaderdefns (self):
        """The table fsw header definitions."""
        return self.defn.fswheaderdefns


def hash_file(filename):
   """"This function returns the SHA-1 hash
   of the file passed into it"""

   # make a hash object
   h = hashlib.sha1()

   # open file for reading in binary mode
   with open(filename,'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)

   # return the hex representation of digest
   return h.hexdigest()


class FSWTabDefn (object):
    """Table Definition

    FSW Table Definitions encapsulate all information required to define a
    single column.  This includes the column name, its opcode,
    subsystem, description and a list of argument definitions.  Name and
    opcode are required.  All others are optional.
    """
    __slots__ = ["name", "delimiter", "uptype", "size", "rows", "fswheaderdefns", "coldefns"]

    MagicNumber = 0x0c03

    def __init__ (self, *args, **kwargs):
        """Creates a new Command Definition."""
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, kwargs.get(name, None))

        if self.fswheaderdefns is None:
            self.fswheaderdefns = [ ]

        if self.coldefns is None:
            self.coldefns = [ ]


    def __repr__ (self):
        return util.toRepr(self)

    def toText(self, stream, fswtab_f, verbose, version):
        out = ""

        size = os.path.getsize(stream.name)
        #print "table name: " + self.name
        #print "stream len: " + str(size)

        noentries = 0
        if self.name != "memory":
            for fswheaderdef in enumerate(self.fswheaderdefns):
                #print "header definition: " + str(fswheaderdef[1])
                fswcoldefn = fswheaderdef[1]
                name = fswcoldefn.name
                #print "name: " + name
                colfmt = str(fswcoldefn.format)
                #print "format: " + colfmt
                colpk = dtype.get(fswcoldefn.type)
                #print "packing: " + str(colpk)
                coltype = fswcoldefn.type
                #print "type: " + coltype
                if isinstance(fswcoldefn.bytes,list):
                   nobytes = fswcoldefn.bytes[1] - fswcoldefn.bytes[0] + 1
                else:
                   nobytes = 1
                #print "bytes: " + str(fswcoldefn.bytes)
                #print "nobytes: " + str(nobytes)

                strval = ""
                if str(colpk) == "PrimitiveType('U8')" and nobytes>1:
                    strval = ""
                    for i in range(nobytes):
                        value = colpk.decode(stream.read(1))
                        strval += str(colfmt % value)
                        #print(colfmt % value)
                else:
                    value = colpk.decode(stream.read(nobytes))
                    #print(colfmt % value)
                if (str(colpk) != "PrimitiveType('U8')") or (str(colpk) == "PrimitiveType('U8')" and nobytes == 1):
                    strval = str(colfmt % value)
                    #print "strval: " + strval
                if name == "NUMBER_ENTRIES":
                    noentries = strval
                    #print "noentries: " + strval
                if self.name != "keep_out_zones" and self.name != "line_of_sight":
                    # Append the value to table row
                    out += name+': %s\n'     % strval

            if verbose is not None and verbose != 0:
               print
               print out
               #fswtab_f.write(out)

            size = size - 32

        out = ""

        if self.name.startswith("log_"):
            norows = self.rows
            #print "norows: " + str(norows)
        else:
            rowbytes = 0
            items = None
            for coldef in enumerate(self.coldefns):
                fswcoldefn = coldef[1]
                items = fswcoldefn.items
                if isinstance(fswcoldefn.bytes,list):
                   nobytes = fswcoldefn.bytes[1] - fswcoldefn.bytes[0] + 1
                else:
                   nobytes = 1
                rowbytes = rowbytes + nobytes
            #print "Row bytes: " + str(rowbytes)
            if items is not None:
                rowbytes = rowbytes * items
                norows = size / rowbytes
            else:
                norows = int(noentries)

            #print "norows: " + str(norows)
            #print "items: " + str(items)

        if norows == 0:
           idx = 1
           for i in range(size):
               byte = stream.read(1)
               value = binascii.hexlify(byte)
               fswtab_f.write(value)
               if (idx%2) == 0:
                   fswtab_f.write(" ")
               if (idx%16) == 0:
                   fswtab_f.write("\n")
               idx += 1
           return

        for i in range(norows):
           condition = None
           #this is how to step into table definitions
           for coldef in enumerate(self.coldefns):
               #print "column definition: " + str(coldef[1])
               fswcoldefn = coldef[1]
               name = fswcoldefn.name
               #print "name: " + name
               colfmt = str(fswcoldefn.format)
               #print "format: " + colfmt
               colpk = dtype.get(fswcoldefn.type)
               #print "packing: " + str(colpk)
               coltype = fswcoldefn.type
               #print "type: " + coltype
               if isinstance(fswcoldefn.bytes,list):
                  nobytes = fswcoldefn.bytes[1] - fswcoldefn.bytes[0] + 1
               else:
                  nobytes = 1
               #print "bytes: " + str(fswcoldefn.bytes)
               #print "nobytes: " + str(nobytes)
               units = fswcoldefn.units
               #print "units: " + units
               enum = fswcoldefn.enum

               items = fswcoldefn.items
               if items is not None:
                   #print "items: " + str(items)
                   for i in range(items):
                      value = colpk.decode(stream.read(nobytes))
                      strval = str(colfmt % value)
                      out += strval + self.delimiter
               else:
                   strval = ""
                   if str(colpk) == "PrimitiveType('U8')" and nobytes>1:
                       strval = ""
                       for i in range(nobytes):
                           value = colpk.decode(stream.read(1))
                           if name == "RESERVED":
                               continue
                           strval += str(colfmt % value)
                           #print(colfmt % value)
                   else:
                       value = colpk.decode(stream.read(nobytes))
                       #print(colfmt % value)

                   if enum is not None:
                      if enum is not None:
                          for enumkey in enumerate(enum.keys()):
                              #print "enumkey: " + str(enumkey[1]) + ", enumval: " + str(enum[enumkey[1]])
                              if enumkey[1] == value:
                                 strval = str(enum[enumkey[1]])
                   else:
                      if units != 'none':
                          strval = str(colfmt % value) + " " + units
                          #print "units: " + units
                      else:
                          if (str(colpk) != "PrimitiveType('U8')") or (str(colpk) == "PrimitiveType('U8')" and nobytes == 1):
                              strval = str(colfmt % value)
                          if self.name == "response" and "CONSTANT" in name and condition > 6:
                              strval = str('%d' % value)
                   #print "strval: " + strval

                   if self.name == "response" and name == "CONDITION_TYPE":
                       #print "value: "+str(value)
                       condition = value
                       #print "condition: "+str(condition)

                   # Append the value to table row
                   if name == "RESERVED":
                       continue
                   out += strval + self.delimiter

           out = out[:-1] + "\n"
        #print
        #print out
        fswtab_f.write(out)

        # Once we are done appending all the columns to the row
        # strip off last comma and append a \r
        # Note: Since it is Access, \n alone does not work
        return

    def convertValue(self, strval):
        try:
            return int(strval)
        except ValueError:
            return float(strval)

    def toBinary(self, tabfile, stream, fswbin_f, verbose, version):
        #print "self.name: "+self.name
        #print "stream name: "+stream.name

        size = os.path.getsize(stream.name)
        #print "stream len: " + str(size)

        #print "self.size: " + str(self.size)

        no_lines = 0
        for line in stream:
            no_lines += 1
        stream.seek(0)

        fsw_header = bytearray(32)
        # sha1 = hash_file(tabfile)
        sha1 = 0

        # Write magic number
        fswbin_f.write( struct.pack('>H', self.MagicNumber             )  )

        # Write upload type
        fswbin_f.write( struct.pack('B', self.uptype         )  )

        # Write version
        fswbin_f.write( struct.pack('B', int(version,16)&255 )  )

        # Write number of lines
        if self.name == "memory":
            fswbin_f.write( struct.pack('>H', 0           )  )
        else:
            fswbin_f.write( struct.pack('>H', no_lines           )  )

        # Write ID (0)
        fswbin_f.write( struct.pack('>H', 0) )

        # # Write CRC placeholder
        fswbin_f.write( struct.pack('>I', 0) )

        # SHA as 0
        pad = struct.pack('B', 0)
        for n in range(20):
          fswbin_f.write(pad)

        # data = bytearray(20)
        # i = 0
        # tmpbytes = list(sha1)
        # for x in range(0, len(sha1)/2):
        #     tmp = ((int(tmpbytes[x],16)&255)<<4) + (int(tmpbytes[x+1],16)&255)
        #     #print "tmp: "+ str(tmp)
        #     data[i] = tmp&0xFF
        #     i += 1

        # fswbin_f.write(data)

        for line in stream:
            #print "line: "+line
            idx = 0
            line = line.replace("\n","")
            allcols = line.split(self.delimiter)
            if self.name == "memory":
                for val in allcols:
                    if val != "":
                        #print "val: "+val
                        data = bytearray(2)
                        tmpbytes = list(val)
                        data[0] = ((int(tmpbytes[0],16)&0xF)<<4) + (int(tmpbytes[1],16)&0xF)
                        data[1] = ((int(tmpbytes[2],16)&0xF)<<4) + (int(tmpbytes[3],16)&0xF)
                        #print "tmp byte1: "+ str(int(tmpbytes[0],16)&0xF)
                        #print "tmp byte2: "+ str(int(tmpbytes[1],16)&0xF)
                        #print "tmp byte3: "+ str(int(tmpbytes[2],16)&0xF)
                        #print "tmp byte4: "+ str(int(tmpbytes[3],16)&0xF)
                        fswbin_f.write(data)
            else:
                idx = 0
                #this is how to step into table definitions
                for coldef in enumerate(self.coldefns):
                    # print "column definition: " + str(coldef[1])
                    fswcoldefn = coldef[1]
                    name = fswcoldefn.name
                    #print "name: " + name
                    colpk = dtype.get(fswcoldefn.type)
                    #print "packing: " + str(colpk)
                    units = fswcoldefn.units
                    #print "units: " + units
                    enum = fswcoldefn.enum

                    if isinstance(fswcoldefn.bytes,list):
                       nobytes = fswcoldefn.bytes[1] - fswcoldefn.bytes[0] + 1
                    else:
                       nobytes = 1
                    # print "bytes: " + str(fswcoldefn.bytes)
                    # print "nobytes: " + str(nobytes)
                    if name == 'RESERVED':
                        #add reserved bytes
                        fswbin_f.write(colpk.encode(0))

                        if coldef[0] != len(self.coldefns)-1:
                          continue
                        else:
                          break

                    items = fswcoldefn.items
                    if items is not None:
                        #print "items: " + str(items)
                        for i in range(items):
                           val = allcols[i]
                           #print "item col val: "+str(val)
                           if units != 'none':
                               val = val.strip()
                               val = val.split(" ")[0]
                           else:
                               val = val.replace(" ","")
                           #print "item col val: "+str(val)
                           fswbin_f.write(colpk.encode(self.convertValue(val)))
                    else:
                        val = allcols[idx]
                        val = val.replace("\n","")
                        #print "else col val 1: "+str(val)
                        if enum is not None:
                           if enum is not None:
                               for enumkey in enumerate(enum.keys()):
                                   enumval = enum[enumkey[1]]
                                   #print "enumkey: " + str(enumkey[1]) + ", enumval: " + str(enum[enumkey[1]])
                                   if enumval == val:
                                      val = str(enumkey[1])
                               #print "XXXX colpk.type: "+colpk.format
                               fswbin_f.write(colpk.encode(self.convertValue(val)))
                        else:
                           #print "XXXX colpk.type: "+colpk.format
                           #print "fswcoldefn.bytes: "+str(fswcoldefn.bytes)
                           #print "xxxx val: "+str(val)
                           #print "units: "+str(units)
                           if units != 'none':
                               val = val.strip()
                               val = val.split(" ")[0]
                               #print "else col val 2a: "+str(val)
                               fswbin_f.write(colpk.encode(self.convertValue(val)))
                               #fswbin_f.write(colpk.encode(float(val)))
                           elif str(colpk) == "PrimitiveType('U8')" and nobytes>1:
                               strval = ""
                               for c in list(val):
                                   #print "xxx c: "+str(c)
                                   tmp = (int(c,16))&255
                                   #print "tmp: "+str(tmp)
                                   fswbin_f.write(colpk.encode(tmp))
                           else:
                               val = val.replace(" ","")
                               #print "else col val 2b: "+str(val)
                               fswbin_f.write(colpk.encode(self.convertValue(val)))
                               #fswbin_f.write(colpk.encode(float(val)))
                    idx += 1

        written = fswbin_f.tell()
        #print "written: "+str(written)

        # print str(self.size) + ", " + str(written)
        if self.size > written:
            padding = bytearray(self.size - (written))
            fswbin_f.write(padding)

        #Now calculate and update CRC field in the FSW header
        fswbin_f.close()
        fname = fswbin_f.name
        crc32 = util.crc32File(fname, 0)
        fswbin_f = open(fname, 'r+b')
        fswbin_f.seek(28)
        crcbuf = bytearray(4)
        crcbuf[0:4]  = struct.pack('>L',crc32)
        fswbin_f.write(crcbuf)

        #version = "0"
        if verbose is not None and verbose != 0:
            log.info("CRC: %x" % crc32)
            print "MAGIC_NUMBER: %x" % self.MagicNumber
            print "UPLOAD_TYPE: " + str(self.uptype)
            print "VERSION: " + str(version)
            print "NUMBER_ENTRIES: " + str(no_lines)
            # print "SHA-1: "+sha1

        #print "fname: "+fname+", crc32: "+str(crc32)

        # Once we are done appending all the columns to the row
        # strip off last comma and append a \r
        # Note: Since it is Access, \n alone does not work
        return


class FSWTabDict (dict):
    """Table dictionary object

    Table Dictionaries provide a Python dictionary (i.e. hashtable)
    interface mapping Tables names to Column Definitions.
    """
    def __init__ (self, *args, **kwargs):
        """Creates a new Command Dictionary from the given command dictionary
        filename.
        """
        self.filename = None
        self.colnames  = { }

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add (self, defn):
        """Adds the given Command Definition to this Command Dictionary."""
        self[defn.name]          = defn
        self.colnames[defn.name] = defn

    def create (self, name, *args):
        """Creates a new command with the given arguments."""
        tab  = None
        defn = self.get(name, None)
        if defn:
            tab = FSWTab(defn, *args)
        return tab

    def load (self, filename):
        """Loads Command Definitions from the given YAML file into this
        Command Dictionary.
        """
        if self.filename is None:
            self.filename = filename

        stream = open(self.filename, "rb")
        for doc in yaml.load_all(stream):
            for table in doc:
                self.add(table)
        stream.close()


class FSWTabDictCache (object):
    def __init__ (self, filename=None):
        if filename is None:
            filename = os.path.join(os.path.dirname(__file__),
                "../../config/table.yaml")
            filename = os.path.abspath(filename)

        self.filename = filename
        self.pcklname = os.path.splitext(filename)[0] + '.pkl'
        self.fswtabdict  = None

    def dirty (self):
        return (not os.path.exists(self.pcklname) or
            os.path.getmtime(self.filename) > os.path.getmtime(self.pcklname))

    def load (self):
        if self.fswtabdict is None:
            if self.dirty():
                self.fswtabdict = FSWTabDict(self.filename)
                self.update()
            else:
                with open(self.pcklname, "rb") as stream:
                    self.fswtabdict = cPickle.load(stream)

        return self.fswtabdict

    def update (self):
        msg = "Saving updates from more recent '%s' to '%s'"
        log.info(msg, self.filename, self.pcklname)
        with open(self.pcklname, "wb") as output:
            cPickle.dump(self.fswtabdict, output, -1)


_DefaultFSWTabDictCache = FSWTabDictCache()


def getDefaultFSWTabDict ():
    fswtabdict = None
    try:
        filename = _DefaultFSWTabDictCache.filename
        fswtabdict  = _DefaultFSWTabDictCache.load()
    except IOError, e:
        msg = "Could not load default command dictionary '%s': %s'"
        log.error(msg, filename, str(e))

    return fswtabdict


def YAMLCtor_FSWColDefn (loader, node):
    fields          = loader.construct_mapping(node, deep=True)
    return FSWColDefn(**fields)


def YAMLCtor_FSWTabDefn (loader, node):
    fields = loader.construct_mapping(node, deep=True)
    fields['fswheaderdefns'] = fields.pop('header', None)
    fields['coldefns'] = fields.pop('columns', None)
    return FSWTabDefn(**fields)


def writeToText (fswtabdict, tabletype, binfile, verbose, version, outpath=None, messages=None):

    verStr = '%02d' % version

    if not outpath:
      outpath = os.path.dirname(os.path.abspath(binfile))
    elif not os.path.isdir(outpath):
      os.makedirs(outpath)

    #get the table definition
    if tabletype != "log":
        fswtabdefn = fswtabdict.get(tabletype)
        #print "TABLE definition: "+str(fswtabdefn)

        # Get the files ready for writing
        fswtab_f = open(outpath + '/' + tabletype + '_table' + verStr + '.txt', 'w')
        stream = open(binfile, 'rb')

        #pass in stream, fswtab_f
        #print "version: "+str(version)
        fswtabdefn.toText(stream,fswtab_f,verbose,version)
        fswtab_f.close()
    else:
        fswtabdefn = fswtabdict.get("log_main")
        #print "TABLE definition: "+str(fswtabdefn)

        fswtab_f = open(outpath + '/log_main_table' + verStr + '.txt', 'w')
        stream = open(binfile, 'rb')
        fswtabdefn.toText(stream,fswtab_f,verbose)
        fswtab_f.close()

        fswtabdefn = fswtabdict.get("log_isr")
        #print "TABLE definition: "+str(fswtabdefn)
        fswtab_f = open(outpath + '/log_isr_table' + verStr + '.txt', 'w')
        fswtabdefn.toText(stream,fswtab_f,verbose)
        fswtab_f.close()

        fswtabdefn = fswtabdict.get("log_evr")
        #print "TABLE definition: "+str(fswtabdefn)
        fswtab_f = open(outpath + '/log_evr_table' + verStr + '.txt', 'w')
        fswtabdefn.toText(stream,fswtab_f,verbose)
        fswtab_f.close()

        fswtabdefn = fswtabdict.get("log_assert")
        #print "TABLE definition: "+str(fswtabdefn)
        fswtab_f = open(outpath + '/log_assert_table' + verStr + '.txt', 'w')
        fswtabdefn.toText(stream,fswtab_f,verbose,version)
        fswtab_f.close()


    #close input file
    stream.close()


def writeToBinary (fswtabdict, tabletype, tabfile, verbose, outbin=None, version=0, binfilemessages=None):

    #get the table definition
    fswtabdefn = fswtabdict.get(tabletype)
    #print "TABLE definition: "+str(fswtabdefn)

    if not outbin:
      # Get the files ready for writing
      outbin = os.path.join(tabletype + '_table' + str(version) + '.bin')

    log.info("Generating binary: %s" % outbin)

    fswbin_f = open(outbin, 'wb')
    #print "output bin file: "+outpath + '/' + tabletype + '_table' + str(version) + '.bin'
    stream = open(tabfile, 'r')

    #pass in stream, fswtab_f
    fswtabdefn.toBinary(tabfile, stream, fswbin_f, verbose, str(version))

    #close input and output files
    stream.close()
    fswbin_f.close()

yaml.add_constructor('!FSWTable' , YAMLCtor_FSWTabDefn)
yaml.add_constructor('!FSWColumn', YAMLCtor_FSWColDefn)
