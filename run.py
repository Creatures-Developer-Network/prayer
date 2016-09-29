from prayer import prayer, tag_block
from sys import argv

pray = prayer(argv[1])

for block in pray.blocks:
    print("Block Type: %s\nBlock Name: %s" % (block['type'],block['name']))
    if block['type'] in ['ICHT','IMSG','MESG','CHAT']:
        # write tag_block to Disk for analysis.
        with open('resources/%s.blk' % block['type'], 'wb') as f:
            f.write(block['decompressed_data'])

        data = tag_block(block)
        for variable in data.named_variables:
            if type(variable[1]) == int:
                print('  INT Key: "%s" Value: %s'% variable)
            elif type(variable[1]) == str:
                print('  STR Key: "%s" Value: "%s"' % variable)
        # generate tag_block based on a list of named variables originaly extracted from the decompressed data and
        # compare it to the original tag_block
        print(data.generate_tag_block(data.named_variables))
        print(block['decompressed_data'])
        if data.generate_tag_block(data.named_variables) == block['decompressed_data']:
            print("MATCH!")