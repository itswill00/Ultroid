# Ultroid - Unified AI Plugin (Text + Vision)
# Powered by Groq LPU™ Inference Engine

import os
from . import udB, ultroid_cmd, LOGS, HNDLR, eor
from pyUltroid._misc import owner_and_sudos
from pyUltroid.fns.helper import async_searcher
from pyUltroid.fns.tools import encode_image_base64

GROQ_API_KEY = udB.get_key("GROQ_API_KEY")


DEFAULT_SYSTEM_PROMPT = (
    "You are Ultroid Optimized, a high-end technical system architect and professional assistant. "
    "MANDATORY: You must ALWAYS respond in Indonesian (Bahasa Indonesia). "
    "Your responses are direct, highly logical, and technically precise. "
    "Follow a markdown-optimized format. Use cold and efficient language. "
    "Do not apologize. Do not use conversational filler. "
    "Prioritize accuracy and deep technical insight above all else."
)

@ultroid_cmd(pattern="(ai|chat)( (.*)|$)")
async def unified_ai(e):
    from pyUltroid.fns.ai_engine import run_ai_task
    from pyUltroid.fns.tools import encode_image_base64
    
    query = e.pattern_match.group(2).strip()
    image_b64 = None
    reply = await e.get_reply_message()
    
    # Vision logic (Keep in plugin for media handling, but pass to engine)
    if reply and (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        dl = await reply.download_media()
        try:
            image_b64 = encode_image_base64(dl)
            import os
            os.remove(dl)
        except Exception as er:
            LOGS.exception(er)
            if os.path.exists(dl): os.remove(dl)

    if not query and reply and reply.text:
        query = reply.text
    
    # Process via Unified Engine
    await run_ai_task(e, query, image_b64=image_b64)

__doc__ = """
**Unified AI Assistant (Groq)**

- `.ai <query>` — Fast AI text response (Llama 3.1 8B).
- `.ai` (reply to image) — Computer Vision analysis (Llama 4 Scout).
- `.ai` (reply to text) — Context-aware chat with history.
- `.chat <query>` — Alias for `.ai`.
"""
