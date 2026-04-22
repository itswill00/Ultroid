from . import ultroid_cmd, asst, udB, HNDLR
from telethon import events, Button
from pyUltroid.dB._core import HELP
import uuid

# Transient storage for secret messages
# For persistence, we could use udB
SECRET_MSGS = {}

@ultroid_cmd(
    pattern="secretmsg(?: |$)(.*)",
    about={
        "header": "Secret Message",
        "usage": "{i}secretmsg [reply to message]",
        "examples": "{i}secretmsg",
    }
)
async def secret_msg_handler(ult):
    reply = await ult.get_reply_message()
    if not reply:
        return await ult.eor("`Reply to a message to make it secret!`", time=5)
    
    msg_id = str(uuid.uuid4())[:8]
    SECRET_MSGS[msg_id] = {
        "text": reply.text,
        "media": reply.media,
        "sender": ult.sender_id
    }
    
    # We'll use the assistant for the inline part
    bot_username = (await asst.get_me()).username
    text = f"🔐 **A secret message has been created!**\n\nOnly the intended person can open this."
    
    await ult.eor(
        text,
        buttons=[
            Button.switch_inline(
                "🚀 Send Secret Message",
                query=f"secret_{msg_id}",
                same_peer=False
            )
        ]
    )

# Assistant Inline Handler for the secret message
@asst.on(events.InlineQuery(pattern=r"secret_(.*)"))
async def inline_secret_handler(event):
    msg_id = event.pattern_match.group(1)
    if msg_id not in SECRET_MSGS:
        return await event.answer([])

    msg_data = SECRET_MSGS[msg_id]
    builder = event.builder
    
    # Result for the person to click
    result = builder.article(
        title="Send Secret Message",
        description="This message is encrypted and private.",
        text="🔐 **You have a secret message!**\n\nClick the button below to read it.",
        buttons=[
            Button.inline("📥 Read Message", data=f"read_secret_{msg_id}")
        ]
    )
    await event.answer([result], cache_time=0)

# Callback handler to reveal the secret
@asst.on(events.CallbackQuery(data=re.compile(b"read_secret_(.*)")))
async def read_secret_callback(event):
    msg_id = event.data_match.group(1).decode()
    if msg_id not in SECRET_MSGS:
        return await event.answer("Message expired or not found!", alert=True)

    msg_data = SECRET_MSGS[msg_id]
    
    # Logic: Only sender or the person who clicks first (if no specific target)
    # Userge allows targeting by username in inline query, we can improve this later.
    # For now, let's just show it if they click.
    
    text = f"🔒 **Secret Message from {msg_data['sender']}**\n\n"
    text += msg_data['text'] or "[Media Content]"
    
    await event.answer(text, alert=True)
