import zlib
from collections import MutableSequence
from typing import ByteString

METADATA_HEADER_LENGTH = 144

class Block:
    """

    Baseclass for PRAY blocks.

    The following functions should be overridden by subclasses to
    extend functionality:
    * _read_block_data
    * _write_block_data

    All PRAY blocks start with a metadata header structured as follows:
    +----------------+-----------------+------------------------------+
    | type/size      | variable        | description                  |
    +================+=================+==============================+
    | 4 Bytes        | type            | type of the block            |
    +----------------+-----------------+------------------------------+
    | 128 Bytes      | name            | Name of the block, remainder |
    |                |                 | is padded with zeroes        |
    +----------------+-----------------+------------------------------+
    | 32-bit Integer | body_length     | uncompressed data size       |
    +----------------+-----------------+------------------------------+
    | 32-bit Integer |  | if compressed, the size when |
    |                |                 | zipped. otherwise same as    |
    |                |                 | above.                       |
    +----------------+-----------------+------------------------------+
    | 32-bit Integer | compressed      | The first bit should be set  |
    |                |                 | to 1 if the data is zipped.  |
    +----------------+-----------------+------------------------------+

    The following attributes and/or properties are exposed:
    * type - the type of this PRAY block
    * name - the name of this block
    * data - the uncompressed binary representation of this block
    * data_compressed - compressed version of this block's data
    * compressed - whether this block is compressed or not

    """

    # override this in subclasses as well
    default_type_string: str = "NONE"

    def __init__(self, source: ByteString = None):
        """

        Construct a PRAY block, optionally from a passed ByteString.

        ByteStrings may be bytes, bytearrays, a memoryview,
        or a subclass of one of those types.

        :param source: a ByteString object
        """
        self.type = self.default_type_string
        self.name: str = ""
        self.data = bytearray(self.type, "latin-1")

        self._body_cache = None
        self._body_cache_compressed = None

        self._compressed: bool = False

        if source:
            self._read_block_data(data=source)

    @property
    def data(self) -> bytes:
        """
        Get the serialized version of this block

        :return: bytes
        """
        return bytes(self._write_block_data(compress_data=False))

    @property
    def body(self) -> bytes:


    @data.setter
    def data(self, block_data: ByteString) -> None:
        self._read_block_data(data=block_data)

    @property
    def compressed_data(self) -> bytes:
        return self._write_block_data()

    @compressed_data.setter
    def compressed_data(self, block_data: ByteString) -> None:
        self._read_block_header(data=block_data)

    @property
    def compressed(self) -> bool:
        return self._compressed


    def _read_block_header(self, data: ByteString) -> None:
        """
        Read the header of a single block.

        :param data:
        :return:
        """

        # The first 4 Byte contain the type of the Block
        self.type = data[:4].decode("latin-1")
        # the following 128 Byte, contain the Name of the Block in latin-1
        # padded with 'NUL' '\0'
        self.name = data[4:132].decode("latin-1").rstrip("\0")
        # then there is a 32 bit Integer, that states the compressed
        # size/length of the data
        data_length = int.from_bytes(data[132:136], byteorder="little", signed=False)
        # right after that, there is another 32 bit Integer that states the
        # uncompressed size/length of the data.
        uncompressed_data_length = int.from_bytes(
            data[136:140], byteorder="little", signed=False
        )
        # then there is an 32 Bit Integer containing either a one or a zero, 1
        # = block data is compressed, 0 = block data is uncompressed
        if (
            int.from_bytes(data[140:METADATA_HEADER_LENGTH], byteorder="little") == 1
            and data_length != uncompressed_data_length
        ):
            self.compressed = True
        else:
            self.compressed = False
        # The Compressed and decompressed Data can each be found at offset 144
        # + the Length of the "self.data_length" Variable
        body_raw = data[
            METADATA_HEADER_LENGTH : METADATA_HEADER_LENGTH + data_length
        ]

        if self.compressed:
            self._data_cache = zlib.decompress(body_raw)
        else:
            self._data_cache = body_raw

    def _write_block_header(self, compress_data: bool = False) -> bytes:
        """

        Return the data of the block, containing:
        * block type header
        * name
        * block length when uncompressed
        * block length after compression is applied, if any
        * a flag block with a bit indicating compression

        See class docstring for full info

        :param compress_data: whether to compress the _data of a block.
        :return: the block as bytes
        """

        data_block = self._data
        uncompressed_length = len(data_block)
        if compress_data:
            data_block = zlib.compress(data_block)
            compress_data_bit = 1
        else:
            compress_data_bit = 0
        data = bytes(self.type, encoding="latin-1")
        data += bytes(self.name, encoding="latin-1").ljust(128, b"\0")
        data += len(data_block).to_bytes(length=4, byteorder="little")
        data += uncompressed_length.to_bytes(length=4, byteorder="little")
        data += compress_data_bit.to_bytes(length=4, byteorder="little")
        data += data_block
        return data

    def _read_block_data(self, data: ByteString) -> None:
        """
        Overrideable function for deserializing a block.

        :param data:
        :return:
        """
        if len(data) < 144:
            raise ValueError("Data too short to be a valid PRAY block of any type")

        self._read_block_header(data)
        self._body_cache = memoryview(self.datadata)144:]

    def _write_block_data(self, compress_data: bool = False) -> bytes:
        """

        Overrideable function for serializing the block.

        :param compress_data:
        :return:
        """
        tmp = bytearray()
        tmp.extend(self._write_block_header(compress_data=True))
        return bytes(tmp)




class TagBlock(Block):
    def __init__(self, data):
        """docstring :D"""
        Block.__init__(self, data)

    @staticmethod
    def create_tag_block(block_type, block_name, named_variables) -> None:
        tmp_tag_block = TagBlock(Block().data)
        tmp_tag_block.type = block_type
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

    def _get_named_integer_variables(self, data, count) ->:
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
