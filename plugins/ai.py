# Ultroid - Groq AI Plugin
# High-Performance Inference Engine

from . import ultroid_cmd, eor, udB, LOGS
from pyUltroid.fns.helper import async_searcher

GROQ_API_KEY = udB.get_key("GROQ_API_KEY")
OCR_API_KEY = udB.get_key("OCR_API_KEY") or "helloworld"

@ultroid_cmd(pattern="(ai|chat)( (.*)|$)")
async def groq_ai(e):
    if not GROQ_API_KEY:
        return await eor(e, "`GROQ_API_KEY` is not set in environment.")
    
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    
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
    
    full_prompt = query
    if image_text:
        full_prompt = f"IMAGE TEXT EXTRACTED:\n{image_text}\n\nUSER QUERY:\n{query}" if query else f"Analyze this text extracted from an image:\n{image_text}"
        
    if not full_prompt:
        return await eor(e, "`Provide a query or reply to a message/image.`")
    
    if not msg:
        msg = await eor(e, "`Inference in progress...`")
    else:
        await msg.edit("`Thinking...`")
    
    # Minimalist technical headers
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional technical assistant. Provide direct, cold, and minimalist answers. Use Markdown. Avoid conversational filler."
            },
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.2
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
