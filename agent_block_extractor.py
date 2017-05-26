#!/bin/python3
from prayer.prayer import Pray
from sys import argv
import os

with open(argv[1], 'rb') as f:
    pray = Pray(f.read())
i = 0
for block in pray.blocks:
    print(block.type)
    print("Block Type: %s\nBlock Name: %s" % (block.type, block.name))
    if block.type in ['DSAG', 'AGNT']:
        # write tag_block to Disk for analysis.
        filename = 'resources/%s%s%s.blk' % (os.path.basename(argv[1]),block.type, i)
        with open(filename, 'wb') as f:
            f.write(block.data)
            print('Wrote decompressed block data to %s' % filename)
            i += 1