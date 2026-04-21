# Ultroid AI Core Engine
# Simplified: Groq (Primary) + Gemini (Fallback)

import asyncio
import html
import os
import re
import time
import json
import aiohttp
from io import BytesIO

from pyUltroid.dB.base import KeyManager

from .. import LOGS, udB

# Database Managers
Bank = KeyManager("ULTROID_AI_TOKENS", cast=dict)
Verified = KeyManager("VERIFIED_AI_USERS", cast=list)

# In-Memory History (Reset on restart)
CHAT_HISTORY = {}
MAX_HISTORY = 10  # 5 user, 5 assistant

# Constants
STARTING_GIFT = 5000
DEFAULT_SYSTEM_PROMPT = (
    "You are Ultroid Optimized, a high-end technical system architect and professional assistant. "
    "MANDATORY: You must ALWAYS respond in Indonesian (Bahasa Indonesia). "
    "Your responses are direct, highly logical, and technically precise. "
    "Follow a markdown-optimized format. Use cold and efficient language. "
    "Do not apologize. Do not use conversational filler. "
    "Prioritize accuracy and deep technical insight above all else."
)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# --------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------

def markdown_to_html(text):
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"```(.*?)```", r"<pre>\1</pre>", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    text = text.replace("\n", "<br/>")
    return text

async def fast_telegraph(title, markdown_text):
    from pyUltroid.fns.tools import make_html_telegraph
    try:
        html_code = markdown_to_html(markdown_text)
        url = await make_html_telegraph(title, html_code)
        return url
    except Exception as e:
        LOGS.warning(f"Telegraph Paste Failed: {str(e)}")
        return None

async def google_search(query):
    from duckduckgo_search import AsyncDDGS
    try:
        async with AsyncDDGS() as ddgs:
            results = [r async for r in ddgs.text(query, max_results=5)]
            return results
    except Exception as e:
        LOGS.warning(f"Search failed: {e}")
        return None

def _get_api_keys(key_name):
    raw = udB.get_key(key_name) or os.environ.get(key_name)
    if not raw: return []
    if isinstance(raw, list): return raw
    return [k.strip() for k in str(raw).split() if k.strip()]

# --------------------------------------------------------------------------
# PROVIDER CALLS
# --------------------------------------------------------------------------

async def _call_groq(messages, model=None):
    keys = _get_api_keys("GROQ_API_KEY")
    if not keys: return None, "Groq API Key Missing."

    model = model or udB.get_key("GROQ_AI_MODEL") or "llama-3.3-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"

    for api_key in keys:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.2}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                    if resp.status == 429:
                        LOGS.warning(f"[Groq] Key {api_key[:8]}... limited. Rotating...")
                        continue
                    if resp.status != 200:
                        LOGS.error(f"[Groq] Error {resp.status}: {await resp.text()}")
                        continue
                    
                    data = await resp.json()
                    return data['choices'][0]['message']['content'], data.get('usage', {}).get('total_tokens', 0)
        except Exception as e:
            LOGS.error(f"[Groq] Connection failed: {e}")
            continue

    # Level 2 Fallback: Groq failed, try Gemini
    LOGS.info("[AI Engine] Groq pool exhausted. Switching to Gemini Fallback...")
    return await _call_gemini(messages)

async def _call_gemini(messages, model=None):
    keys = _get_api_keys("GEMINI_API_KEY")
    if not keys: return None, "Gemini API Key Missing."
    
    model = model or udB.get_key("GEMINI_MODEL") or "gemini-1.5-flash"
    
    gemini_contents = []
    system_instruction = ""
    for m in messages:
        if m['role'] == "system":
            system_instruction = m['content']
        else:
            parts = [{"text": str(m['content'])}]
            gemini_contents.append({"role": "model" if m['role'] == "assistant" else "user", "parts": parts})

    payload = {"contents": gemini_contents}
    if system_instruction:
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

    for key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as resp:
                    if resp.status != 200: continue
                    data = await resp.json()
                    ans = data['candidates'][0]['content']['parts'][0]['text']
                    return ans, 0
        except: continue
    return None, "Gemini fallback failed."

# --------------------------------------------------------------------------
# MAIN ENGINE ENTRY POINT
# --------------------------------------------------------------------------

async def run_ai_task(event, query, image_b64=None, system_override=None, use_search=False, provider=None):
    from pyUltroid._misc import owner_and_sudos
    from .._misc._wrappers import eor

    uid = event.sender_id
    is_admin = uid in owner_and_sudos()
    
    try:
        if not is_admin:
            if not Verified.contains(uid):
                Verified.add(uid)
                current_bank = Bank.get() or {}
                current_bank[str(uid)] = current_bank.get(str(uid), 0) + STARTING_GIFT
                Bank.add(current_bank)
            if Bank.get().get(str(uid), 0) <= 0:
                return await eor(event, "`[AI] Insufficient balance.`")

        system_prompt = system_override or udB.get_key("AI_SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT
        msg = await eor(event, "`[AI] Analyzing...`")

        context = ""
        sources = []
        if use_search and query:
            await msg.edit("`Search | Researching web...`")
            results = await google_search(query)
            if results:
                context = "Here is some real-time context from the web:\n"
                for r in results:
                    context += f"- {r['title']}: {r['body']}\n"
                    sources.append(r['link'])
                query = f"CONTEXT:\n{context}\n\nUSER QUESTION: {query}"

        messages = [{"role": "system", "content": system_prompt}]
        chat_id = str(event.chat_id)
        if chat_id not in CHAT_HISTORY: CHAT_HISTORY[chat_id] = []
        for past_msg in CHAT_HISTORY[chat_id][-MAX_HISTORY:]:
            messages.append(past_msg)

        content = [{"type": "text", "text": query or "Describe this image technically in Indonesian."}]
        if image_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
        
        messages.append({"role": "user", "content": content})

        start_time = time.time()
        
        # Simple Dispatch
        if provider == "gemini":
            res = await _call_gemini(messages)
        else:
            res = await _call_groq(messages, model=VISION_MODEL if image_b64 else None)

        ans, usage_or_err = res
        duration = round(time.time() - start_time, 2)

        if not ans:
            return await msg.edit(f"`[AI ERROR] {usage_or_err}`")

        clean_user_text = query if query else "Visual Request"
        if "CONTEXT:" in clean_user_text:
            clean_user_text = clean_user_text.split("USER QUESTION:")[-1].strip()
        
        CHAT_HISTORY[chat_id].append({"role": "user", "content": clean_user_text})
        CHAT_HISTORY[chat_id].append({"role": "assistant", "content": ans.strip()})
        if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY * 2:
            CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-(MAX_HISTORY * 2):]

        total_tokens = usage_or_err if isinstance(usage_or_err, int) else 0
        if not is_admin and total_tokens > 0:
            current_bank = Bank.get() or {}
            current_bank[str(uid)] = max(0, current_bank.get(str(uid), 0) - total_tokens)
            Bank.add(current_bank)

        output = f"> \"{clean_user_text[:100]}\"\n\n{ans.strip()}"
        if sources:
            output += "\n\n**Sources**:\n" + "\n".join([f"• {s}" for s in sources[:3]])

        footer = f"\n\n**time**: `{duration}s` | **tokens**: `{total_tokens}`"
        
        if len(output) > 2000:
            tg_url = await fast_telegraph(f"Ultroid AI: {clean_user_text[:30]}...", output)
            if tg_url:
                return await msg.edit(f"> \"{clean_user_text[:30]}...\"\n\n**Read Full Response**: [Telegraph]({tg_url}){footer}", link_preview=True)

        await msg.edit(output + footer, link_preview=False)

    except Exception as e:
        LOGS.exception(e)
        await eor(event, f"`AI Error: {str(e)}`")
