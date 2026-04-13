# Ultroid - Smart Reply Plugin (Refactored)
# Powered by centralized AI Core Engine
"""
» Commands Available -

• `{i}ask <question>`
    Ask AI for any technical information.
    Add `--search` to enable real-time web research.

• `{i}summarize` (reply to message)
    Get a concise summary of a replied text message.

• `{i}tldr <count>`
    Summarize the last N messages in the chat.

• `{i}search <query>`
    Direct web search results.

• `{i}debug`
    Autonomous log analysis and troubleshooting.

• `{i}aimodel`
    View or switch the active AI model.
"""
from . import udB, ultroid_cmd, LOGS, HNDLR
from pyUltroid._misc import owner_and_sudos
from pyUltroid.fns.ai_engine import run_ai_task, google_search
import os

@ultroid_cmd(pattern="ask( (.*)|$)")
async def ask_ai(e):
    """Unified AI assistant via .ask command."""
    question = e.pattern_match.group(1).strip()
    use_search = False
    
    if question.startswith("--search "):
        use_search = True
        question = question.replace("--search ", "", 1).strip()
    elif question.startswith("-s "):
        use_search = True
        question = question.replace("-s ", "", 1).strip()

    # Accept question from replied message if not provided inline
    if not question:
        reply = await e.get_reply_message()
        if reply and reply.text:
            question = reply.text.strip()

    if not question:
        return await e.eor("`[AI] Example: .ask What is machine learning?`")

    # Hand off to centralized engine
    await run_ai_task(e, question, use_search=use_search)


@ultroid_cmd(pattern="summarize$")
async def summarize_msg(e):
    reply = await e.get_reply_message()
    if not reply or not reply.text:
        return await e.eor("`[AI] Reply to the message you want summarized.`")

    xx = await e.eor("`[AI] Summarizing...`")
    prompt = f"Summarize the following message in 2-3 concise sentences:\n\n{reply.text[:3000]}"
    
    # Use engine for consistency
    await run_ai_task(e, prompt, system_override="You are a professional summarizer. Be concise.")


@ultroid_cmd(pattern="tldr( (.*)|$)")
async def tldr(e):
    match = e.pattern_match.group(1).strip()
    try:
        limit = max(5, min(int(match), 200)) if match.isdigit() else 50
    except Exception:
        limit = 50

    xx = await e.eor(f"`[AI] Reading last {limit} messages...`")

    collected = []
    async for msg in e.client.iter_messages(e.chat_id, limit=limit):
        if msg.text and not msg.out:
            sender = getattr(msg.sender, "first_name", "?") or "?"
            collected.append(f"{sender}: {msg.text.strip()}")

    if not collected:
        return await xx.edit("`[AI] No text messages found to summarize.`")

    await xx.edit("`[AI] Analyzing conversation...`")
    conversation = "\n".join(reversed(collected))[:4000]
    prompt = (
        "The following is a conversation from a Telegram group. "
        "Summarize it in up to 5 bullet points covering the key topics discussed:\n\n"
        f"{conversation}"
    )
    
    # Use engine for consistency
    await run_ai_task(e, prompt, system_override="You are a conversation analyst. Provide a professional TL;DR.")


@ultroid_cmd(pattern="aimodel( (.*)|$)", fullsudo=True)
async def set_ai_model(e):
    _VALID = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    model = e.pattern_match.group(1).strip()

    if not model:
        current = udB.get_key("GROQ_AI_MODEL") or "llama-3.3-70b-versatile"
        return await e.eor(
            f"**Current AI model:** `{current}`\n\n"
            f"**Available models:**\n" + "\n".join(f"• `{m}`" for m in _VALID)
        )

    if model not in _VALID:
        return await e.eor(
            f"`[AI] Unknown model '{model}'.`\n"
            f"Available: `{'`, `'.join(_VALID)}`"
        )

    udB.set_key("GROQ_AI_MODEL", model)
    await e.eor( f"`[AI] Model switched to: {model}`")


@ultroid_cmd(pattern="search( (.*)|$)")
async def web_search_cmd(e):
    query = e.pattern_match.group(1).strip()
    if not query:
        return await e.eor("`Search | Provide a query. Example: .search Space X Launch`")

    xx = await e.eor("`Search | Researching...`")
    results = await google_search(query)
    
    if not results:
        return await xx.edit("`Search | No results found for your query.`")
    
    output = f"🖥 **Web Search Results**\n`Query: {query}`\n\n"
    for i, r in enumerate(results[:5], 1):
        output += f"{i}. **[{r['title']}]({r['link']})**\n"
        output += f"   `{r['body'][:150]}...`\n\n"
    
    await xx.edit(output, link_preview=False)


@ultroid_cmd(pattern="debug$", fullsudo=True)
async def ai_debug(e):
    xx = await e.eor("`[AI] Analyzing system logs...`")
    log_file = "ultroid.log"
    if not os.path.exists(log_file):
        return await xx.edit("`Debug | log file (ultroid.log) not found.`")

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            logs = "".join(lines[-50:])
    except Exception as err:
        return await xx.edit(f"`Debug | Error reading logs: {err}`")

    prompt = (
        "The following are the last 50 lines of a Telegram userbot's logs. "
        "Identify any errors, tracebacks, or critical failures. "
        "Explain what happened and provide a code fix or solution if possible.\n\n"
        f"LOGS:\n{logs}"
    )
    
    # Use engine for debug analysis
    await run_ai_task(e, prompt, system_override="You are a professional Python Debugger and Systems Engineer.")


