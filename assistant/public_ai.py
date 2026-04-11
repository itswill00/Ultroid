# Ultroid - Assistant Bot
# Token Bank & Verification System

import re
from telethon import Button
from pyUltroid.dB.base import KeyManager
from . import asst, callback, asst_cmd, udB, OWNER_ID, owner_and_sudos, get_string, inline_mention

# Database Managers
from pyUltroid.fns.ai_engine import Bank, Verified, STARTING_GIFT, fast_telegraph

# --------------------------------------------------------------------------
# ADMINISTRATIVE COMMANDS (Owner Only)
# --------------------------------------------------------------------------

@asst_cmd(pattern="gift( (.*)|$)", owner=True)
async def gift_tokens(event):
    """Grant tokens to a user by ID or reply."""
    args = event.pattern_match.group(1).strip().split()
    target_id = None
    amount = 0

    if event.is_reply:
        reply = await event.get_reply_message()
        target_id = reply.sender_id
        if args:
            try:
                amount = int(args[0])
            except ValueError:
                return await event.reply("`[BANK] Invalid amount.`")
    elif len(args) >= 2:
        try:
            target_id = int(args[0])
            amount = int(args[1])
        except ValueError:
            return await event.reply("`[BANK] Usage: /gift <id> <amount>`")
    
    if not target_id or amount <= 0:
        return await event.reply("`[BANK] Usage: Reply to user with /gift <amount> or use /gift <id> <amount>`")

    # Add to bank
    current_tokens = Bank.get().get(str(target_id), 0)
    new_total = current_tokens + amount
    Bank.add({str(target_id): new_total})
    
    await event.reply(f"`[BANK] Successfully granted {amount:,} tokens to {target_id}. New balance: {new_total:,}`")
    try:
        await asst.send_message(target_id, f"**[Ultroid Bank]**\nYou have received a gift of **{amount:,} tokens**!\nYour new balance is **{new_total:,} tokens**.")
    except Exception:
        pass

@asst_cmd(pattern="setbank( (.*)|$)", owner=True)
async def set_tokens(event):
    """Force set a user's balance."""
    args = event.pattern_match.group(1).strip().split()
    if len(args) < 2:
        return await event.reply("`[BANK] Usage: /setbank <id> <amount>`")
    
    try:
        target_id = str(args[0])
        amount = int(args[1])
        Bank.add({target_id: amount})
        await event.reply(f"`[BANK] Set balance for {target_id} to {amount:,}`")
    except ValueError:
        await event.reply("`[BANK] Invalid ID or amount.`")

@asst_cmd(pattern="checkbank( (.*)|$)", owner=True)
async def check_user_bank(event):
    """Check status of a user."""
    target_id = None
    args = event.pattern_match.group(1).strip()
    if event.is_reply:
        reply = await event.get_reply_message()
        target_id = reply.sender_id
    elif args:
        target_id = args
    
    if not target_id:
        return await event.reply("`[BANK] Provide ID or reply to a user.`")
    
    balance = Bank.get().get(str(target_id), 0)
    is_verified = Verified.contains(int(target_id)) if str(target_id).isdigit() else False
    
    status = "Verified" if is_verified else "Unverified"
    await event.reply(f"**[Ultroid Bank Status]**\nUser: `{target_id}`\nStatus: `{status}`\nBalance: `{balance:,} tokens`")

# --------------------------------------------------------------------------
# PERSONA MANAGEMENT (Owner Only)
# --------------------------------------------------------------------------

@asst_cmd(pattern="setsystem( (.*)|$)", owner=True)
async def set_ai_system(event):
    """Update the AI system prompt."""
    meta = event.pattern_match.group(1).strip()
    if not meta:
        return await event.reply("`[PERSONA] Usage: /setsystem <your instructions>`")
    
    udB.set_key("GROQ_SYSTEM_PROMPT", meta)
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

# --------------------------------------------------------------------------
# USER COMMANDS
# --------------------------------------------------------------------------

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

@asst_cmd(pattern="(ask|ai)( (.*)|$)")
async def public_ask(event):
    """Public AI command for Assistant Bot."""
    query = event.pattern_match.group(2).strip()
    if not query:
        reply = await event.get_reply_message()
        if reply and reply.text:
            query = reply.text.strip()
            
    if not query:
        return await event.reply("`Usage: /ask <your question>`")

    from pyUltroid.fns.ai_engine import run_ai_task
    await run_ai_task(event, query)

# --------------------------------------------------------------------------
# CALLBACK HANDLERS
# --------------------------------------------------------------------------

@callback(re.compile(r"ai_app_(\d+)"), owner=True)
async def approve_ai(event):
    target_id = int(event.data_match.group(1))
    if not Verified.contains(target_id):
        Verified.add(target_id)
        # Give starting gift if no balance exists
        curr = Bank.get().get(str(target_id), 0)
        if curr == 0:
            Bank.add({str(target_id): STARTING_GIFT})
            gift_msg = f" and received a starting gift of {STARTING_GIFT:,} tokens"
        else:
            gift_msg = ""
            
        await event.edit(f"`[BANK] User {target_id} has been approved{gift_msg}.`")
        try:
            await asst.send_message(target_id, f"**[Ultroid Bank]**\nYour AI access has been **Approved**!\nYou have `{Bank.get().get(str(target_id), 0):,} tokens` available.\n\nUsage: Send questions to this bot or use `/ask <question>`.")
        except Exception:
            pass
    else:
        await event.answer("User already verified.", alert=True)

@callback(re.compile(r"ai_rej_(\d+)"), owner=True)
async def reject_ai(event):
    target_id = int(event.data_match.group(1))
    await event.edit(f"`[BANK] Request from {target_id} rejected.`")
    try:
        await asst.send_message(target_id, f"`[Ultroid Bank] Sorry, your AI access request was rejected.`")
    except Exception:
        pass

# Legacy logic removed. All AI processing is now handled by pyUltroid.fns.ai_engine.

