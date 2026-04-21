# Ultroid AI Core Engine
# Centralized logic for Banking, Persona, and Multi-Provider Interaction

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

# Providers Configuration
ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions"
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20240620",
    "gemini": "gemini-1.5-flash",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile"
}

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# --------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------

def markdown_to_html(text):
    """Basic MD to HTML conversion for Telegraph."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"```(.*?)```", r"<pre>\1</pre>", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    text = text.replace("\n", "<br/>")
    return text

async def fast_telegraph(title, markdown_text):
    """Pasts to telegraph with fallback."""
    from pyUltroid.fns.tools import make_html_telegraph
    try:
        html_code = markdown_to_html(markdown_text)
        url = await make_html_telegraph(title, html_code)
        return url
    except Exception as e:
        LOGS.warning(f"Telegraph Paste Failed: {str(e)}")
        return None

async def google_search(query):
    """Integrated DuckDuckGo search for AI context."""
    from duckduckgo_search import AsyncDDGS
    try:
        async with AsyncDDGS() as ddgs:
            results = [r async for r in ddgs.text(query, max_results=5)]
            return results
    except Exception as e:
        LOGS.warning(f"Search failed: {e}")
        return None

def _get_api_keys(key_name):
    """Parses multiple space-separated keys from DB or Env."""
    raw = udB.get_key(key_name) or os.environ.get(key_name)
    if not raw:
        return []
    if isinstance(raw, list): return raw
    return [k.strip() for k in str(raw).split() if k.strip()]

# --------------------------------------------------------------------------
# PROVIDER CALLS
# --------------------------------------------------------------------------

async def _call_openai_like(provider, messages, model=None, stream=False):
    """Helper for OpenAI-compatible APIs (OpenAI, Groq, DeepSeek)."""
    keys_map = {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
    keys = _get_api_keys(keys_map.get(provider))
    if not keys: return None, f"{provider.upper()} API Key Missing."

    model = model or udB.get_key(f"{provider.upper()}_MODEL") or DEFAULT_MODELS[provider]
    url = ENDPOINTS[provider]

    async def _request(api_key):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.2, "stream": stream}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    return None, await resp.text()
                
                if stream:
                    full_content = ""
                    async for line in resp.content:
                        if line:
                            line_text = line.decode('utf-8').strip()
                            if line_text.startswith("data: "):
                                data_str = line_text[6:]
                                if data_str == "[DONE]": break
                                try:
                                    data_json = json.loads(data_str)
                                    delta = data_json['choices'][0].get('delta', {}).get('content', '')
                                    if delta:
                                        full_content += delta
                                        yield delta, 0
                                except: continue
                else:
                    data = await resp.json()
                    yield data['choices'][0]['message']['content'], data.get('usage', {}).get('total_tokens', 0)

    # Try keys
    for key in keys:
        try:
            if stream:
                return _request(key) # Return generator
            else:
                async for res in _request(key): return res
        except Exception as e:
            LOGS.error(f"[{provider}] Key failed: {e}")
            continue
    return None, "All keys failed."

async def _call_anthropic(messages, model=None, stream=False):
    keys = _get_api_keys("ANTHROPIC_API_KEY")
    if not keys: return None, "Anthropic API Key Missing."
    
    model = model or udB.get_key("ANTHROPIC_MODEL") or DEFAULT_MODELS["anthropic"]
    url = ENDPOINTS["anthropic"]

    # Adapt messages: Anthropic uses system as a top-level param
    system_msg = next((m['content'] for m in messages if m['role'] == 'system'), "")
    filtered_msgs = [m for m in messages if m['role'] != 'system']

    async def _request(api_key):
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": filtered_msgs,
            "system": system_msg,
            "max_tokens": 4096,
            "stream": stream
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200: return None, await resp.text()
                if stream:
                    full_text = ""
                    async for line in resp.content:
                        if line:
                            line_text = line.decode('utf-8').strip()
                            if line_text.startswith("data: "):
                                try:
                                    data = json.loads(line_text[6:])
                                    if data['type'] == 'content_block_delta':
                                        delta = data['delta']['text']
                                        full_text += delta
                                        yield delta, 0
                                except: continue
                else:
                    data = await resp.json()
                    yield data['content'][0]['text'], data.get('usage', {}).get('output_tokens', 0)

    for key in keys:
        try:
            if stream: return _request(key)
            else:
                async for res in _request(key): return res
        except Exception as e: continue
    return None, "All keys failed."

async def _call_gemini(messages, model=None):
    keys = _get_api_keys("GEMINI_API_KEY")
    if not keys: return None, "No Gemini API Keys."
    
    model = model or udB.get_key("GEMINI_MODEL") or DEFAULT_MODELS["gemini"]
    
    gemini_contents = []
    system_instruction = ""
    for m in messages:
        if m['role'] == "system":
            system_instruction = m['content']
        else:
            parts = []
            content = m['content']
            if isinstance(content, list):
                for part in content:
                    if part['type'] == "text": parts.append({"text": part['text']})
                    # Add inline_data for images if needed
            else:
                parts.append({"text": str(content)})
            gemini_contents.append({"role": "model" if m['role'] == "assistant" else "user", "parts": parts})

    payload = {"contents": gemini_contents}
    if system_instruction:
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

    for key in keys:
        url = ENDPOINTS["gemini"].format(model=model, key=key)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as resp:
                    if resp.status != 200: continue
                    data = await resp.json()
                    ans = data['candidates'][0]['content']['parts'][0]['text']
                    return ans, 0
        except: continue
    return None, "Gemini failed."

# --------------------------------------------------------------------------
# MAIN ENGINE ENTRY POINT
# --------------------------------------------------------------------------

async def run_ai_task(event, query, image_b64=None, system_override=None, use_search=False, provider=None, model=None):
    """Unified AI processor for all providers."""
    from pyUltroid._misc import owner_and_sudos
    from .._misc._wrappers import eor

    uid = event.sender_id
    is_admin = uid in owner_and_sudos()
    
    # Provider selection logic
    if not provider:
        provider = udB.get_key("DEFAULT_AI_PROVIDER") or "groq"
    
    LOGS.info(f"run_ai_task started. provider={provider}, sender={uid}")

    try:
        # 1. Authorization
        if not is_admin:
            if not Verified.contains(uid):
                Verified.add(uid)
                current_bank = Bank.get() or {}
                current_bank[str(uid)] = current_bank.get(str(uid), 0) + STARTING_GIFT
                Bank.add(current_bank)

            balance = Bank.get().get(str(uid), 0)
            if balance <= 0:
                return await eor(event, "`[Ultroid Bank] Insufficient balance.`")

        # 2. Preparation
        system_prompt = system_override or udB.get_key("AI_SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT
        
        msg = await eor(event, "`[AI] Analyzing...`")

        # 3. Web Search
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

        # 4. Construct Messages
        messages = [{"role": "system", "content": system_prompt}]
        chat_id = str(event.chat_id)
        if chat_id not in CHAT_HISTORY: CHAT_HISTORY[chat_id] = []
        for past_msg in CHAT_HISTORY[chat_id][-MAX_HISTORY:]:
            messages.append(past_msg)

        content = []
        if not query and image_b64:
            query = "Describe this image technically in Indonesian."
        if query:
            content.append({"type": "text", "text": query})
        if image_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
        
        messages.append({"role": "user", "content": content})

        # 5. Execution
        start_time = time.time()
        
        # Dispatch to provider
        if provider == "openai":
            res = await _call_openai_like("openai", messages, model=model)
        elif provider == "groq":
            res = await _call_openai_like("groq", messages, model=model or (VISION_MODEL if image_b64 else None))
        elif provider == "deepseek":
            res = await _call_openai_like("deepseek", messages, model=model)
        elif provider == "anthropic":
            res = await _call_anthropic(messages, model=model)
        elif provider == "gemini":
            res = await _call_gemini(messages, model=model)
        else:
            return await msg.edit(f"`Unknown provider: {provider}`")

        ans, usage_or_err = res
        duration = round(time.time() - start_time, 2)

        if not ans:
            return await msg.edit(f"`[AI ERROR] {usage_or_err}`")

        # Update History
        clean_user_text = query if query else "Attached an image for analysis."
        if "CONTEXT:" in clean_user_text:
            clean_user_text = clean_user_text.split("USER QUESTION:")[-1].strip()
        
        CHAT_HISTORY[chat_id].append({"role": "user", "content": clean_user_text})
        CHAT_HISTORY[chat_id].append({"role": "assistant", "content": ans.strip()})
        if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY * 2:
            CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-(MAX_HISTORY * 2):]

        # 6. Post-processing
        total_tokens = usage_or_err if isinstance(usage_or_err, int) else 0
        if not is_admin and total_tokens > 0:
            current_bank = Bank.get() or {}
            current_bank[str(uid)] = max(0, current_bank.get(str(uid), 0) - total_tokens)
            Bank.add(current_bank)

        q_preview = clean_user_text[:100].replace('\n', ' ')
        output = f"> \"{q_preview}\"\n\n{ans.strip()}"
        if sources:
            output += "\n\n**Sources**:\n" + "\n".join([f"• {s}" for s in sources[:3]])

        footer = f"\n\n**provider**: `{provider}`\n**time**: `{duration}s`\n**tokens**: `{total_tokens}`"
        
        if len(output) > 2000:
            tg_url = await fast_telegraph(f"Ultroid AI: {q_preview[:30]}...", output)
            if tg_url:
                return await msg.edit(f"> \"{q_preview}\"\n\n**Read Full Response**: [Telegraph]({tg_url}){footer}", link_preview=True)

        await msg.edit(output + footer, link_preview=False)

    except Exception as e:
        LOGS.exception(e)
        await eor(event, f"`AI Error: {str(e)}`")
