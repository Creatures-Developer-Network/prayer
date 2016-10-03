from prayer import prayer, tag_block
from sys import argv

pray = prayer(argv[1])

i = 0
for block in pray.blocks:
    print("Block Type: %s\nBlock Name: %s" % (block['type'],block['name']))
    if block['type'] in ['ICHT','IMSG','MESG','CHAT','OMSG','OCHT','MOEP']:
        # write tag_block to Disk for analysis.
        filename = 'resources/%s%s.blk' % (block['type'],i)
        with open(filename, 'wb') as f:
            f.write(block['decompressed_data'])
            print('Wrote decompressed block data to %s' % filename)
            i += 1
        data = tag_block(block)
        for variable in data.named_variables:
            if type(variable[1]) == int:
                print('  INT Key: "%s" Value: %s'% variable)
            elif type(variable[1]) == str:
                print('  STR Key: "%s" Value: "%s"' % variable)