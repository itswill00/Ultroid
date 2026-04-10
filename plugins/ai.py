# Ultroid - Groq AI Plugin
# High-Performance Inference Engine

from . import ultroid_cmd, eor, udB, LOGS
from pyUltroid.fns.helper import async_searcher

GROQ_API_KEY = udB.get_key("GROQ_API_KEY")

@ultroid_cmd(pattern="(ai|chat)( (.*)|$)")
async def groq_ai(e):
    if not GROQ_API_KEY:
        return await eor(e, "`GROQ_API_KEY` is not set in environment.")
    
    query = e.pattern_match.group(2).strip()
    reply = await e.get_reply_message()
    
    if not query and reply and reply.text:
        query = reply.text
    
    if not query:
        return await eor(e, "`Provide a query or reply to a message.`")
    
    msg = await eor(e, "`Inference in progress...`")
    
    # Minimalist technical headers
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Using Llama 3.1 70B for high-quality technical output
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional technical assistant. Provide direct, cold, and minimalist answers. Use Markdown. Avoid conversational filler."
            },
            {"role": "user", "content": query}
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
