import zlib
import os
from collections import MutableSequence
from prayer.blocks import Block, TagBlock



class Prayer:
    # This list contains all the Blocks the given PRAY file contains.
    blocks = list()

    def __init__(self, pray):
        if type(pray) == bytes:
            self.data = bytearray(pray)
        elif type(pray) == bytearray:
            self.data = pray
        else:
            raise TypeError('Only bytes or a bytearray are accepted! a %s was given.' % type(pray))
        # Every PRAY File begins with 4 Bytes, containg the word 'PRAY' coded in ASCII)
        # if the File does not contain the Header, it is propably not a PRAY File!
        if self.data[:4].decode('latin-1') != "PRAY":
            raise TypeError('The given File "%s" is not a PRAY File! (PRAY Header is missing)' % pray)
        # Strip of the PRAY Header and set the variable data to a Bytearray containing the Data.
        self.data = self.data[4:]
        # this function handles the Date and extracts all pray Blocks, and appends them to the `blocks` list.
        self._extract_pray_blocks(self.data)

    def _extract_pray_blocks(self, data):
        compressed_data_length = int.from_bytes(data[132:136], byteorder='little', signed=False)
        self.blocks.append(Block(data))
        if len(data[144 + compressed_data_length:]) != 0:
            self._extract_pray_blocks(data[144 + compressed_data_length:])