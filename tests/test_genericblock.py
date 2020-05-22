import zlib
from itertools import chain, product
from typing import ByteString, Generator

import pytest
from prayer.blocks import Block, BLOCK_HEADER_LENGTH, BLOCK_HEADER_STRUCT


class DerivedBlock(Block):
    """

    An example of how easy defining a new block type could be.

    Block format consists of a prefix, a header, and a body.

    Exposed properties using @property decorators should include:
    * data, the entire data of the block as bytes
    * body, the data of only the non-header part of the block.

    there may also be _compressed versions of the above that return zlib
    compressed versions of the same data.

    Reading and writing headers is common to all blocks and can be
    inherited, but the block prefix and body I/O are type-dependent.

    Ideally, you should only need to override:
    * default_type_string, a class-level variable storing the block prefix
    * _read_block_body(self, source: ByteString) -> None
    * _write_block_body(self, compress_data: bool = False) -> None

    The above methods will be called by _read_block and _write_block.

    Having prefixes stored on each block class lets us generate sets of
    block types that we can expect at a given point. This has a lot of
    uses.

    Implementing file formats can be reduced to subclassing or
    instantiating a PRAY reader that takes a different list of subclasses.

    Implementing rudimentary creature export support? It could look
    something like this:

    .. code-block :: python
        valid_blocks = { CreaBlock, GeneBlock, DsExBlock, PhotBlock  }

    This would also be useful for Rebabel. The way it's currently
    implemented, manually entering the string headers, means tracking down
    a bug caused by a typo could waste developer time. If the name of a
    class isn't found, the IDE or interpreter will immediately let us know
    there is an invalid symbol.

    _read_block should create a memoryview of the data source. That view
    then gets passed to _read_header and _read_block_body. Memoryviews
    are sliceable references to an original data source that do not copy
    the underlying data, only point to it. This means many operations are
    far more efficient on a memoryview than on a bytes object.

    If we migrate to 3.8 in the future, we can have .data and .body
    properties return read-only memoryviews to avoid any extra copy
    operations.


    """

    # replaces "NONE" that generic blocks have
    default_type_string: str = "TEST"

    def _read_block_body(self, body_source: memoryview) -> None:
        """

        Read the block's body and fill any internal variables.

        Also store the binary data of the source.

        This method is called by _read_block.

        Memoryviews are sliceable references to byestring objects that
        support most of the same operations. Slicing one returns another
        memoryview without copying any of the underlying contents. See
        above or the python doc for more information.

        :param body_source: the source of the body
        :return:
        """
        # set internal variables here
        pass

    def _write_block_body(self, compress_data: bool = False) -> None:
        """
        Write the body contents to the internal data cache bytearray.

        Doesn't return anything, use the .data or .body properties to
        access the result afterward.

        :param compress_data: whether to compress the data
        :return:
        """
        # serialize internal variables here
        pass


class TestTypeSetter:

    @pytest.mark.parametrize("bad_string", ["_", "bad", "toolong"])
    def test_base_setter_raises_value_error_on_bad_length(self, bad_string):
        """
        type.setter raises ValueError if the prefix set isn't 4 characters long
        """
        b = Block()
        with pytest.raises(ValueError):
            b.type = bad_string
        assert b.type == "NONE"

    @pytest.mark.parametrize("valid", ("fake", "four"))
    def test_setter_sets_type_for_valid_values(self, valid):
        """
        type.setter changes the type for four letter strings
        """
        fake = valid
        b = Block()
        b.type = fake
        assert b.type == fake

    def test_setter_calls_on_subclasses_raise_typerror(self):
        """
        Setting prefix on subclasses of Block raises TypeError
        """
        d = DerivedBlock()
        with pytest.raises(TypeError):
            d.type = "TYPE"


class TestNameSetter:

    @pytest.mark.parametrize(
        "bad_name",
        (
            "ﬁ"  # fi ligature in unicode, U+FB01
            "☎",  # telephone unicode
            "f" * 128  # too long, doesn't allow for null byte at end
        )
    )
    def test_name_setter_raises_value_error_invalid_values(self, bad_name):
        b = Block()
        with pytest.raises(ValueError):
            b.name = bad_name

    @pytest.mark.parametrize(
        "valid_name",
        (
            "a",
            "name.spr",
            "name.wav",
            "bg.blk",
            "a" * 127
        )
    )
    def test_name_setter_sets_name_on_good_values(self, valid_name):
        b = Block()
        b.name = valid_name
        assert b.name == valid_name


def make_valid_datasource_types(
        bytes_like: ByteString) -> Generator[bytes, bytearray, memoryview]:
    """
    Helper function, make a version in every valid bytestring type

    :param bytes_like: will be returned in every ByteString type
    :return:
    """
    for t in {bytes, bytearray, memoryview}:
        if isinstance(bytes_like, t):
            yield bytes_like
        else:
            yield t(bytes_like)

# helpers useful for testing the block setters
VALID_SOURCE_DATATYPE_SAMPLES = make_valid_datasource_types(b"test")
BAD_SOURCE_DATATYPE_SAMPLES = (
    "string",
    1,
    [],
    (3, 'a')
)
BAD_BODY_DATA_SAMPLES = (
    b"a" * 128,  # too long
    b"a"  # too short
)


class TestBodySetterAlone:

    @pytest.mark.parametrize(
        "data_source",
        VALID_SOURCE_DATATYPE_SAMPLES
    )
    def test_sets_body_with_valid_types(self, data_source):
        b = Block()
        b.body = data_source
        assert b.body == bytes(data_source)

    @pytest.mark.parametrize(
        "bad_arg_type",
        BAD_SOURCE_DATATYPE_SAMPLES
    )
    def test_typerror_on_bad_types(self, bad_arg_type):
        b = Block()
        with pytest.raises(TypeError):
            b.body = bad_arg_type


class TestDataSetterAlone:

    @pytest.mark.parametrize(
        "raw_body,compress",
        product(
            (b"test data goes here lets hope its long enough aaaa", ),
            (True, False)
        )
    )
    def test_sets_values_correctly(self, raw_body, compress):
        final_body = raw_body
        if compress:
            final_body = zlib.compress(final_body)

        data = bytearray(BLOCK_HEADER_STRUCT.pack(
            b"NONE",
            b"test_name",
            len(raw_body), len(final_body),
            int(compress)
        ))
        data.extend(final_body)

        b = Block()
        b.data = data
        assert b.type == "NONE"
        assert b.name == "test_name"
        assert b.body == final_body

    @pytest.mark.parametrize("bad_data_type", BAD_SOURCE_DATATYPE_SAMPLES)
    def test_typeerror_on_bad_source_type(
            self,
            bad_data_type
    ):
        b = Block()
        with pytest.raises(TypeError):
            b.data = bad_data_type

    @pytest.mark.parametrize(
        "truncated_header",
        (
            chain(
                make_valid_datasource_types(b""),
                make_valid_datasource_types(b"\0"),
                make_valid_datasource_types(b"\0" * (BLOCK_HEADER_LENGTH - 1))
            )
        )
    )
    def test_valueerror_on_truncated_header(self, truncated_header):
        b = Block()
        with pytest.raises(ValueError):
            b.data = truncated_header

    @pytest.mark.parametrize(
        "wrong_length_uncompressed_body",
        BAD_BODY_DATA_SAMPLES
    )
    def test_valuerror_on_wrong_length_uncompressed_body(
            self,
            wrong_length_uncompressed_body
    ):
        bad_data = bytearray(BLOCK_HEADER_STRUCT.pack(
            b"NONE",
            b"test block",
            50, 50,
            0
        ))
        bad_data.extend(wrong_length_uncompressed_body)

        for type_variant in make_valid_datasource_types(bad_data):
            with pytest.raises(ValueError):
                block = Block()
                block.data = type_variant

    @pytest.mark.parametrize(
        "wrong_compressed_length",
        map(
            zlib.compress,
            BAD_BODY_DATA_SAMPLES
        )
    )
    def test_valueerror_on_wrong_compressed_length(
        self,
        wrong_compressed_length
    ):
        bad_data = bytearray(BLOCK_HEADER_STRUCT.pack(
            b"NONE",
            b"test block",
            50, 50,
            1
        ))
        bad_data.extend(wrong_compressed_length)

        for type_variant in make_valid_datasource_types(bad_data):
            with pytest.raises(ValueError):
                block = Block()
                block.data = type_variant

    @pytest.mark.parametrize(
        "decompresses_to_wrong_length",
        map(
            zlib.compress,
            BAD_BODY_DATA_SAMPLES
        )
    )
    def test_valueerror_on_wrong_decompressed_length(
            self,
            decompresses_to_wrong_length
    ):
        bad_data = bytearray(BLOCK_HEADER_STRUCT.pack(
            b"NONE",
            b"test block",
            50, len(decompresses_to_wrong_length),
            1
        ))
        bad_data.extend(decompresses_to_wrong_length)

        for type_variant in make_valid_datasource_types(bad_data):
            with pytest.raises(ValueError):
                block = Block()
                block.data = type_variant



