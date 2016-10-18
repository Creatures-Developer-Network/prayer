from prayer.prayer import Pray
from prayer.blocks import TagBlock
from sys import argv

with open(argv[1],'rb') as f:
    pray = Pray( f.read())
i = 0
for block in pray.blocks:
    print("Block Type: %s\nBlock Name: %s" % (block.type,block.name))
    if block.type in ['ICHT','IMSG','MESG','CHAT','OMSG','OCHT','MOEP']:
        # write tag_block to Disk for analysis.
        filename = 'resources/%s%s.blk' % (block.type,i)
        with open(filename, 'wb') as f:
            f.write(block.data)
            print('Wrote decompressed block data to %s' % filename)
            i += 1
        tag_block = TagBlock(block.block_data)
        for variable in tag_block.named_variables:
            if type(variable[1]) == int:
                print('\tINT Key: "%s" Value: %s' % variable)
            elif type(variable[1]) == str:
                print('\tSTR Key: "%s" Value: "%s"' % variable)