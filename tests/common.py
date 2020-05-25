from typing import ByteString, Generator, Tuple


def make_valid_bytestrings(
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

def bytestrings_tuple(bytes_like: ByteString) -> Tuple[bytes, bytearray, memoryview]:
    """
    Wraps above to produce a tuple.

    This prevents hitting empty generators during tests.

    :param bytes_like:
    :return:
    """
    return tuple(make_valid_bytestrings(bytes_like))
