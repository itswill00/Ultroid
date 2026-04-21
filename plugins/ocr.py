# Ultroid - OCR Plugin
# Integrated by Antigravity (Minimalist Edition)

import os

# Free OCR API: https://ocr.space/ocrapi
from . import LOGS, eor, get_help, udB, ultroid_cmd

__doc__ = get_help("ocr")

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
        from pyUltroid.fns.tools import ocr_space
        results = await ocr_space(dl, api_key=OCR_API_KEY)

        if results:
            await msg.edit(f"**OCR Result:**\n\n`{results}`")
        else:
            await msg.edit("`Could not find any text in this image or processing failed.`")

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
