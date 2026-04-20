"""
✘ Help for Wikipedia

• {i}help wikipedia - To see available commands.
"""
# Ultroid Userbot
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""

✘ Commands Available -

• `{i}wiki <search query>`
    Smart Wikipedia search with disambiguation handling.

"""

import wikipedia

from . import *


@ultroid_cmd(pattern="wiki ?(.*)")
async def wiki(e):
    srch = e.pattern_match.group(1)
    if not srch:
        return await e.eor("`Give some text to search on wikipedia !`")

    msg = await e.eor(f"`Searching \"{srch}\" on Wikipedia...`")

    try:
        # Set language to English (default) or detect
        wikipedia.set_lang("en")

        # Get summary with a limit of 3 sentences for conciseness
        mk = wikipedia.summary(srch, sentences=3)

        # Final output formatting
        te = f"📖 **Wikipedia: {srch.title()}**\n\n{mk}\n\n"
        te += f"🔗 [Read More](https://en.wikipedia.org/wiki/{srch.replace(' ', '_')})"

        await msg.edit(te, link_preview=False)

    except wikipedia.exceptions.DisambiguationError as de:
        # Handle multiple results
        options = de.options[:5]
        opt_text = "\n".join([f"• `{opt}`" for opt in options])
        await msg.edit(f"❌ **Ambiguous search!**\n\nDid you mean:\n{opt_text}\n\n`Try a more specific query.`")

    except wikipedia.exceptions.PageError:
        await msg.edit(f"❌ **Page not found!**\nCould not find any Wikipedia entry for `{srch}`.")

    except Exception as err:
        LOGS.exception(err)
        await msg.edit(f"**ERROR** : {str(err)}")
