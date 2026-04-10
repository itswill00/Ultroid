# Ultroid - Groq AI Plugin
# High-Performance Inference Engine

from . import ultroid_cmd, eor, udB, LOGS
from pyUltroid.fns.helper import async_searcher

GROQ_API_KEY = udB.get_key("GROQ_API_KEY")
OCR_API_KEY = udB.get_key("OCR_API_KEY") or "helloworld"

# Simple in-memory chat history (sliding window of 5 messages)
CHAT_HISTORY = {}

@ultroid_cmd(pattern="(ai|chat)( (.*)|$)")
async def groq_ai(e):
    if not GROQ_API_KEY:
        return await eor(e, "`GROQ_API_KEY` is not set in environment.")
    
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    chat_id = e.chat_id
    
    image_text = ""
    msg = None
    
    # Check if reply is image/document for OCR integration
    if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        from pyUltroid.fns.tools import ocr_space
        import os
        msg = await eor(e, "`Extracting text from image...`")
        dl = await reply.download_media("temp/")
        try:
            image_text = await ocr_space(dl, api_key=OCR_API_KEY)
            if not image_text:
                await msg.edit("`Failed to extract text from image. Proceeding with query only.`")
        finally:
            if os.path.exists(dl):
                os.remove(dl)

    if not query and reply and reply.text:
        query = reply.text
    
    # Build Prompt
    full_prompt = query
    if image_text:
        full_prompt = f"IMAGE TEXT:\n{image_text}\n\nUSER QUERY:\n{query}" if query else f"Analyze this image text:\n{image_text}"
        
    if not full_prompt:
        return await eor(e, "`Provide a query or reply to a message/image.`")
    
    if not msg:
        msg = await eor(e, "`Inference in progress...`")
    else:
        await msg.edit("`Thinking with context...`")
    
    # Initialize history for this chat
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
        
    # Enhanced Expert System Prompt
    system_prompt = (
        "You are KODA, a high-end technical system architect and professional assistant. "
        "Your responses are direct, highly logical, and technically precise. "
        "Follow a markdown-optimized format. Use cold and efficient language. "
        "Do not apologize. Do not use conversational filler. "
        "Prioritize accuracy and deep technical insight above all else."
    )
    
    # Prepare messages with history
    messages = [{"role": "system", "content": system_prompt}]
    for hist in CHAT_HISTORY[chat_id]:
        messages.append(hist)
    messages.append({"role": "user", "content": full_prompt})
    
    # Minimalist technical headers
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": messages,
        "temperature": 0.3
    }
    
    try:
        response = await async_searcher(
            "https://api.groq.com/openai/v1/chat/completions",
            post=True,
            json=payload,
            headers=headers,
            re_json=True
        )
        
        if response and response.get("choices"):
            ans = response["choices"][0]["message"]["content"]
            await msg.edit(ans)
            
            # Update history (keep last 5 interactions)
            CHAT_HISTORY[chat_id].append({"role": "user", "content": full_prompt})
            CHAT_HISTORY[chat_id].append({"role": "assistant", "content": ans})
            if len(CHAT_HISTORY[chat_id]) > 10:  # 5 pairs
                CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-10:]
        else:
            err = response.get("error", {}).get("message") or "Unknown API error"
            await msg.edit(f"**Groq Error:** `{err}`")
            
    except Exception as er:
        LOGS.exception(er)
        await msg.edit(f"`Error: {str(er)}`")

__doc__ = """
**AI Assistant (Groq)**

- `.ai <query>`: Get a fast AI response.
- `.chat <query>`: Same as .ai.
- Works as a reply to text messages.
"""
