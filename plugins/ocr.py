# Ultroid - OCR Plugin
# Integrated by Antigravity (Minimalist Edition)

import os
from . import ultroid_cmd, eor, get_string, LOGS, udB, bash
from pyUltroid.fns.helper import async_searcher

# Free OCR API: https://ocr.space/ocrapi
OCR_API_KEY = udB.get_key("OCR_API_KEY") or "helloworld"

@ultroid_cmd(pattern="ocr$", fullsudo=True)
async def ocr_reader(e):
    if not e.reply_to_msg_id:
        return await eor(e, "`Reply to an image or document to extract text.`")
    
    reply = await e.get_reply_message()
    if not (reply.photo or (reply.document and reply.document.mime_type.startswith("image"))):
        return await eor(e, "`Reply to an image file only.`")
    
    msg = await eor(e, "`Extracting text...`")
    
    # Download the media
    dl = await reply.download_media("temp/")
    
    try:
        # OCR.space API works well with direct reachable URLs or multipart upload.
        # For simplicity and to avoid complex Form-Data in async_searcher, 
        # we'll use a direct POST to the API if possible, or use the multipart helper.
        
        # Since async_searcher is already there, let's use it with the 'data' kwarg.
        import aiohttp
        data = aiohttp.FormData()
        data.add_field('apikey', OCR_API_KEY)
        data.add_field('language', 'eng')
        data.add_field('file', open(dl, 'rb'))
        
        response = await async_searcher(
            "https://api.ocr.space/parse/image",
            post=True,
            data=data,
            re_json=True
        )
        
        if response and response.get("ParsedResults"):
            results = response["ParsedResults"][0].get("ParsedText")
            if results:
                await msg.edit(f"**OCR Result:**\n\n`{results}`")
            else:
                await msg.edit("`Could not find any text in this image.`")
        else:
            error = response.get("ErrorMessage") or "Unknown error"
            await msg.edit(f"**OCR Error:** `{error}`")
            
    except Exception as er:
        LOGS.exception(er)
        await msg.edit(f"`Error: {str(er)}`")
    finally:
        if os.path.exists(dl):
            os.remove(dl)

__doc__ = """
**OCR (Optical Character Recognition)**

- `.ocr`: Extract text from a replied image.
"""
