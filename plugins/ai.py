# Ultroid - Unified AI Plugin (Text + Vision)
# Powered by Groq LPU™ Inference Engine

import os
from . import ultroid_cmd, eor, udB, LOGS
from pyUltroid.fns.helper import async_searcher
from pyUltroid.fns.tools import encode_image_base64

GROQ_API_KEY = udB.get_key("GROQ_API_KEY")

# In-memory chat history (sliding window of 5 interactions per chat)
# Hard cap: max 500 active chat sessions to prevent memory leak
CHAT_HISTORY = {}
_CHAT_HISTORY_MAX_SESSIONS = 500

@ultroid_cmd(pattern="(ai|chat)( (.*)|$)")
async def unified_ai(e):
    if not GROQ_API_KEY:
        return await eor(e, "`GROQ_API_KEY` is not set in environment.")
    
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    chat_id = e.chat_id
    
    image_b64 = None
    msg = None
    model = "llama-3.1-8b-instant" # Default text model (Fast & Stable)
    
    # Check if reply is image/document for Vision integration
    if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        msg = await eor(e, "`Analyzing image...`")
        os.makedirs("temp", exist_ok=True)
        dl = await reply.download_media("temp/")
        try:
            # Check file size (Groq limit is 4MB)
            if os.path.getsize(dl) > 4 * 1024 * 1024:
                await msg.edit("`Image too large (>4MB). Please compress it.`")
                return os.remove(dl)
            
            image_b64 = encode_image_base64(dl)
            model = "meta-llama/llama-4-scout-17b-16e-instruct" # Switch to Llama 4 Scout Vision
        except Exception as er:
            LOGS.exception(er)
            await msg.edit(f"`Vision Error: {str(er)}`")
        finally:
            if os.path.exists(dl):
                os.remove(dl)

    if not query and reply and reply.text:
        query = reply.text
    
    if not query and not image_b64:
        return await eor(e, "`Provide a query or reply to a message/image.`")
    
    if not msg:
        msg = await eor(e, "`Processing request...`")
    else:
        await msg.edit("`Thinking...`")
    
    # Initialize history for this chat
    # Evict oldest sessions if at capacity
    if len(CHAT_HISTORY) >= _CHAT_HISTORY_MAX_SESSIONS and chat_id not in CHAT_HISTORY:
        oldest = next(iter(CHAT_HISTORY))
        del CHAT_HISTORY[oldest]
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
        
    # Expert System Prompt
    system_prompt = (
        "You are Ultroid Optimized, a high-end technical system architect and professional assistant. "
        "Respond in the same language as the user. "
        "Your responses are direct, highly logical, and technically precise. "
        "Follow a markdown-optimized format. Use cold and efficient language. "
        "Do not apologize. Do not use conversational filler. "
        "Prioritize accuracy and deep technical insight above all else."
    )
    
    # Construct Content
    content = []
    if query:
        content.append({"type": "text", "text": query})
    elif image_b64:
        content.append({"type": "text", "text": "Describe this image technically and answer any implied questions."})
    
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_b64}"
            }
        })

    # Prepare messages with history
    messages = [{"role": "system", "content": system_prompt}]
    for hist in CHAT_HISTORY[chat_id]:
        # Vision models sometimes have trouble with mixed history types, 
        # so we keep history as text-only for stability in this minimalist version.
        if isinstance(hist["content"], str):
            messages.append(hist)
            
    messages.append({"role": "user", "content": content})
    
    # Headers
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }
    
    # Measure execution time
    import time
    start_time = time.time() * 1000 
    
    try:
        response = await async_searcher(
            "https://api.groq.com/openai/v1/chat/completions",
            post=True,
            json=payload,
            headers=headers,
            re_json=True
        )
        
        duration = round(time.time() * 1000 - start_time)
        
        if response and response.get("choices"):
            ans = response["choices"][0]["message"]["content"]
            
            # Measurement for duration already handled
            duration = round(time.time() * 1000 - start_time)
            
            # Sanitize answer for nested code blocks (Telegram limitation)
            # We replace triple backticks inside the answer to avoid breaking the outer block
            sanitized_ans = ans.replace("```", "'''")
            
            # Simplify model name for display
            model_map = {
                "meta-llama/llama-4-scout-17b-16e-instruct": "Llama 4 Scout",
                "llama-3.1-8b-instant": "Llama 3.1 8B",
            }
            short_model = model_map.get(model, model.split('/')[-1])
            # Generate display text for the input
            input_text = query or ("[Image Analysis]" if image_b64 else "[Reply Context]")
            
            # 1. Quote Layout
            q_preview = input_text[:200].replace('\n', ' ')
            output = f"> \"{q_preview}\"\n\n{sanitized_ans.strip()}"
            
            # 2. Telemetry Metrix & Footer
            footer = f"\n\n`[{short_model}]` • `[{duration}ms]`"
            
            # 3. Smart Auto-Fallback
            if len(output) > 1000:
                from io import BytesIO
                file_name = "ai_response.md"
                with BytesIO(str.encode(output)) as out_file:
                    out_file.name = file_name
                    await e.reply(f"> \"{q_preview}\"{footer}", file=out_file)
                await msg.delete()
            else:
                await msg.edit(output + footer, link_preview=False)
            
            # Update history (keep last 5 interactions, text-only)
            CHAT_HISTORY[chat_id].append({"role": "user", "content": query or "[Visual Inquiry]"})
            CHAT_HISTORY[chat_id].append({"role": "assistant", "content": ans})
            if len(CHAT_HISTORY[chat_id]) > 10:
                CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-10:]
        else:
            err = response.get("error", {}).get("message") or "Unknown API error"
            await msg.edit(f"**Groq Error:** `{err}`")
            
    except Exception as er:
        LOGS.exception(er)
        await msg.edit(f"`Error: {str(er)}`")

__doc__ = """
**Unified AI Assistant (Groq)**

- `.ai <query>` — Fast AI text response (Llama 3.1 8B).
- `.ai` (reply to image) — Computer Vision analysis (Llama 4 Scout).
- `.ai` (reply to text) — Context-aware chat with history.
- `.chat <query>` — Alias for `.ai`.
"""
