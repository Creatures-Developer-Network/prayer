from typing import Union, ByteString, Any


# a hack for type checking behavior that seems contrary to the docs, but
# that may only be because I don't understand the typing module correctly.
def valid_bytestring(src: Any) -> bool:
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


def coerce_encoding(
        src: str,
        max_length: int = None,
        encoding: str='cp1252'
) -> bytes:
    """
    Force a string to match a given encoding and if passed, max length.

    The maximum length is checked after the string is encoded.

    :param src: the string to coerce to the encoding used by creatures
    :param max_length: a maximum length to use, if any.
    :param encoding: the encoding to coerce to.
    :return:
    """

    # This is more informative than the previous behavior of breaking
    # at write time, but it's bad. Maybe keep both an encoded and
    # string version around? Revisit in encoding fix ticket?

    encoded_value = bytes(src, encoding)
    # raise if it doesn't fit in a 128-byte null terminated string
    if max_length:
        if not isinstance(max_length, int):
            raise TypeError(
                f"Expected an int for max_length, not {max_length}"
            )
        elif max_length < 0:
            raise ValueError(
                "max_length cannot be negative"
            )
        elif len(encoded_value) > max_length:
            raise ValueError(
                "Encoded value is too long"
            )

    return encoded_value




