# Ultroid AI Core Engine
# Centralized logic for Banking, Persona, and Groq Interaction

import os
import re
import time
import html
import asyncio
from io import BytesIO
from pyUltroid.dB.base import KeyManager
from .. import udB, LOGS

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
    "Respond in the same language as the user. "
    "Your responses are direct, highly logical, and technically precise. "
    "Follow a markdown-optimized format. Use cold and efficient language. "
    "Do not apologize. Do not use conversational filler. "
    "Prioritize accuracy and deep technical insight above all else."
)

# --------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------

def markdown_to_html(text):
    """Basic MD to HTML conversion for Telegraph."""
    # Escape HTML to prevent injection
    text = html.escape(text)
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Pre-formatted code
    text = re.sub(r"```(.*?)```", r"<pre>\1</pre>", text, flags=re.DOTALL)
    # Inline code
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    # Line breaks
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

# --------------------------------------------------------------------------
# WEB SEARCH UTILITY
# --------------------------------------------------------------------------

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

# --------------------------------------------------------------------------
# CORE API CALL
# --------------------------------------------------------------------------

# Model khusus vision (support gambar)
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

async def _call_groq(messages, vision_model=None, model=None):
    """Internal helper to call Groq API and extract usage.
    
    Args:
        messages: List of message dicts.
        vision_model: Deprecated. Use 'model' parameter.
        model: Manual model override (e.g. 'llama-3.1-8b-instant')
    """
    import aiohttp
    api_key = udB.get_key("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    
    # Priority: model > vision_model (legacy) > udB > default
    if not model:
        model = vision_model or udB.get_key("GROQ_AI_MODEL") or "llama-3.3-70b-versatile"

    
    if not api_key:
        return None, "API Key Missing."

    LOGS.info(f"[Groq] Using model: {model}")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    
    for attempt in range(max_retries := 2):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
                    if resp.status in [413, 429]:  # Rate Limit or TPM Limit
                        wait = (attempt + 1) * 10
                        LOGS.warning(f"[Groq] Rate Limit Hit ({resp.status}). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status != 200:
                        err = await resp.text()
                        LOGS.error(f"[Groq] API Error {resp.status}: {err[:300]}")
                        return None, f"API Error {resp.status}: {err[:200]}"
                    
                    data = await resp.json()
                    ans = data['choices'][0]['message']['content']
                    usage = data.get('usage', {}).get('total_tokens', 0)
                    return ans, usage
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
                continue
            LOGS.exception(f"[Groq] Request failed: {e}")
            return None, str(e)
    
    return None, "Rate Limit Exhausted after retries."


# --------------------------------------------------------------------------
# MAIN ENGINE ENTRY POINT
# --------------------------------------------------------------------------

async def run_ai_task(event, query, image_b64=None, system_override=None, use_search=False):
    """Unified AI processor for all plugins."""
    from pyUltroid._misc import owner_and_sudos
    from .._misc._wrappers import eor
    
    uid = event.sender_id
    is_admin = uid in owner_and_sudos()
    
    from .. import udB, LOGS
    LOGS.info(f"run_ai_task started. sender={uid}, is_admin={is_admin}")
    
    try:
        # 1. Authorization & Auto-registration
        if not is_admin:
            if not Verified.contains(uid):
                Verified.add(uid)
                # Auto-gift starting tokens
                current_bank = Bank.get() or {}
                current_bank[str(uid)] = current_bank.get(str(uid), 0) + STARTING_GIFT
                Bank.add(current_bank)
                # First time notification (silent or integrated)
            
            balance = Bank.get().get(str(uid), 0)
            if balance <= 0:
                return await eor(event, "`[Ultroid Bank] Insufficient balance. Please contact owner for refill.`")

        # 2. Preparation (System Prompt)
        system_prompt = system_override or udB.get_key("GROQ_SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT
        
        # 3. Handle Web Search
        context = ""
        sources = []
        if use_search and query:
            msg = await eor(event, "`[SEARCH] Researching web...`")
            results = await google_search(query)
            if results:
                context = "Here is some real-time context from the web:\n"
                for r in results:
                    context += f"- {r['title']}: {r['body']}\n"
                    sources.append(r['link'])
                query = f"CONTEXT:\n{context}\n\nUSER QUESTION: {query}"
            else:
                await msg.edit("`[SEARCH] No results. Using core knowledge...`")
        else:
            msg = await eor(event, "`[AI] Analyzing...`")

        # 4. Construct Messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Inject History
        chat_id = str(event.chat_id)
        if chat_id not in CHAT_HISTORY:
            CHAT_HISTORY[chat_id] = []
        for past_msg in CHAT_HISTORY[chat_id][-MAX_HISTORY:]:
            messages.append(past_msg)
        
        content = []
        # Jika ada gambar tapi tidak ada teks, pakai prompt default DULU
        if not query and image_b64:
            query = "Describe this image technically. Provide details about what you see."
        if query:
            content.append({"type": "text", "text": query})
        if image_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
                
        messages.append({"role": "user", "content": content})
        
        # 5. Execution (Timing)
        # Otomatis pakai vision model jika ada gambar
        start_time = time.time()
        ans, usage_or_err = await _call_groq(
            messages,
            vision_model=VISION_MODEL if image_b64 else None
        )
        duration = round(time.time() - start_time, 2)
        
        if not ans:
            # Re-fetch logic if it was a search query that failed
            return await msg.edit(f"`[GROQ ERROR] {usage_or_err}`")
            
        # Update History
        clean_user_text = query if query else "Attached an image for analysis."
        CHAT_HISTORY[chat_id].append({"role": "user", "content": clean_user_text})
        CHAT_HISTORY[chat_id].append({"role": "assistant", "content": ans.strip()})
        
        # Prune memory
        if len(CHAT_HISTORY[chat_id]) > MAX_HISTORY * 2:
            CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-(MAX_HISTORY * 2):]
        
        # 6. Token Deduction
        total_tokens = usage_or_err if isinstance(usage_or_err, int) else 0
        if not is_admin and total_tokens > 0:
            current_bank = Bank.get() or {}
            current_balance = current_bank.get(str(uid), 0)
            new_balance = max(0, current_balance - total_tokens)
            current_bank[str(uid)] = new_balance
            Bank.add(current_bank)

        # 7. Formatting & Telemetry
        model = udB.get_key("GROQ_AI_MODEL") or "llama-3.3-70b-versatile"
        short_model = model.split('/')[-1] if '/' in model else model
        q_preview = query[:100].replace('\n', ' ') if query else "Visual Request"
        if "CONTEXT:" in q_preview: 
            q_preview = q_preview.split("USER QUESTION:")[-1].strip()
            
        output = f"> \"{q_preview}\"\n\n{ans.strip()}"
        if sources:
            output += "\n\n**Sources**:\n" + "\n".join([f"• {s}" for s in sources[:3]])

        footer = f"\n\n**model**: `{short_model}`\n**time**: `{duration}s`\n**tokens**: `{total_tokens}`"
        if not is_admin:
            footer += f"\n**limit**: `-{total_tokens}`"

        # 8. Dispatch (Smart Fallback)
        if len(output) > 1000:
            tg_url = await fast_telegraph(f"Ultroid AI: {q_preview[:30]}...", output)
            if tg_url:
                return await msg.edit(f"> \"{q_preview}\"\n\n**Read Full Response**: [Telegraph]({tg_url}){footer}", link_preview=True)
            
            # Internal Fallback to File
            with BytesIO(str.encode(output)) as out_file:
                out_file.name = "response.md"
                # For file fallback, we might need a new message
                await msg.delete()
                return await event.reply(f"> \"{q_preview}\"{footer}", file=out_file)

        # Final edit
        await msg.edit(output + footer, link_preview=False)
        
    except Exception as e:
        LOGS.exception(e)
        from traceback import format_exc
        err_msg = f"`[AI ERROR] {str(e)}`"
        if is_admin:
             err_msg += f"\n\n**Traceback:**\n`{format_exc()[:500]}`"
        try:
            await eor(event, err_msg)
        except Exception as e2:
            LOGS.error(f"[AI ENGINE] eor failed during error dispatch: {e2}")
