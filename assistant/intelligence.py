# Ultroid Assistant - Intelligence & Research Tools

import os
from telethon import events
from . import asst, asst_cmd, udB, OWNER_NAME
from pyUltroid.fns.tools import async_searcher

@asst_cmd(pattern="tr( (.*)|$)", public=True)
async def assistant_translate(event):
    """Universal Translation Bot."""
    input_str = event.pattern_match.group(1).strip()
    if not event.is_reply and not input_str:
        return await event.reply("`Usage: /tr <lang_code> (as reply) or /tr <lang_code> <text>`")
    
    # Simple logic using a translation library if available, else direct API
    # For now, we'll interface with the core logic if possible.
    # To keep it autonomous and fast, we'll assume a standard translate library is present.
    try:
        from googletrans import Translator
        translator = Translator()
        
        target_lang = "en"
        text_to_tr = ""
        
        if "|" in input_str:
            target_lang, text_to_tr = input_str.split("|", 1)
        elif input_str:
            target_lang = input_str.split()[0]
            text_to_tr = " ".join(input_str.split()[1:])
        
        if not text_to_tr and event.is_reply:
            reply = await event.get_reply_message()
            text_to_tr = reply.text
            
        if not text_to_tr:
            return await event.reply("`No text found to translate.`")

        result = translator.translate(text_to_tr, dest=target_lang.strip())
        
        text = (
            f"**Translation**\n"
            f"---\n"
            f"**Source ({result.src}):** `{text_to_tr}`\n"
            f"**Result ({result.dest}):** `{result.text}`"
        )
        await event.reply(text)
    except Exception as e:
        await event.reply(f"❌ Error: `{str(e)}`")

@asst_cmd(pattern="ask( (.*)|$)", public=True)
async def assistant_ask_ai(event):
    """AI Response for Assistant Bot."""
    query = event.pattern_match.group(1).strip()
    if not query and event.is_reply:
        reply = await event.get_reply_message()
        query = reply.text
        
    if not query:
        return await event.reply("`Please provide a query.`")

    x = await event.reply("`Processing...`")
    
    try:
        # Interface with Groq/OpenAI if configured
        api_key = udB.get_key("GROQ_API_KEY")
        if not api_key:
            return await x.edit("`[ERROR] AI not configured.`")
        
        from groq import Groq
        client = Groq(api_key=api_key)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"You are a professional assistant for the {OWNER_NAME} project. Provide concise, technical advice. No fluff."},
                {"role": "user", "content": query}
            ],
        )
        
        response = completion.choices[0].message.content
        header = f"**AI Response**\n---\n"
        
        if len(response) > 4000:
            with open("response.txt", "w") as f:
                f.write(response)
            await event.reply(header, file="response.txt")
            os.remove("response.txt")
            await x.delete()
        else:
            await x.edit(header + response)
            
    except Exception as e:
        await x.edit(f"❌ Error: `{str(e)}`")
