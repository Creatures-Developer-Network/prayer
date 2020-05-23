#!/bin/python3
from prayer.prayer import Pray
from prayer.blocks import TagBlock
from sys import argv
import os

for file in argv[1:]:
    with open(file, "rb") as f:
        pray = Pray(f.read())
    fixed_pray_file_data = bytes("PRAY", encoding="latin-1")
    for block in pray.blocks:
        print(block.prefix)
        if block.prefix not in ["CREA", "GENE", "GLST", "PHOT", "warp"]:
            print("YEPP Corrupted")
            print(block.block_data.hex())
        else:
            if block.prefix == "warp":
                tag_block = TagBlock(block.block_data)
                for variable in tag_block.named_variables:
                    if type(variable[1]) == int:
                        print('\tINT Key: "%s" Value: %s' % variable)
                    elif type(variable[1]) == str:
                        print('\tSTR Key: "%s" Value: "%s"' % variable)
            print("Block Type: %s\nBlock Name: %s" % (block.prefix, block.name))
            fixed_pray_file_data += block.zblock_data
    if file.endswith(".warp.detected_broken"):
        print(file.rsplit(".", 1)[0])
        with open(file.rsplit(".", 1)[0], "wb") as f:
            f.write(fixed_pray_file_data)
