# Ultroid - Unified AI Plugin
# Simplified: Groq (Primary) + Gemini (Fallback)

import os
from . import get_help
__doc__ = get_help("ai")

from pyUltroid.fns.ai_engine import google_search, run_ai_task
from pyUltroid.fns.tools import encode_image_base64
from . import LOGS, udB, ultroid_cmd

# --------------------------------------------------------------------------
# MAIN AI COMMANDS (.ai, .ask, .chat)
# --------------------------------------------------------------------------

@ultroid_cmd(pattern="(ai|ask|chat)( (.*)|$)")
async def unified_ai(e):
    """Unified AI assistant (Groq + Gemini Fallback)."""
    query = e.pattern_match.group(2).strip()
    image_b64 = None
    use_search = False
    
    if query.startswith("--search ") or query.startswith("-s "):
        use_search = True
        query = query.replace("--search ", "", 1).replace("-s ", "", 1).strip()
    
    reply = await e.get_reply_message()
    if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        dl = await reply.download_media()
        try:
            image_b64 = encode_image_base64(dl)
            os.remove(dl)
        except Exception:
            if os.path.exists(dl): os.remove(dl)

    if not query and reply and reply.text:
        query = reply.text

    if not query and not image_b64:
        return await e.eor("`[AI] Usage: .ai <question>`")

    await run_ai_task(e, query, image_b64=image_b64, use_search=use_search)

# --------------------------------------------------------------------------
# DIRECT PROVIDER OVERRIDES
# --------------------------------------------------------------------------

@ultroid_cmd(pattern="(groq|gemini)( (.*)|$)")
async def provider_override(e):
    """Directly call Groq or Gemini."""
    provider = e.pattern_match.group(1).lower()
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    
    if not query and reply and reply.text:
        query = reply.text
        
    if not query:
        return await e.eor(f"`[AI] Usage: .{provider} <question>`")
        
    await run_ai_task(e, query, provider=provider)

# --------------------------------------------------------------------------
# UTILITY COMMANDS
# --------------------------------------------------------------------------

@ultroid_cmd(pattern="summarize$")
async def summarize_msg(e):
    reply = await e.get_reply_message()
    if not reply or not reply.text:
        return await e.eor("`[AI] Reply to the message you want summarized.`")
    await run_ai_task(e, reply.text, system_override="Summarize this in 3 bullet points in Indonesian.")

@ultroid_cmd(pattern="tldr( (.*)|$)")
async def tldr_chat(e):
    match = e.pattern_match.group(1).strip()
    limit = max(10, min(int(match), 100)) if match.isdigit() else 50
    xx = await e.eor(f"`[AI] Reading last {limit} messages...`")
    collected = []
    async for msg in e.client.iter_messages(e.chat_id, limit=limit):
        if msg.text and not msg.out:
            sender = getattr(msg.sender, "first_name", "?") or "User"
            collected.append(f"{sender}: {msg.text.strip()}")
    if not collected: return await xx.edit("`[AI] No recent conversation found.`")
    prompt = "Summarize this conversation into 5 key points in Indonesian:\n\n" + "\n".join(reversed(collected))[:3500]
    await run_ai_task(e, prompt, system_override="Analyze this conversation concisely.")

@ultroid_cmd(pattern="debug$", fullsudo=True)
async def ai_troubleshoot(e):
    xx = await e.eor("`[AI] Analyzing system logs...`")
    if not os.path.exists("ultroid.log"): return await xx.edit("`Log file not found.`")
    with open("ultroid.log", "r") as f:
        logs = "".join(f.readlines()[-50:])
    prompt = f"Identify errors in these logs and provide a solution in Indonesian:\n\n{logs}"
    await run_ai_task(e, prompt, system_override="You are a professional system debugger.")

__doc__ = """
**Unified AI Assistant (Groq + Gemini)**

- `.ai <query>` — AI query (Groq/Gemini).
- `.ask --search <query>` — Web research.
- `.chat` (reply to image) — Vision analysis.
- `.summarize` — Summarize text.
- `.tldr <count>` — Chat history summary.
- `.groq` / `.gemini` — Explicit provider call.
"""
