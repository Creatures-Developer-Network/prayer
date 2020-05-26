"""
Baseclass Block & TagBlocks for PRAY blocks.

All PRAY blocks are composed of two binary sections:
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
from io import BytesIO, RawIOBase
from itertools import chain
from struct import Struct
from typing import ByteString, Union, Iterable, Tuple, Callable

from prayer.common import valid_bytestring, coerce_encoding

MAX_BLOCK_NAME_LENGTH = 127
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
    default_prefix: bytes = b"NONE"

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
        self._prefix: str = self.default_prefix


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
    def prefix_mutable(self) -> bool:
        """
        Whether the current instance is allowed to alter its prefix.

        False for anything that isn't a base Block or TagBlock.

        :return: whether prefix is a mutable property
        """
        # it's important to use the current class and
        # not an instanceof call for this.
        return self.__class__ in INSTANCES_CAN_CHANGE_PREFIX

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

        if not self.prefix_mutable :
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

        # Dirty, the return value is discarded and errors are
        # raised if there's a problem. Really should keep around
        # two versions of each string somehow.
        coerce_encoding(value, MAX_BLOCK_NAME_LENGTH)
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
        if not valid_bytestring(body):
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

        # Error if trying to create a non-generic block from
        # a mismatched prefix.
        if raw_header.prefix != self._prefix:
            if not self.prefix_mutable:
                raise TypeError(
                    f"Prefix {raw_header.prefix} is not allowed for "
                    f"blocks of type {type(self)}"
                )
            self._prefix = raw_header.prefix

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
            self.prefix,
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


def _read_uint32(src_stream: RawIOBase) -> int:
    """
    Read a UInt32 from a stream and return it

    :param src_stream:
    :return:
    """
    return int.from_bytes(src_stream.read(4), byteorder="little")


def _read_prefixed_string(
        src_stream: RawIOBase,
        encoding=DEFAULT_ENCODING
) -> str:
    """
    Read a length-prefixed string from a stream and return it

    :param src_stream: the stream to read from
    :param encoding: what encoding to decode the string bytes with
    :return:
    """
    num_bytes_to_read = _read_uint32(src_stream)
    string = src_stream.read(num_bytes_to_read).decode()
    return string


def _write_uint32(out_stream, i: int) -> None:
    """
    Write an int to the passed stream

    :param out_stream: stream to write to
    :param i:
    :return:
    """
    out_stream.write(i.to_bytes(4, "little"))


def _write_prefixed_string(
    out_stream,
    s: str
) -> None:
    """
    Encode a passed string, prefix it with length, write both to stream

    :param out_stream: where to write to
    :param s: string to encode
    :return:
    """
    encoded = s.encode(DEFAULT_ENCODING)
    _write_uint32(out_stream, len(encoded))
    out_stream.write(encoded)


class TagBlock(Block):
    """

    Read/write string and integer variables.

    Demonstrates how much cleaner the code can be by using streams and
    inheritance to handle location counting for you.

    It's still inefficient as it doesn't cache values properly, but that
    is assumed to be a target for a future ticket.

    """

    # note this isn't an actual valid prefix, and should be overridden
    # by subclasses, as with the "NONE" prefix the base Block class uses.
    default_prefix: bytes = b"TAGS"

    def __init__(
            self,
            name: str = None,
            compressed: Union[bool, int] = True,
            body: ByteString = None,
            data: ByteString = None,
            named_variables: Iterable[Tuple[str, Union[int, str]]] = None,
    ):
        """
        Construct a base TagBlock. Mirrors the keywords on Block.

        if neither body or data fields are defined, named_variables

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

        # This approach is still incorrect imo. Implementing a
        # MutableMapping subclass could be better if we don't need to
        # support repeated tag names. Int and string tags with the same
        # name could still be supported fairly easily internally if there
        # are separate internal ints and strings dicts, and would give us
        # free length prefixing without having to separate out ints and
        # strings from the list each time want to write the tag.
        self.named_variables = []

        if not self.body and not self.data:
            if not isinstance(named_variables, Iterable):
                raise TypeError(
                    "named_variables must be an iterable"
                )

            for i, k, v in enumerate(named_variables):
                if not isinstance(k, str):
                    raise TypeError(
                        f"All keys must be strings, "
                        f"but got ({k}, {v}) at index {i}"
                    )
                elif not (isinstance(v, str) and isinstance(v, int)):
                    raise TypeError(
                        f"All values must be ints or strings, "
                        f"but got ({k}, {v}) at index {i}"
                    )

                self.named_variables.append((k, v))


    def _read_variable_type(
            self,
            src: RawIOBase,
            value_reader: Callable
    ) -> None:
        """
        Read a block of (string, datatype) pairs from the passed stream.

        Using a stream does the location arithmetic for you. No slicing
        needs to be done manually.

        The datatype is specified by the value_reader function at the
        moment. This will be hopefully be clearly annotated in future
        revisions using the TypeVar functionality in python's typing
        module.

        :param src: the stream to read from
        :param value_reader: a function that will take care of reading
        :return: nothing, appends to internal variable set
        """

        num_to_read = _read_uint32(src)

        for i in range(0, num_to_read):

            name = _read_prefixed_string(src)
            data = value_reader(src)

            self.named_variables.append((name, data))

    def _read_body(self) -> None:
        """
        Read the tags from stream.

        Overrides the empty _read_body method in the baseclass, called by
        the data property through _read_block.

        :return:
        """

        # This is kind of ugly. should rework internal methods to use
        # streams by default in another ticket so we get friendly io for
        # free? It would allow socketserver.StreamRequestHandler to be
        # used and a lot of code to be cleaned up to avoid manually
        # slicing everything.
        src = BytesIO(self._body_cache)

        #
        # Each named Integer Variable consists of 3 Parts:
        # - a 32bit Integer Variable that states the length of the name 'key_length'
        # - n Bytes containing said Name, where n is the length specified in the Integer beforhand 'key'
        # - a 32bit Integer containing the 'value' of the Named Integer
        # +------------------+-------------------+--------------+
        # | 4B  Int len(KEY) | nB KEY in LATIN-1 | 4B Int Value |
        # +------------------+-------------------+--------------+
        #
        self._read_variable_type(src, _read_uint32)
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
        self._read_variable_type(src, _read_prefixed_string)

    def _write_variable_type(
            self,
            dest_stream,  # not sure how to type this yet
            value_writer: Callable,
            src  # ditto here, pycharm complains that using Sized is better here.
    ) -> None:
        """
        Write the passed iterable to passed stream using the passed writer

        :param dest_stream:
        :param value_writer: 
        :return: 
        """

        _write_uint32(len(src))

        for name, value in src:
            _write_prefixed_string(dest_stream, name)
            value_writer(dest_stream, value)

    # compress_data probably shouldn't be passed at the moment, but fixing
    # that is out of the scope of this commit.
    def _write_body(self, compress_data: bool = True) -> None:
        """
        Write the body to internal _bytes_cache.

        Overrides the empty write_body method in Block, called by
        _write_body whenever a data property access is made.

        This is inefficient, but is meant to be temporary and fixable in
        the baseclass.

        :param compress_data: whether to compress the data.
        :return:
        """

        # write to a stream for easier record keeping
        dest = BytesIO()

        ints = list()
        strings = list()

        for key, value in self.named_variables:
            if type(value) is int:
                ints.append(value)
            elif type(value) is str:
                strings.append(value)
            else:
                #  this should be handled on add/append attempt instead
                raise ValueError(
                    f"Expected string or int values but got {value}"
                )

        self._write_variable_type(ints, _write_uint32)
        self._write_variable_type(strings, _write_prefixed_string)

        self._body_cache.extend(dest.getvalue())


INSTANCES_CAN_CHANGE_PREFIX.add(TagBlock)


# This behavior might be better placed on TagBlock class itself. Nothing
# uses it right now, neither in this library or Rebabel, but i'm not
# deleting it right away until there is some discussion around it.
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
