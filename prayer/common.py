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
