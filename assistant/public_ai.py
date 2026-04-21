# Ultroid - Assistant Bot
# Token Bank & Verification System

import re

from telethon import Button

from pyUltroid import LOGS, asst, udB
from pyUltroid._misc import owner_and_sudos
from pyUltroid._misc._assistant import asst_cmd, callback

# Core Engine Logic
from pyUltroid.fns.ai_engine import STARTING_GIFT, Bank, Verified
from pyUltroid.fns.helper import inline_mention

# Re-define OWNER_ID locally or use safely from udB
OWNER_ID = udB.get_key("OWNER_ID")

# ────────────────────────────────────────────────────────────────────────--
# ADMINISTRATIVE COMMANDS (Owner Only)
# ────────────────────────────────────────────────────────────────────────--

@asst_cmd(pattern="gift( (.*)|$)", owner=True)
async def gift_tokens(event):
    """Grant tokens to a user by ID or reply."""
    args = event.pattern_match.group(1).strip().split()
    target_id = None
    amount = 0

    reply = await event.get_reply_message()
    if reply:
        target_id = reply.sender_id
        if args: amount = int(args[0])
    elif len(args) == 2:
        target_id = int(args[0])
        amount = int(args[1])

    if not target_id or not amount:
        return await event.reply("`Usage: /gift <user_id> <amount> or reply to a message with /gift <amount>`")

    current_bank = Bank.get() or {}
    current_balance = current_bank.get(str(target_id), 0)
    current_bank[str(target_id)] = current_balance + amount
    Bank.add(current_bank)

    await event.reply(f"`[Ultroid Bank] Successfully gifted {amount:,} tokens to {target_id}.`")

@asst_cmd(pattern="setbank( (.*)|$)", owner=True)
async def set_user_tokens(event):
    """Directly set a user's token balance."""
    args = event.pattern_match.group(1).strip().split()
    if len(args) != 2:
        return await event.reply("`Usage: /setbank <user_id> <amount>`")

    uid, amount = args[0], int(args[1])
    current_bank = Bank.get() or {}
    current_bank[str(uid)] = amount
    Bank.add(current_bank)
    await event.reply(f"`[Ultroid Bank] Balance for {uid} set to {amount:,} tokens.`")

@asst_cmd(pattern="checkbank( (.*)|$)", owner=True)
async def check_user_tokens(event):
    """Check a specific user's balance."""
    uid = event.pattern_match.group(1).strip()
    if not uid:
        reply = await event.get_reply_message()
        if reply: uid = reply.sender_id

    if not uid:
        return await event.reply("`Usage: /checkbank <user_id> or reply to a message.`")

    balance = Bank.get().get(str(uid), 0)
    await event.reply(f"`[Ultroid Bank] User {uid} has {balance:,} tokens.`")

# ────────────────────────────────────────────────────────────────────────--
# PERSONA MANAGEMENT
# ────────────────────────────────────────────────────────────────────────--

@asst_cmd(pattern="setsystem( (.*)|$)", owner=True)
async def set_ai_system(event):
    """Directly update the global AI system prompt."""
    prompt = event.pattern_match.group(1).strip()
    if not prompt:
        return await event.reply("`Usage: /setsystem <new prompt content>`")

    udB.set_key("GROQ_SYSTEM_PROMPT", prompt)
    await event.reply("`[PERSONA] System Prompt updated successfully.`")

@asst_cmd(pattern="getsystem$", owner=True)
async def get_ai_system(event):
    """Retrieve the current system prompt."""
    prompt = udB.get_key("GROQ_SYSTEM_PROMPT")
    if not prompt:
        return await event.reply("`[PERSONA] Currently using default Technical System Architect prompt.`")
    await event.reply(f"**[Current System Prompt]**\n\n`{prompt}`")

@asst_cmd(pattern="resetsystem$", owner=True)
async def reset_ai_system(event):
    """Reset to default prompt."""
    udB.del_key("GROQ_SYSTEM_PROMPT")
    await event.reply("`[PERSONA] System Prompt reset to default.`")

# ────────────────────────────────────────────────────────────────────────--
# USER COMMANDS
# ────────────────────────────────────────────────────────────────────────--

@asst_cmd(pattern="apply_ai$")
async def apply_ai_gate(event):
    """Users apply for AI access."""
    if event.sender_id in owner_and_sudos():
        return await event.reply("`[Ultroid] You are an admin. Tokens are unlimited for you.`")

    if Verified.contains(event.sender_id):
        balance = Bank.get().get(str(event.sender_id), 0)
        return await event.reply(f"`[Ultroid] You are already verified.`\nBalance: `{balance:,} tokens`")

    mention = inline_mention(event.sender)
    await event.reply("`[Ultroid] Request sent. Please wait for owner approval.`")

    # Send to owner
    buttons = [
        [
            Button.inline("Approve ✅", data=f"ai_app_{event.sender_id}"),
            Button.inline("Reject ❌", data=f"ai_rej_{event.sender_id}")
        ]
    ]
    await asst.send_message(
        OWNER_ID,
        f"**[AI Access Request]**\nUser: {mention} `[{event.sender_id}]` wants to use Ultroid AI.",
        buttons=buttons
    )

@asst_cmd(pattern="balance$")
async def user_balance(event):
    """Check own balance."""
    if event.sender_id in owner_and_sudos():
        return await event.reply("`[Ultroid Bank] Status: Master/Sudo (Unlimited)`")

    if not Verified.contains(event.sender_id):
        return await event.reply("`[Ultroid Bank] Status: Unverified. Use /apply_ai to start.`")

    balance = Bank.get().get(str(event.sender_id), 0)
    await event.reply(f"**[Ultroid Bank]**\nYour current balance: `{balance:,} tokens`.")

@asst_cmd(pattern="(ask|ai)(?:@\\w+)?( (.*)|$)")
async def public_ask(event):
    """Public AI command for Assistant Bot."""
    LOGS.info(f"[Asst Bot] /ai command triggered by user {event.sender_id}")
    query = event.pattern_match.group(2).strip()
    if not query:
        return await event.reply("`[Usage] /ask <pertanyaan>`")

    from pyUltroid.fns.ai_engine import run_ai_task
    await run_ai_task(event, query)

# ────────────────────────────────────────────────────────────────────────--
# CALLBACK HANDLERS
# ────────────────────────────────────────────────────────────────────────--

@callback(re.compile("ai_(app|rej)_(.*)"))
async def ai_callback_handler(event):
    if event.sender_id != OWNER_ID:
        return await event.answer("Owner Only!", alert=True)

    action = event.pattern_match.group(1).decode("utf-8")
    target_id = int(event.pattern_match.group(2).decode("utf-8"))

    if action == "app":
        if not Verified.contains(target_id):
            Verified.add(target_id)
            # Give starting gift
            current_bank = Bank.get() or {}
            current_bank[str(target_id)] = current_bank.get(str(target_id), 0) + STARTING_GIFT
            Bank.add(current_bank)

            await event.edit(f"`User {target_id} approved and gifted {STARTING_GIFT:,} tokens.`")
            await asst.send_message(target_id, f"`[Ultroid] Congratulations! Your AI access is approved.`\nStarting balance: `{STARTING_GIFT:,} tokens`.")
        else:
            await event.answer("User already verified.", alert=True)
    else:
        await event.edit(f"`Request from {target_id} rejected.`")
        await asst.send_message(target_id, "`[Ultroid] Sorry, your AI access request was rejected.`")
