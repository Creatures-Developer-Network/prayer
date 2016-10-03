from prayer import tag_block
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

with open('resources/%s.blk' % 'aw_in_message_from_bob.agents', 'wb') as f:
    f.write(
        bytes(
            'PRAY', encoding='latin-1') + tag_block.generate_tag_block(
            type='IMSG',
            name=block_name,
            compress_data=False,
            named_variable_list=data
        )
    )
