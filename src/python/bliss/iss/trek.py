"""BLISS TReK Command Converter

The bliss.iss.trek module provides the dictionary for translating
Commands into text csv files to be imported into TReK.

"""

"""
Authors: Jordan Padams

Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""

import cPickle
import os
import yaml

import bliss


MSID_DEVICE_ID = "UAZA25RT"
MSID_SIGNAL_TYPE = "K"

YAML_VARS = ['cmd', 'arg']

class ColDefn (object):
    """ColDefn - Argument Definition

    Argument Definitions encapsulate all information required to define
    a single command argument.  This includes the argument name, its
    description, units, type, byte position within a command, name-value
    enumerations, and allowed value ranges.  Name, type, and byte
    position are required.  All others are optional.
    """
    __slots__ = [
        "name", "_default", "max_length", "_whitespace", "_unique", "_values"
    ]

    def __init__ (self, *args, **kwargs):
        """Creates a new Column Definition.
        """
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))


    def __repr__ (self):
        return bliss.util.toRepr(self)

    @property
    def values (self):
        """The argument values."""
        return self._values

    @values.setter
    def values (self, value):
        self._values = value if value is not None else { }

    @property
    def default (self):
        """The argument default value."""
        return self._default

    @default.setter
    def default (self, value):
        self._default = str(value) if value is not None else ''

    @property
    def whitespace (self):
        """The argument whitespace flag if it can contain whitespace."""
        return self._whitespace

    @whitespace.setter
    def whitespace (self, value):
        self._whitespace = value if value is not None else False

    @property
    def unique (self):
        """The argument uniqueness flag whether or not it must be unique
        according to the specification.
        """
        return self._unique

    @unique.setter
    def unique (self, value):
        self._unique = value if value is not None else False

    def evaluate (self, cmd, arg, keysdict={ }, cnt=0):
        """Evaluate the column definition using the cmd, keys dictionary, and
        cnt as possible variables to evaluate against as specified in the YAML
        definition"""

        eval_str = ""
        value = ""

        if self.values:
            if cmd.name in self.values.keys():
                value = str(self.values[cmd.name])
            elif arg.name in self.values.keys():
                value = str(self.values[arg.name])

        if not value:
                value = self.default

        # Get the column default values
        # If the value start with '$' we want to evaluate it
        if value.startswith('$'):
            eval_str = value.replace('$','')
            value = eval(eval_str)

        if value is not None:
            value = str(value)
        else:
            value = ""

        valid, value = self.validate(eval_str, value, keysdict)

        # Check uniqueness, as applicable
        if self.unique:
            if value == "":
                value = "value"

            while value in keysdict.keys():
                # If value is in the pk dictionary, find out the number
                # of matches, increment that number, and append to
                # the value
                matches = keysdict.get(value) + 1
                keysdict[value] = matches
                suffix = "_" + str(matches)

                substring_index = self.max_length - len(suffix)
                value = value[0:substring_index] + suffix

            # Add new key to dictionary so we ensure uniqueness
            keysdict.update({value:0})

            # Change the command/argument name in case it is referenced in the future
            if YAML_VARS.count(eval_str.split('.')[0]) > 0:
                obj = eval(eval_str.split('.')[0])
                slotindex = obj.__slots__.index(eval_str.split('.')[1] )
                setattr(obj, obj.__slots__[slotindex], value)
                #print obj.name

        # Enclose in quotes if field may contain whitespace. Replace newlines
        if self.whitespace:
            value = "\"" + value.replace('\n',' ').rstrip() + "\""

        return value

    def validate (self, eval_str, value, keysdict={ }, messages=None):
        """Returns True if the given Argument value is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        valid = True

        def log (msg):
            if messages is not None:
                messages.append(msg)

        if len(value) > self.max_length:
            # Take slice of string if longer than max length
            value = value[0:self.max_length]
                
        return valid, value

class Tab (object):
    """Table object that contains column definitions

    Commands reference their Command Definition and may contain arguments.
    """
    def __init__ (self, defn, *args):
        """Creates a new OCO-3 Command based on the given command definition
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


class TabDefn (object):
    """Table Definition

    Command Definitions encapsulate all information required to define a
    single command.  This includes the command name, its opcode,
    subsystem, description and a list of argument definitions.  Name and
    opcode are required.  All others are optional.
    """
    __slots__ = ["name", "coldefns"]


    def __init__ (self, *args, **kwargs):
        """Creates a new Command Definition."""
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, kwargs.get(name, None))

        if self.coldefns is None:
            self.coldefns = [ ]


    def __repr__ (self):
        return bliss.util.toRepr(self)

    def toCsv(self, cmd, arg, keys_d, cnt):
        out = ""
        coldefn_list = self.coldefns

        # Loop through each column definition and evaluate
        for coldefn in coldefn_list:
            value = coldefn.evaluate(cmd, arg, keys_d, cnt)

            # Append the value to table row
            out += value + ","
        
        # Once we are done appending all the columns to the row
        # strip off last comma and append a semicolon and \r 
        # Note: Since it is Access, \n alone does not work
        return out[:-1] + ";\r\n"


class TabDict (dict):
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
        self[defn.name]            = defn
        self.colnames[defn.name] = defn

    def create (self, name, *args):
        """Creates a new OCO-3 command with the given arguments."""
        tab  = None
        defn = self.get(name, None)
        if defn:
            tab = Tab(defn, *args)
        return tab

    def load (self, filename):
        """Loads Command Definitions from the given YAML file into this
        Command Dictionary.
        """
        if self.filename is None:
            self.filename = filename
            stream        = open(self.filename, "rb")
            for tab in yaml.load_all(stream):
                self.add(tab)
            stream.close()


class TabDictCache (object):
    def __init__ (self, filename=None):
        if filename is None:
            filename = os.path.join(os.path.dirname(__file__), 
                "../../config/trek_cmd.yaml")
            filename = os.path.abspath(filename)

        self.filename = filename
        self.pcklname = os.path.splitext(filename)[0] + '.pkl'
        self.tabdict  = None

    def dirty (self):
        return (not os.path.exists(self.pcklname) or 
            os.path.getmtime(self.filename) > os.path.getmtime(self.pcklname))

    def load (self):
        if self.tabdict is None:
            if self.dirty():
                self.tabdict = TabDict(self.filename)
                self.update()
            else:
                with open(self.pcklname, "rb") as stream:
                    self.tabdict = cPickle.load(stream)

        return self.tabdict

    def update (self):
        msg = "Saving updates from more recent '%s' to '%s'"
        bliss.log.info(msg, self.filename, self.pcklname)
        with open(self.pcklname, "wb") as output:
            cPickle.dump(self.tabdict, output, -1)

class TrekArgDefn(object):
    """Wrapper class for ArgDefn that adds some Trek-specific
    functionality to the ArgDefn object that would not be applicable
    for cmd.py.
    """

    # This dictionary represents the CCSDS Header argument that must be appended
    # to the end of every command. The type denotes is LSB_16 because per
    # MSFC-DOC-1949D, the data type ICHK is stored in the least significant
    # 16 bits of the last command data word, padded with leading zeroes as
    # necessary to fill the 16 bits
    CCSDS_ARG = {
        "name" : "ccsds_checksum",
        "type" : "LSB_U16",
        "bytes" : [106, 107],
        "fixed" : True
    }

    # This dictionary represents the default padding column that will be
    # appended to all commands that are less than 53 words
    PAD_ARG = {
        "name"  : "padding",
        "value" : 0,
        "fixed" : True
    }

    # Dictionary to provide mapping from Primitive Data Types
    # to the ISS Uplink Data Types defined in MSFC-DOC-1949D
    PDT_TO_UDT = {
        "I8"      :  "IMAG", 
        "U8"      :  "IUNS",
        "LSB_I16" :  "ITWO",
        "MSB_I16" :  "ITWO",
        "LSB_U16" :  "IUNS",
        "MSB_U16" :  "IUNS",
        "LSB_I32" :  "ITWO",
        "MSB_I32" :  "ITWO",
        "LSB_U32" :  "IUNS",
        "MSB_U32" :  "IUNS",
        "LSB_F32" :  "FEEE",
        "MSB_F32" :  "FEEE",
        "LSB_D64" :  "FEEE",
        "MSB_D64" :  "FEEE",
        "S"       :  "SUND"
    }

    # Provide the mappings from the available uplink data type
    # to their applicable input data types and units
    UDT_MAPPINGS = {
        "FEEE"  :  { "idt" : "D", "type" : "bits"},
        "ICHK"  :  { "idt" : "", "type" : "bits"},
        "IMAG"  :  { "idt" : "D", "type" : "bits"},
        "ITWO"  :  { "idt" : "D", "type" : "bits"},
        "IUNS"  :  { "idt" : "H", "type" : "bits"},  # right-justified
        "SUND"  :  { "idt" : "H", "type" : "bytes"}
    }

    def __init__ (self, defn, *args):
        self.defn = defn
        self.__slots__ = defn.__slots__

        # Set all the properties according to the 'parent' argdefn
        for slot in defn.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            value =  getattr(defn, name, None)
            setattr(self, name, value)

    def __repr__ (self):
        self.defn.__repr__()

    @property
    def nbytes (self):
        """The number of bytes required to encode this argument using the
        primitive data type. Includes validation against what is described
        in YAML"""
        return self.defn.nbytes

    @property
    def startword (self):
        """The argument start word in the command"""
        return self.defn.startword

    @property
    def startbit (self):
        """The argument start bit in the word"""
        return self.defn.startbit

    @property
    def uplinktype (self):
        """The argument uplink data type per MSFC-DOC-1949.

        These types are necessary for mapping to what data types recognizable
        to the POIC.
        """
        if not self.defn.type.string:
            udt = self.PDT_TO_UDT[self.defn.type.name]
        else:
            udt = self.PDT_TO_UDT[self.defn.type.name.rstrip('0123456789')]

        return udt if udt is not None else ""

    @property
    def inputtype (self):
        """The argument input data type per MSFC-DOC-1949.

        These types are necessary for mapping to what data types recognizable
        to the POIC.
        """
        idt = self.UDT_MAPPINGS[self.uplinktype]['idt']
        return idt if idt is not None else ""

    @property
    def swapped (self):
        """Determined whether or not the value should be byte-swapped"""
        if self.defn.type.endian == 'LSB':
            return 'Y'
        else:
            return 'N'

    @property
    def unitlength(self):
        """Calculates the argument size using the correct units. Dependent upon the
        input data type"""
        reptype = self.UDT_MAPPINGS[self.uplinktype]['type']

        if reptype == 'bytes':
            return self.nbytes
        elif reptype == 'bits':
            return self.nbytes * 8
        else:
            msg = "Representation type '%s' not found for '%s'. Check configuration."
            bliss.log.error(msg, reptype, self.name)
            return ""

    @property 
    def rawvalue(self):
        """Translates the value for the argument (if applicable) into the correct
        format (i.e. HEX where idt = H """
        if self.inputtype == 'H' and self.value is not None and self.value != 0:
            return hex(int(self.value)).lstrip('0x')
        else:
            return self.value


_DefaultTabDictCache = TabDictCache()


def getDefaultTabDict ():
    tabdict = None

    try:
        filename = _DefaultTabDictCache.filename
        tabdict  = _DefaultTabDictCache.load()
    except IOError, e:
        msg = "Could not load default command dictionary '%s': %s'"
        bliss.log.error(msg, filename, str(e))

    return tabdict

def YAMLCtor_ColDefn (loader, node):
    fields          = loader.construct_mapping(node, deep=True)
    return ColDefn(**fields)

def YAMLCtor_TabDefn (loader, node):
    fields = loader.construct_mapping(node, deep=True)
    fields['coldefns'] = fields.pop('columns', None)
    return TabDefn(**fields)

def generateMsid(seqnum):
    """Generates MSID based on sequence number, default
    device Id, and signal type"""
    seqnum = str(seqnum)
    while len(seqnum) < 4:
        seqnum = "0" + seqnum

    return MSID_DEVICE_ID + str(seqnum) + MSID_SIGNAL_TYPE

def appendDfltArgs(cmd):
    """Builds the argument definitions for the default arguments for
    padding the command (when applicable) and appending the CCSDS checksum
    """
    start = cmd.argsize

    cmdsize = bliss.cmd.getMaxCmdSize()

    # Only add padding if its needed
    if start != cmdsize - 1 :
        newarg = TrekArgDefn.PAD_ARG

        # Get remaining size for padding
        # cmdsize-1 because byte slices start at 0
        newarg['bytes'] = [start, cmdsize-1]
        newarg['type'] = "S" + str(cmdsize - start)

        cmd.argdefns.append(bliss.cmd.ArgDefn(**newarg))


    cmd.argdefns.append(bliss.cmd.ArgDefn(**TrekArgDefn.CCSDS_ARG))


def writeToCsv (cmddict, outpath='../output/', messages=None):

    if not os.path.isdir(outpath):
        os.makedirs(outpath)

    # Get the files ready for writing
    cmd_f = open(outpath + '/command.txt', 'w')
    cmdfld_f = open(outpath + '/command_fld.txt', 'w')

    # Get a unique dictionaries ready for table primary keys
    cmdkeys_d = { }

    # Get the command table definition dictionary
    cmdtabdefn  = getDefaultTabDict()
    for cmdcnt, opcode in enumerate(cmddict.keys()):
        cmddefn  = cmddict.get(opcode)
        argdefns = cmddefn.argdefns

        tabdefndict = cmdtabdefn.colnames
        cmdtab = tabdefndict.get('command')
        
        if cmddefn.staging_required():
            tabrow = cmdtab.toCsv(cmddefn, None, cmdkeys_d, cmdcnt)
            #print
            #print tabrow
            cmd_f.write(tabrow)

            appendDfltArgs(cmddefn)

            argkeys_d = { }

            for argcnt, argdefn in enumerate(argdefns):
                cmdfldtab = tabdefndict.get('command_fld')

                trekArg = TrekArgDefn(argdefn)

                tabrow = cmdfldtab.toCsv(cmddefn, trekArg, argkeys_d, argcnt)
                #print "-- " + tabrow
                cmdfld_f.write(tabrow)

yaml.add_constructor('!Table' , YAMLCtor_TabDefn)
yaml.add_constructor('!Column', YAMLCtor_ColDefn)
