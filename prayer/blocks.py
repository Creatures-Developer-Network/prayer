"""
Baseclass Block & TagBlocks for PRAY blocks.

All PRAY blocks are composed of three binary sections:
* prefix, 4 characters specifying the prefix of block
* header, metadata structured as in the table below
* body data

PRAY headers are 144 bytes long, structured as follows:
+------------+--------------------------+------------------------------+
| type/size  | variable                 | description                  |
+============+==========================+==============================+
| 4 Bytes    | prefix                   | prefix prefix of the block.  |
+------------+--------------------------+------------------------------+
| 128 Bytes  | name                     | Name of the block, remainder |
|            |                          | is padded with zeroes.       |
+------------+--------------------------+------------------------------+
| Int32      | body_length              | uncompressed data size.      |
+------------+--------------------------+------------------------------+
| Int32      | body_length_decompressed | body size when unzipped. the |
|            |                          | same as above if block data  |
|            |                          | isn't compressed.            |
+------------+--------------------------+------------------------------+
| Int32      | compressed               | The first bit should be set  |
|            |                          | to 1 if the data is zipped.  |
+------------+------------------------+--------------------------------+

The structure of the body depends on the type of block. This library
handles this through inheritance of a baseclass.

"""
import zlib
from collections import MutableSequence, namedtuple
from typing import ByteString, Any, Union
from struct import Struct
from itertools import chain


MAX_BLOCK_NAME_LENGTH = 128
DEFAULT_ENCODING = 'cp1252'


# this Struct definition assumes that python is using the same sizes as
# cpython does on x86/amd64 by default. It's unlikely that this will be
# run on python implementations that differ, but it's good to note the
# assumption just in case.
BLOCK_HEADER_STRUCT = Struct(
    "<"  # little endian
    "4s"  # 4 bytes, type prefix
    "128s"  # 128 bytes, block name, c-string padded with zeroes
    "I"  # 32 bit signed int,  uncompressed length
    "I"  # 32 bit signed int, compressed length
    "I"  # compression flag
)
BLOCK_HEADER_LENGTH = BLOCK_HEADER_STRUCT.size
BlockHeaderTuple = namedtuple(
    "BlockHeaderTuple",
    (
        "prefix",
        "name",
        "length",
        "length_decompressed",
        "compressed"
    )
)


# a hack for type checking behavior that seems contrary to the docs, but
# that may only be because I don't understand the typing module correctly.
def valid_data_source(src: Any) -> bool:
    """
    Validate the data source as something a block can read from.

    This may be the incorrect way of handling this. The doc for the typing
    module states that ByteString should match bytes, bytearray, and
    memoryview, and that the bytes prefix should match those as well.

    However, ByteString only works with bytes and bytearray builtins.

    :param src: an object to be checked
    :return:
    """
    return isinstance(src, ByteString) or isinstance(src, memoryview)


# track which Block classes are generics allowed to change their prefix
INSTANCES_CAN_CHANGE_PREFIX = set()

class Block:
    """

    Baseclass for PRAY blocks.

    The following attributes and/or properties are exposed:
    * prefix - the 4 character prefix of this PRAY block
    * name - the name of this block
    * compressed - whether the block was compressed at read
    * data - the uncompressed representation of this block, with header
    * data_compressed - zlib-compressed version of this block, with header
    * body - the data of the body, uncompressed
    * body_compressed - the data of the body, compressed with zlib

    The following attributes may be used to set values:
    * prefix, but only on base Block instances
    * name
    * data
    * body
    * body_compressed

    The structure of the body data is dependent on the prefix of PRAY block.
    Subclasses should override the following methods to handle reading and
    writing block bodies:
    * _read_body
    * _write_body

    """

    # override this in subclasses
    default_type_string: str = "NONE"

    def __init__(
            self,
            name: str = None,
            compressed: Union[bool, int] = False,
            body: ByteString = None,
            data: ByteString = None
    ):
        """

        Construct a PRAY block, optionally from a passed ByteString.

        The bytestrings may be passed as either body or data keyword args.

        ByteStrings may be bytes, bytearrays, a memoryview,
        or a subclass of one of those types.

        Name sets the name of the block in the header.

        Compressed singals whether the source data was initially compressed.
        It also tells the constructor whether the body argument should be
        treated as zipped or not.

        Body is the data to read the data of the block from. If compressed
        is true, then this data will be unzipped before attempting to set
        the body data of the block.

        The data parameter overrides all other types, and the block will
        attempt to read from it.

        :param name: the name to set the block's name attribute to.
        :param compressed: whether the body data was compressed at read time
        :param body: a ByteString to read as body data
        :param data: a ByteString including both header and body data
        """

        # set prefix to the class string value.
        self._prefix: str = self.default_type_string

        self.name = ""
        if name is not None:
            if not isinstance(name, str):
                raise TypeError("Block name must be a string")

            self.name = name

        self.compressed = compressed

        # Stubs for caching. Replace with better code in the future?
        # Works for now as we only return bytes to maintain compatibility
        # with 3.7.
        self._body_cache = bytearray()  # uncompressed body data
        self._body_compressed_cache = bytearray()

        # these are updated when the body is? temp vars, really.
        self._expected_length: int = None
        self._expected_length_decompressed: int = None
        self._header_cache = bytearray(BLOCK_HEADER_LENGTH)  # caches header

        if data:
            self._read_block(data)
        elif body:
            if self.compressed:
                self.body = zlib.decompress(body)
            else:
                self.body = body

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value: str) -> None:
        """
        Sets the block prefix, but only on base Block and TagBlocks.

        Subclasses raise exceptions since they're supposed to use an
        override of the class variable.

        The generic baseclass prefix values are mutable so users can
        explore PRAY and warp packets at their leisure.

        :param value: 4 letter string.
        :return:
        """

        # it's important to use the current class and
        # not an instanceof call for this.
        if self.__class__ not in INSTANCES_CAN_CHANGE_PREFIX:
            raise TypeError(
                "Can only change the prefix on generic Blocks and "
                "TagBlocks not their subclasses."
            )
        if len(value) != 4:
            raise ValueError("Block types must be 4 character strings")

        self._prefix = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """
        Store the name.

        Raises a ValueError when:
        * length is over 128
        * the string can't be encoded to match c2e's encoding

        :param value: candidate for being the new block name
        :return:
        """

        if not isinstance(value, str):
            raise TypeError(
                f"Name must be set to a str, not a {type(value)}"
            )

        # This is more informative than the previous behavior of breaking
        # at write time, but it's bad. Maybe keep both an encoded and
        # string version around? Revisit in encoding fix ticket?
        try:
            encoded_value = bytes(value, DEFAULT_ENCODING)
        except UnicodeEncodeError as e:
            raise ValueError(
                "Name must only contain characters that "
                "can be encoded in Windows-1252/CP-1252."
            ) from e

        # raise if it doesn't fit in a 128-byte null terminated string
        if len(encoded_value) >= MAX_BLOCK_NAME_LENGTH:
            raise ValueError(
                "Name must be encodeable to 127 Windows-1252/CP-1252 "
                "characters or less."
            )
        self._name = value

    @property
    def data(self) -> bytes:
        """
        Get the serialized version of this block, header + body.

        :return: bytes
        """

        self._write_block(compress_data=False)
        return bytes(chain(self._header_cache, self._body_cache))

    @property
    def body(self) -> bytes:
        """
        Return the body contents of this block, uncompressed

        :return: the body of the block as bytes
        """
        return bytes(self._body_cache)

    @body.setter
    def body(self, body: ByteString) -> None:
        """
        Copy the value of the passed bytestring to the internal body cache

        :param body: a bytestring to be the source of the body
        :return: None
        """
        if not valid_data_source(body):
            raise TypeError(
                "body must be a bytes, bytearray, or memoryview"
            )

        # trust python's implementation to handle mutability wisely,
        # don't unnecessarily throw away and create objects.
        if len(self._body_cache) > len(body):
            self._body_cache.clear()

        # copy the contents of body to the internal cache, then interpret it
        self._body_cache[0:] = body
        self._read_body()

    @property
    def body_compressed(self) -> bytes:
        self._write_body(compress_data=True)
        return zlib.compress(self._body_cache)

    @data.setter
    def data(self, block_data: ByteString) -> None:
        self._read_block(data=block_data)

    @property
    def data_compressed(self) -> bytes:
        self._write_block(compress_data=True)
        return bytes(chain(self._header_cache, self._body_compressed_cache))

    @property
    def compressed(self) -> bool:
        return self._compressed

    @compressed.setter
    def compressed(self, compressed: bool) -> None:
        if isinstance(compressed, bool):
            self._compressed = compressed
        else:
            raise TypeError(
                f"Expected bool or int for compressed,"
                f" but got {compressed}."
            )


    def _read_block_header(self, data: ByteString) -> None:
        """
        Read the header of a single block.

        :param data:
        :return:
        """

        raw_header = BlockHeaderTuple._make(
            BLOCK_HEADER_STRUCT.unpack_from(data)
        )

        self._prefix = raw_header.prefix.decode("latin-1")
        self.name = raw_header.name.decode("latin-1").rstrip("\0")
        self._expected_length = raw_header.length
        self._expected_length_decompressed = raw_header.length_decompressed

        # then there is an 32 Bit Integer containing either a one or a zero, 1
        # = block data is compressed, 0 = block data is uncompressed
        if (
            raw_header.compressed
            and raw_header.length != raw_header.length_decompressed
        ):
            self._compressed = True
        else:
            self._compressed = False


    def _write_block_header(self, compress_data: bool = False) -> None:
        """

        Write the header of the block to internal cache.
        Assumes that the body cache has already been updated.

        The following will be written to the cache:
        * block prefix header
        * name
        * block length when uncompressed
        * block length after compression is applied, if any
        * a flag block with a bit indicating compression

        See class and module docstrings for full info about headers

        :param compress_data: whether to compress the _data of a block.
        :return: the block as bytes
        """

        uncompressed_length = len(self._body_cache)
        data_block = self._body_cache

        if compress_data:
            data_block = self._body_compressed_cache

        BLOCK_HEADER_STRUCT.pack_into(
            self._header_cache, 0,
            bytes(self.prefix, encoding="latin-1"),
            bytes(self.name, encoding="latin-1").ljust(128, b"\0"),
            len(data_block),
            uncompressed_length,
            int(compress_data)
        )

    def _read_body(self) -> None:
        """
        Deserialize the internal body cache to internal variables.

        Override this for subclasses, does nothing on the baseclass.
        """
        pass

    def _write_body(self, compress_data: bool = True) -> None:
        """

        Serialize subclass internal variables to data caches.

        :return:
        """
        pass


    def _read_block(self, data: ByteString) -> None:
        """
        Read whole block data from the passed bytestring.

        It does a number of things:
        * calls _read_header
        * decompresses the body data if needed and sets the internal cache
        * calls _read_body

        :param data: the source bytestring to read from.
        :return: None
        """

        try:
            # using a memoryview avoids copying, even when sliced.
            root_memoryview: memoryview = memoryview(data)

        except TypeError as e:
            # clarifies things for end users little, not sure if it's a good idea
            raise TypeError(
                f"Block data can only be read from valid ByteStrings,"
                f" i.e. bytes, bytearrays, and memoryviews, not"
                f" {type(data)}"
            ) from e

        if len(root_memoryview) < BLOCK_HEADER_LENGTH:
            raise ValueError(
                "Provided data too short to be a valid PRAY block"
            )

        self._read_block_header(root_memoryview)

        # Putting body decompression here rather than in _read_body makes
        # implementing new blocks easier. It eliminates the need for a
        # super() call to decompress the data at the start of every
        # _read_body() definition.
        body_source = root_memoryview[BLOCK_HEADER_LENGTH:]

        if self._compressed:  # check body length and decompress it
            if len(body_source) != self._expected_length:
                raise ValueError(
                    f"Expected {self._expected_length} bytes"
                    f" of compressed body data but got {len(body_source)}"
                    f" bytes instead"
                )
            body_source = zlib.decompress(body_source)

        if len(body_source) != self._expected_length_decompressed:
            raise ValueError(
                f"Expected uncompressed body to be"
                f" {self._expected_length_decompressed} bytes but got "
                f"{len(body_source)} bytes instead."
            )

        # set body cache & extract internal data from it
        self.body = body_source

    def _write_block(self, compress_data: bool = False) -> None:
        """

        Serialize the block components to internal bytearrays.

        Also handles compression to avoid complicating _write_body.

        :return: None, components are written to internal bytearrays.
        """

        self._write_body(compress_data=compress_data)

        if compress_data:
            self._body_compressed_cache = self.body_compressed

        self._write_block_header(compress_data=compress_data)


INSTANCES_CAN_CHANGE_PREFIX.add(Block)

class TagBlock(Block):

    # note this isn't an actual valid prefix, and should be overridden
    # by subclasses, as with the "NONE" prefix the base Block class uses.
    default_type_string: str = "TAGS"

    def __init__(
            self,
            name: str = None,
            compressed: Union[bool, int] = True,
            body: ByteString = None,
            data: ByteString = None
    ):
        """
        Construct a base TagBlock. Mirrors the keywords on Block.

        :param name:
        :param compressed:
        :param body:
        :param data:
        """
        super().__init__(
            name=name,
            compressed=compressed,
            body=body,
            data=data
        )


    @staticmethod
    def create_tag_block(block_type, block_name, named_variables) -> None:
        tmp_tag_block = TagBlock(Block().data)
        tmp_tag_block.prefix = block_type
        tmp_tag_block.name = block_name
        tmp_tag_block.number_of_integer_variables = 0
        tmp_tag_block.number_of_string_varaibles = 0
        for variable in named_variables:
            if type(variable[1] == int):
                number_of_integer_variables = +1
                tmp_tag_block.named_variables.append(variable)
            elif type(variable[1 == str]):
                number_of_string_varaibles = +1
                tmp_tag_block.named_variables.append(variable)
        return tmp_tag_block

        raise NotImplementedError

    def _get_named_integer_variables(self, data, count):
        """

        :param data:
        :param count:
        :return:
        """
        #
        # Each named Integer Variable consists of 3 Parts:
        # - a 32bit Integer Variable that states the length of the name 'key_length'
        # - n Bytes containing said Name, where n is the length specified in the Integer beforhand 'key'
        # - a 32bit Integer containing the 'value' of the Named Integer
        # +------------------+-------------------+--------------+
        # | 4B  Int len(KEY) | nB KEY in LATIN-1 | 4B Int Value |
        # +------------------+-------------------+--------------+
        #
        if count != 0:
            key_length = int.from_bytes(data[:4], byteorder="little")
            key = data[4 : 4 + key_length].decode("latin-1")
            value = int.from_bytes(
                data[4 + key_length : 8 + key_length], byteorder="little"
            )
            self.named_variables.append((key, value))
            self._get_named_integer_variables(
                data=data[8 + key_length :], count=count - 1
            )
        else:
            self.str_data = data

    def _get_named_string_variables(self, data, count):
        #
        # Each named String Variable consists of 4 Parts:
        # - a 32bit Integer Variable that states the length of the name 'key_length'
        # - n Bytes containing said name, where n is the length specified in the Integer beforhand 'key'
        # - a 32bit Integer Variable that states the length of the value 'value_length'
        # - n Bytes containing said 'value', where n is the length specified in the Integer beforhand 'value_length'
        # +-----------------+-------------------+-------------------+---------------------+
        # | 4B Int len(KEY) | nB KEY in LATIN-1 | 4B Int len(Value) | nB Value in LATIN-1 |
        # +-----------------+-------------------+-------------------+---------------------+
        #
        if count != 0:
            key_length = int.from_bytes(data[:4], byteorder="little")
            key = data[4 : 4 + key_length].decode("latin-1")
            value_length = int.from_bytes(
                data[4 + key_length : 8 + key_length], byteorder="little"
            )
            value = data[8 + key_length : 8 + key_length + value_length].decode(
                "latin-1"
            )
            self.named_variables.append((key, value))
            self._get_named_string_variables(
                data=data[8 + key_length + value_length :], count=count - 1
            )
        else:
            self.str_data = data

    @property
    def data(self) -> ByteString:
        # if self.named_variables.data_changed:
        if True:
            ints = list()
            strings = list()
            for variable in self.named_variables:
                if type(variable[1]) == int:
                    ints.append(variable)
                elif type(variable[1] == str):
                    strings.append(variable)
            tmp_ints = bytes(len(ints).to_bytes(length=4, byteorder="little"))
            for variable in ints:
                tmp_ints += len(bytes(variable[0], encoding="latin-1")).to_bytes(
                    length=4, byteorder="little"
                )
                tmp_ints += bytes(variable[0], encoding="latin-1")
                tmp_ints += variable[1].to_bytes(length=4, byteorder="little")
            tmp_strings = bytes(len(strings).to_bytes(length=4, byteorder="little"))
            for variable in strings:
                tmp_strings += len(bytes(variable[0], encoding="latin-1")).to_bytes(
                    length=4, byteorder="little"
                )
                tmp_strings += bytes(variable[0], encoding="latin-1")
                tmp_strings += len(bytes(variable[1], encoding="latin-1")).to_bytes(
                    length=4, byteorder="little"
                )
                tmp_strings += bytes(variable[1], encoding="latin-1")
            self._data = tmp_ints + tmp_strings
            # self.named_variables.data_changed = False
        return self._data

    @data.setter
    def data(self, data: ByteString):
        self._data = data
        self.named_variables = list()
        # Integers
        self.number_of_integer_variables = int.from_bytes(data[:4], byteorder="little")
        self._get_named_integer_variables(
            data=data[4:], count=self.number_of_integer_variables
        )
        # Strings
        self.number_of_string_varaibles = int.from_bytes(
            self.str_data[:4], byteorder="little"
        )
        self._get_named_string_variables(
            data=self.str_data[4:], count=self.number_of_string_varaibles
        )


INSTANCES_CAN_CHANGE_PREFIX.add(TagBlock)


class TagBlockVariableList(MutableSequence):
    """

    A sequence of tag blocks

    """
    def __init__(self, data=None):
        self.data_changed = False
        super(TagBlockVariableList, self).__init__()
        if not (data is None):
            self._list = list(data)
        else:
            self._list = list()

    def append(self, val) -> None:
        """
        Append data to t
        :param val:
        :return:
        """
        list_idx = len(self._list)
        self.data_changed = True
        self.insert(list_idx, val)
