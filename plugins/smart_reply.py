# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.
"""
✘ Commands Available -

• `{i}ask <question>`
    Ask anything to the AI (via Groq API). Requires GROQ_API_KEY in .env.
    Use `--search` or `-s` to enable real-time web research.
    Example: `.ask --search Who is the current CEO of Tesla?`

• `{i}search <query>`
    Perform a direct web search and view the top results.

• `{i}summarize`
    Reply to a message to get a concise AI-generated summary.

• `{i}tldr <count>`
    Read the last N messages in the chat and produce a summary.
    Example: `.tldr 50`

• `{i}aimodel <name>`
    Switch the AI model. Default: llama-3.3-70b-versatile
    Available: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
"""

import os
from datetime import datetime

from . import udB, ultroid_cmd, LOGS, HNDLR
from pyUltroid.fns.misc import google_search

help_smart_reply = __doc__

_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_MODEL_KEY = "GROQ_AI_MODEL"
_PROMPT_KEY = "GROQ_SYSTEM_PROMPT"
_MAX_TOKENS = 1024
_SYSTEM_PROMPT = (
    "You are a precise, technical assistant. "
    "Respond concisely and directly in the same language the user writes in."
)


def _get_system_prompt() -> str:
    return udB.get_key(_PROMPT_KEY) or _SYSTEM_PROMPT


def _get_model() -> str:
    return udB.get_key(_MODEL_KEY) or _DEFAULT_MODEL


def _get_api_key() -> str | None:
    return udB.get_key("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")


async def _call_groq(prompt: str, system: str = _SYSTEM_PROMPT) -> str | None:
    """Call Groq API and return response text, or None on failure."""
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import aiohttp
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _get_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": _MAX_TOKENS,
            "temperature": 0.5,
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    LOGS.warning(f"[AI] Groq API error {resp.status}: {err[:200]}")
                    return None
                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as err:
        LOGS.exception(err)
        return None


@ultroid_cmd(pattern="ask( (.*)|$)")
async def ask_ai(e):
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

    if not _get_api_key():
        return await e.eor(
            "`[AI] GROQ_API_KEY is not set.`\n"
            "`Add to .env: GROQ_API_KEY=gsk_xxx`"
        )

    xx = await e.eor("`[AI] Processing...`")
    
    context = ""
    sources = []
    
    # Audit Mode Logic
    special_system = None
    if "--code" in question:
        question = question.replace("--code", "").strip()
        special_system = (
            "You are a Senior Systems Architect and Security Engineer. "
            "Analyze the following code or technical problem with focus on: "
            "1. Efficiency and Performance. 2. Security Vulnerabilities. 3. Best Practices. "
            "Be extremely technical and rigorous."
        )

    if use_search:
        await xx.edit("`[AI] Searching web for context...`")
        results = await google_search(question)
        if results:
            context = "Here is some real-time context from the web:\n"
            for r in results[:4]:
                context += f"- {r['title']}: {r['description']}\n"
                sources.append(r['link'])
            
            system_prompt = special_system or (
                "You are a precise, technical assistant with access to real-time web search results. "
                "Use the provided context to answer the user's question accurately. "
                "If the context is irrelevant, rely on your core knowledge but prioritize real-time data for current events."
            )
            prompt = f"CONTEXT:\n{context}\n\nUSER QUESTION: {question}"
            result = await _call_groq(prompt, system=system_prompt)
        else:
            await xx.edit("`[AI] Search returned no results. Falling back to core knowledge...`")
            result = await _call_groq(question, system=special_system or _get_system_prompt())
    else:
        result = await _call_groq(question, system=special_system or _get_system_prompt())

    if not result:
        return await xx.edit("`[AI] No response from AI. Check your API key.`")

    model = _get_model()
    header = "🛠 Engineering Audit" if special_system else "Answer"
    output = f"**Question:** {question[:200]}\n\n"
    output += f"**{header}:**\n{result}\n\n"
    
    if sources:
        output += "**Sources:**\n"
        for s in sources[:3]:
            output += f"• {s}\n"
        output += "\n"
        
    output += f"`Model: {model}`"
    await xx.edit(output, link_preview=False)


@ultroid_cmd(pattern="summarize$")
async def summarize_msg(e):
    reply = await e.get_reply_message()
    if not reply or not reply.text:
        return await e.eor("`[AI] Reply to the message you want summarized.`")

    if not _get_api_key():
        return await e.eor("`[AI] GROQ_API_KEY is not set.`")

    xx = await e.eor("`[AI] Summarizing...`")
    prompt = f"Summarize the following message in 2-3 concise sentences:\n\n{reply.text[:3000]}"
    result = await _call_groq(prompt)

    if not result:
        return await xx.edit("`[AI] Failed to get a summary.`")

    await xx.edit(f"**Summary:**\n{result}")


@ultroid_cmd(pattern="tldr( (.*)|$)")
async def tldr(e):
    match = e.pattern_match.group(1).strip()
    try:
        limit = max(5, min(int(match), 200)) if match.isdigit() else 50
    except Exception:
        limit = 50

    if not _get_api_key():
        return await e.eor("`[AI] GROQ_API_KEY is not set.`")

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
    result = await _call_groq(prompt)

    if not result:
        return await xx.edit("`[AI] Failed to analyze the conversation.`")

    await xx.edit(f"**TL;DR — last {limit} messages:**\n\n{result}")


@ultroid_cmd(pattern="aimodel( (.*)|$)", fullsudo=True)
async def set_ai_model(e):
    _VALID = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]
    model = e.pattern_match.group(1).strip()

    if not model:
        current = _get_model()
        return await e.eor(
            f"**Current AI model:** `{current}`\n\n"
            f"**Available models:**\n" + "\n".join(f"• `{m}`" for m in _VALID)
        )

    if model not in _VALID:
        return await e.eor(
            f"`[AI] Unknown model '{model}'.`\n"
            f"Available: `{'`, `'.join(_VALID)}`"
        )

    udB.set_key(_MODEL_KEY, model)
    await e.eor(f"`[AI] Model switched to: {model}`")


@ultroid_cmd(pattern="search( (.*)|$)")
async def web_search(e):
    query = e.pattern_match.group(1).strip()
    if not query:
        return await e.eor("`[SEARCH] Provide a query. Example: .search Space X Launch`")

    xx = await e.eor("`[SEARCH] Researching...`")
    results = await google_search(query)
    
    if not results:
        return await xx.edit("`[SEARCH] No results found for your query.`")
    
    output = f"🖥 **Web Search Results**\n`Query: {query}`\n\n"
    for i, r in enumerate(results[:5], 1):
        output += f"{i}. **[{r['title']}]({r['link']})**\n"
        output += f"   `{r['description'][:150]}...`\n\n"
    
    await xx.edit(output, link_preview=False)


@ultroid_cmd(pattern="setprompt( (.*)|$)", fullsudo=True)
async def set_ai_prompt(e):
    prompt = e.pattern_match.group(1).strip()
    if not prompt:
        current = _get_system_prompt()
        return await e.eor(f"**Current System Prompt:**\n`{current}`")
    
    udB.set_key(_PROMPT_KEY, prompt)
    await e.eor("`[AI] System prompt updated successfully.`")


@ultroid_cmd(pattern="remprompt$", fullsudo=True)
async def rem_ai_prompt(e):
    udB.del_key(_PROMPT_KEY)
    await e.eor("`[AI] System prompt reset to default.`")


@ultroid_cmd(pattern="debug$", fullsudo=True)
async def ai_debug(e):
    if not _get_api_key():
        return await e.eor("`[AI] GROQ_API_KEY is not set.`")

    xx = await e.eor("`[AI] Analyzing system logs...`")
    
    log_file = "ultroid.log"
    if not os.path.exists(log_file):
        return await xx.edit("`[DEBUG] log file (ultroid.log) not found.`")

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            logs = "".join(lines[-50:])
    except Exception as err:
        return await xx.edit(f"`[DEBUG] Error reading logs: {err}`")

    prompt = (
        "The following are the last 50 lines of a Telegram userbot's logs. "
        "Identify any errors, tracebacks, or critical failures. "
        "Explain what happened and provide a code fix or solution if possible.\n\n"
        f"LOGS:\n{logs}"
    )
    
    system = "You are a professional Python Debugger and Systems Engineer."
    result = await _call_groq(prompt, system=system)

    if not result:
        return await xx.edit("`[AI] Debugger failed to analyze logs.`")

    output = f"🔍 **Autonomous Log Analysis**\n\n{result}\n\n`Audit Complete.`"
    await xx.edit(output)
