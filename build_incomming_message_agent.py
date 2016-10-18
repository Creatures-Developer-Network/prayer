from prayer.blocks import TagBlock
from datetime import datetime


date_sent = datetime.now().strftime('%Y%m%d%H%M%S')
sender_id = str(17827)
sender_nickname = "Bob"

block_name = name = sender_id + date_sent + "_message"

data = list(
    (
        ("Subject", "Test Message from Bob"),
        ("Message", "This Message was built by PRAYER!"),
        ("Date Sent", date_sent),
        ("Sender UserID", sender_id),
        ("AW Sender UserID", sender_id),
        ("Sender Nickname", sender_nickname),
        ("AW Sender Nickname", sender_nickname)
    )
)

with open('resources/%s.blk' % 'herpderp.agents', 'wb') as f:
    pray_file_data = bytes('PRAY', encoding='latin-1')
    pray_file_data += TagBlock.create_tag_block(block_type='IMSG', block_name=block_name, named_variables=data).block_data
    f.write(pray_file_data)
    