import zlib


class prayer:
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
        # The first 4 Byte contain the type of the Block
        pray_block_type = data[:4].decode('latin-1')
        # the following 128 Byte, contain the Name of the Block (ASCII or UTF-8, i dont know) padded with 'NUL' '\0'
        block_name = data[4:132].decode('latin-1').rstrip('\0')
        # then there is a 32 bit Integer, that states the compressed size/length of the data
        compressed_data_length = int.from_bytes(data[132:136], byteorder='little', signed=False)
        # right after that, there is another 32 bit Integer that states the uncompressed size/length of the data
        uncompressed_data_length = int.from_bytes(data[136:140], byteorder='little', signed=False)
        # then there is an 32 Bit Integer containing either a one or a zero, 1 = block data is compressed, 0 = block data is uncompressed
        if int.from_bytes(data[140:144], byteorder='little') == 1:
            compressed = True
        else:
            compressed = False
        # The Compressed and decompressed Data can each be found at offset 144 + the Length of the "compressed_data_length" Variable
        compressed_data = data[144:144 + compressed_data_length]
        if compressed:
            decompressed_data = zlib.decompress(compressed_data)
        else:
            decompressed_data = compressed_data
        # Now we put everything into a nice, clean Dict :D
        pray_block = {
            'type': pray_block_type,
            'name': block_name,
            'compressed_data_length': compressed_data_length,
            'uncompressed_data_length': uncompressed_data_length,
            'compressed_data': compressed_data,
            'decompressed_data': decompressed_data
        }
        # and add it to the 'blocks' list
        self.blocks.append(pray_block)
        # if there is any data Left, we pass it, in a recursive Fashion, to the '_extract_pray_blocks' function.
        if len(data[144 + compressed_data_length:]) != 0:
            self._extract_pray_blocks(data[144 + compressed_data_length:])


class tag_block:
    # A tag block contains named String and Integer Variables.
    # it has a List of Tuples named_variables which contains all the Named variables extracted form the given Data

    def __init__(self, block):
        self.mesg_data = bytearray(block['decompressed_data'])
        self.named_variables = list()
        # Integers
        number_of_integers = int.from_bytes(self.mesg_data[:4], byteorder='little')
        self._get_named_integer_variables(data=self.mesg_data[4:], count=number_of_integers)
        # Strings
        number_of_strings = int.from_bytes(self.str_data[:4], byteorder='little')
        self._get_named_string_variables(data=self.str_data[4:], count=number_of_strings)

    def _get_named_integer_variables(self, data, count):
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
            key_length = int.from_bytes(data[:4], byteorder='little')
            key = data[4:4 + key_length].decode('latin-1')
            value = int.from_bytes(data[4 + key_length:8 + key_length], byteorder='little')
            self.named_variables.append((key, value))
            self._get_named_integer_variables(data=data[8 + key_length:], count=count - 1)
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
            key_length = int.from_bytes(data[:4], byteorder='little')
            key = data[4:4 + key_length].decode('latin-1')
            value_length = int.from_bytes(data[4 + key_length:8 + key_length], byteorder='little')
            value = data[8 + key_length:8 + key_length + value_length].decode('latin-1')
            self.named_variables.append((key, value))
            self._get_named_string_variables(data=data[8 + key_length + value_length:], count=count - 1)
        else:
            self.str_data = data

    @staticmethod
    def generate_tag_block_data(named_variabe_list):
        ints = list()
        strings = list()
        for variable in named_variabe_list:
            if type(variable[1]) == int:
                ints.append(variable)
            elif type(variable[1] == str):
                strings.append(variable)
        tmp_ints = bytes(len(ints).to_bytes(length=4, byteorder='little'))
        for variable in ints:
            tmp_ints += (len(bytes(variable[0], encoding='latin-1')).to_bytes(length=4, byteorder='little'))
            tmp_ints += bytes(variable[0], encoding='latin-1')
            tmp_ints += variable[1].to_bytes(length=4, byteorder='little')
        tmp_strings = bytes(len(strings).to_bytes(length=4, byteorder='little'))
        for variable in strings:
            tmp_strings += (len(bytes(variable[0], encoding='latin-1')).to_bytes(length=4, byteorder='little'))
            tmp_strings += bytes(variable[0], encoding='latin-1')
            tmp_strings += (len(bytes(variable[1], encoding='latin-1')).to_bytes(length=4, byteorder='little'))
            tmp_strings += bytes(variable[1], encoding='latin-1')
        return tmp_ints + tmp_strings

    @staticmethod
    def generate_tag_block(type, name, compress_data, named_variable_list):
        data_block = tag_block.generate_tag_block_data(named_variable_list)
        uncompressed_length = len(data_block)
        if compress_data:
            data_block = zlib.compress(data_block)
            compress_data_bit = 1
        else:
            compress_data_bit = 0
        data = bytes(type, encoding='latin-1')
        data += bytes(name, encoding='latin-1').ljust(128, b'\0')
        data += len(data_block).to_bytes(length=4, byteorder='little')
        data += uncompressed_length.to_bytes(length=4, byteorder='little')
        data += compress_data_bit.to_bytes(length=4, byteorder='little')
        data += data_block
        return (data)
