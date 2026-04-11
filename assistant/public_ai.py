# Ultroid - Assistant Bot
# Token Bank & Verification System

import re
from telethon import Button
from pyUltroid.dB.base import KeyManager
from . import asst, callback, asst_cmd, udB, OWNER_ID, owner_and_sudos, get_string, inline_mention

# Database Managers
Bank = KeyManager("ULTROID_AI_TOKENS", cast=dict)
Verified = KeyManager("VERIFIED_AI_USERS", cast=list)

# Constants
STARTING_GIFT = 5000  # Default tokens for new verified users

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
    if event.sender_id in owner_and_sudos():
        # Sudoers should use the main bot, but we allow them here too
        pass
    elif not Verified.contains(event.sender_id):
        return await event.reply("`[Ultroid] Access Denied. Use /apply_ai to request verification.`")
    
    balance = Bank.get().get(str(event.sender_id), 0)
    if balance <= 0 and event.sender_id not in owner_and_sudos():
        return await event.reply("`[Ultroid Bank] Insufficient balance. Please contact owner for refill.`")

    query = event.pattern_match.group(2).strip()
    if not query:
        reply = await event.get_reply_message()
        if reply and reply.text:
            query = reply.text.strip()
            
    if not query:
        return await event.reply("`Usage: /ask <your question>`")

    # Import the worker from smart_reply (we will refactor this next)
    from plugins.smart_reply import _call_groq, _get_model
    from pyUltroid.fns.tools import get_stored_file
    import time
    from io import BytesIO

    processing = await event.reply("`[AI] Processing...`")
    start_time = time.time()
    
    # We will modify _call_groq to return (text, tokens)
    res_data = await _call_groq(query, return_usage=True)
    if not res_data:
        return await processing.edit("`[AI] API Error. Please try again later.`")
    
    ans, total_tokens = res_data
    duration = round(time.time() - start_time, 2)
    
    # Deduct tokens for non-sudoers
    if event.sender_id not in owner_and_sudos():
        new_balance = balance - total_tokens
        Bank.add({str(event.sender_id): max(0, new_balance)})
    
    model = _get_model()
    q_preview = query[:200].replace('\n', ' ')
    output = f"> \"{q_preview}\"\n\n{ans.strip()}\n"
    footer = f"\n**model**: `{model}`\n**detik**: `{duration}s`\n**token**: `{total_tokens}`"
    if event.sender_id not in owner_and_sudos():
        footer += f"\n**limit**: `-{total_tokens}`"

    if len(output) > 1000:
        with BytesIO(str.encode(output)) as out_file:
            out_file.name = "response.md"
            await event.reply(f"> \"{q_preview}\"{footer}", file=out_file)
        await processing.delete()
    else:
        await processing.edit(output + footer, link_preview=False)

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
        await asst.send_message(target_id, "`[Ultroid Bank] Sorry, your AI access request was rejected.`")
    except Exception:
        pass

# --------------------------------------------------------------------------
# CORE HELPER
# --------------------------------------------------------------------------

async def verify_and_deduct(event, tokens):
    """Check if user is verified and has enough tokens, then deduct."""
    uid = event.sender_id
    if uid in owner_and_sudos():
        return True # Unlimited
    
    if not Verified.contains(uid):
        await event.reply("`[Ultroid] Verification required. Use /apply_ai to request access.`")
        return False
    
    balance = Bank.get().get(str(uid), 0)
    if balance < tokens:
        await event.reply(f"`[BANK] Insufficient balance. Required: {tokens:,} | Available: {balance:,}`")
        return False
    
    # Deduct
    new_balance = balance - tokens
    Bank.add({str(uid): new_balance})
    return True
