# Ultroid - Unified AI Plugin
# Powered by centralized AI Core Engine (Groq, GPT, Claude, DeepSeek, Gemini)

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
    """Unified AI assistant handling text, vision, and research."""
    cmd = e.pattern_match.group(1).lower()
    query = e.pattern_match.group(2).strip()
    image_b64 = None
    use_search = False
    
    # Research flag check
    if query.startswith("--search ") or query.startswith("-s "):
        use_search = True
        query = query.replace("--search ", "", 1).replace("-s ", "", 1).strip()
    
    reply = await e.get_reply_message()
    
    # 1. Image handling (Vision)
    if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        dl = await reply.download_media()
        try:
            image_b64 = encode_image_base64(dl)
            os.remove(dl)
        except Exception as er:
            LOGS.exception(er)
            if os.path.exists(dl): os.remove(dl)

    # 2. Text fallback from reply
    if not query and reply and reply.text:
        query = reply.text

    if not query and not image_b64:
        return await e.eor(f"`[AI] Usage: .{cmd} <your question>`")

    # 3. Process via Unified Engine
    await run_ai_task(e, query, image_b64=image_b64, use_search=use_search)

# --------------------------------------------------------------------------
# PROVIDER SPECIFIC COMMANDS
# --------------------------------------------------------------------------

@ultroid_cmd(pattern="(gpt|claude|deepseek|gemini|groq)( (.*)|$)")
async def provider_ai(e):
    """Directly call a specific AI provider."""
    provider = e.pattern_match.group(1).lower()
    if provider == "claude": provider = "anthropic"
    
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    
    if not query and reply and reply.text:
        query = reply.text
        
    if not query:
        return await e.eor(f"`[AI] Usage: .{provider} <your question>`")
        
    await run_ai_task(e, query, provider=provider)

# --------------------------------------------------------------------------
# UTILITY COMMANDS
# --------------------------------------------------------------------------

@ultroid_cmd(pattern="summarize$")
async def summarize_msg(e):
    """Summarize replied text."""
    reply = await e.get_reply_message()
    if not reply or not reply.text:
        return await e.eor("`[AI] Reply to the message you want summarized.`")

    await run_ai_task(e, reply.text, system_override="Summarize the text in 3 concise bullet points in Indonesian.")

@ultroid_cmd(pattern="tldr( (.*)|$)")
async def tldr_chat(e):
    """Summarize last N messages."""
    match = e.pattern_match.group(1).strip()
    limit = max(10, min(int(match), 100)) if match.isdigit() else 50
    
    xx = await e.eor(f"`[AI] Reading last {limit} messages...`")
    collected = []
    async for msg in e.client.iter_messages(e.chat_id, limit=limit):
        if msg.text and not msg.out:
            sender = getattr(msg.sender, "first_name", "?") or "User"
            collected.append(f"{sender}: {msg.text.strip()}")
            
    if not collected:
        return await xx.edit("`[AI] No recent conversation found.`")
        
    prompt = "Summarize this conversation context into 5 key points in Indonesian:\n\n" + "\n".join(reversed(collected))[:3500]
    await run_ai_task(e, prompt, system_override="You are a conversation analyst. Be concise.")

@ultroid_cmd(pattern="search( (.*)|$)")
async def direct_search(e):
    """Perform real-time web research."""
    query = e.pattern_match.group(1).strip()
    if not query: return await e.eor("`[Search] Provide a query.`")
    
    xx = await e.eor("`[Search] Researching...`")
    results = await google_search(query)
    if not results: return await xx.edit("`[Search] No results found.`")
    
    out = f"🔍 **Research Results: {query}**\n\n"
    for i, r in enumerate(results[:5], 1):
        out += f"{i}. **[{r['title']}]({r['link']})**\n   _{r['body'][:120]}..._\n\n"
    await xx.edit(out, link_preview=False)

@ultroid_cmd(pattern="aimodel( (.*)|$)", fullsudo=True)
async def ai_settings(e):
    """Manage AI providers and models."""
    from pyUltroid.fns.ai_engine import DEFAULT_MODELS
    
    args = e.pattern_match.group(1).strip().split()
    if not args:
        provider = udB.get_key("DEFAULT_AI_PROVIDER") or "groq"
        return await e.eor(
            f"🤖 **AI Settings**\n\n"
            f"**Default Provider:** `{provider}`\n"
            f"**Usage:** `.aimodel <provider>` to set default.\n"
            f"**Supported:** `groq`, `openai`, `anthropic`, `deepseek`, `gemini`"
        )
    
    new_provider = args[0].lower()
    if new_provider not in DEFAULT_MODELS:
        return await e.eor(f"`[AI] Invalid provider. Choose from: {list(DEFAULT_MODELS.keys())}`")
        
    udB.set_key("DEFAULT_AI_PROVIDER", new_provider)
    await e.eor(f"`[AI] Default provider set to: {new_provider}`")

@ultroid_cmd(pattern="debug$", fullsudo=True)
async def ai_troubleshoot(e):
    """Analyze logs using AI."""
    xx = await e.eor("`[AI] Analyzing system logs...`")
    if not os.path.exists("ultroid.log"): return await xx.edit("`Log file not found.`")
    
    with open("ultroid.log", "r") as f:
        logs = "".join(f.readlines()[-50:])
        
    prompt = f"Identify errors in these logs and provide a solution in Indonesian:\n\n{logs}"
    await run_ai_task(e, prompt, system_override="You are a professional system debugger.")

__doc__ = """
**Unified AI Assistant**

- `.ai <query>` — Multi-provider AI query.
- `.ask --search <query>` — Web research enabled.
- `.chat` (reply to image) — Vision analysis.
- `.summarize` — Summarize replied text.
- `.tldr <count>` — Chat history summary.
- `.gpt`, `.claude`, `.deepseek` — Direct provider calls.
- `.search <query>` — Pure web search.
- `.aimodel <provider>` — Switch default provider.
"""
