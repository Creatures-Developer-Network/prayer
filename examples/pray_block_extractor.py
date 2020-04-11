#!/bin/python3
from prayer.prayer import Pray
from sys import argv
import os

with open(argv[1], "rb") as f:
    pray = Pray(f.read())
i = 0
for block in pray.blocks:
    print(block.type)
    print("Block Type: %s\nBlock Name: %s" % (block.type, block.name))
    with open("./%s-%s-%s.blk" % (os.path.basename(argv[1]), block.type, i), "wb") as f:
        f.write(block._block_data)
        print("Wrote decompressed block data to %s" % filename)
    i += 1
