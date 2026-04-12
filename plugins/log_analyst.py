"""
AOSP Log Analyst — AI Powered Diagnostic Tool
Analyze large log files (Logcat, Dmesg, Build logs) using Groq AI.

Commands:
    .analyze / .analise <reply_to_file> [instruction]
"""

import os
import re
import gzip
import time
import asyncio
from io import BytesIO

from telethon import events
from . import udB, LOGS, ultroid_cmd, asst, OWNER_NAME, get_string

# ── Configuration ──────────────────────────────────────────────────────────

# Max lines to send to AI (Digest size)
MAX_DIGEST_LINES = 250
# Context window for each detected error (lines before/after)
CONTEXT_WINDOW = 15



# ── LOG PATTERNS ────────────────────────────────────────────────────────────

# Patterns indicating high-priority diagnostic info
CRITICAL_PATTERNS = [
    r"FATAL EXCEPTION",
    r"Process: .* crashed",
    r"SIGSEGV",
    r"SIGABRT",
    r"Kernel panic",
    r"Oops: ",
    r"avc:  denied",
    r"ninja: build stopped",
    r"FAILED:",
    r"error:",
    r"\*\*\* \*\*\* \*\*\*",  # Tombstone header
    r"Build fingerprint:",
    r"Abort message:",
]

# Patterns for log type detection
TYPE_LOGCAT = re.compile(r"^[0-9-]{5}\s[0-9:.]+\s+[0-9]+\s+[0-9]+\s[VDIWEF]/")
TYPE_DMESG  = re.compile(r"^\[\s*[0-9.]+\].*")

# ── Smapling Logic ──────────────────────────────────────────────────────────

def _smart_sample(content: str) -> str:
    """Extracts critical chunks from a large log file to fit AI context."""
    lines = content.splitlines()
    total_lines = len(lines)
    
    if total_lines <= MAX_DIGEST_LINES:
        return content

    # 1. Identify critical line indices
    critical_indices = []
    for i, line in enumerate(lines):
        if any(re.search(p, line, re.IGNORECASE) for p in CRITICAL_PATTERNS):
            critical_indices.append(i)

    # 2. Extract Head (first 100) and Tail (last 300)
    digest_lines = set(range(min(100, total_lines)))
    digest_lines.update(range(max(0, total_lines - 300), total_lines))

    # 3. Add Context around critical events
    for idx in critical_indices:
        start = max(0, idx - CONTEXT_WINDOW)
        end = min(total_lines, idx + CONTEXT_WINDOW)
        digest_lines.update(range(start, end))

    # 4. Reconstruct and sort
    sorted_indices = sorted(list(digest_lines))
    
    # 5. Build final digest with ellipsis markers
    digest = []
    last_idx = -1
    for idx in sorted_indices:
        if last_idx != -1 and idx > last_idx + 1:
            digest.append("... [lines skipped] ...")
        
        # Truncate overly long individual lines (noise reduction)
        line = lines[idx]
        if len(line) > 500:
            line = line[:500] + " ... [long line truncated]"
            
        digest.append(line)
        last_idx = idx
        
        # Guard against overly large digests
        if len(digest) > MAX_DIGEST_LINES:
            break

    final_text = "\n".join(digest)
    
    # 6. Hard character limit (approx 5k-6k tokens)
    # 18,000 chars ensures we stay well under the 12,000 token limit 
    # even with dense logs.
    if len(final_text) > 18000:
        final_text = final_text[:18000] + "\n... [truncated due to API size limit]"
        
    return final_text



def _detect_type(content: str) -> str:
    # Sampling first 50 lines for detection
    sample = content.splitlines()[:50]
    sample_text = "\n".join(sample)
    
    if "*** *** ***" in sample_text or "Build fingerprint:" in sample_text:
        return "Tombstone / Native Crash"
    if TYPE_LOGCAT.search(sample_text):
        return "Logcat (Android Runtime)"
    if TYPE_DMESG.search(sample_text):
        return "Kernel Dmesg / Kmsg"
    if "ninja: build stopped" in content or "FAILED:" in content:
        return "AOSP Build Log"
    
    return "Generic Log / Text"

# ── AI Integration ─────────────────────────────────────────────────────────

async def _call_log_ai(log_content: str, log_type: str, user_instruction: str = ""):
    """Specialized AI call for log analysis."""
    from pyUltroid.fns.ai_engine import _call_groq
    
    # Deterministic behavior: analyze log technically.
    # Include instruction to respond in user's language.
    system_prompt = (
        "You are an expert AOSP (Android Open Source Project) and Linux Kernel Developer. "
        "Your task is to analyze the provided log digest and provide a Root Cause Analysis (RCA). "
        "Identify crashes, ANRs, boot loops, or build failures. "
        "Provide specific, technical solutions (e.g., adb commands, file paths, SELinux policies). "
        "\n\nCRITICAL RULES:\n"
        "1. Respond in the SAME LANGUAGE as the user's instruction. If no instruction, use English.\n"
        "2. Keep it technical and minimalist (Zero-Gimmick).\n"
        "3. Do not apologize or use conversational filler."
    )
    
    query = (
        f"LOG TYPE: {log_type}\n"
        f"USER INSTRUCTION: {user_instruction or 'Analyze this log for errors.'}\n\n"
        f"LOG DIGEST:\n```\n{log_content}\n```"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    # Use a high-TPM model for heavy log processing
    # llama-3.1-8b-instant typically has 30k-100k TPM limits, 
    # preventing the 413 error seen on the 70b model.
    ans, usage = await _call_groq(messages, model="llama-3.1-8b-instant")
    return ans, usage


# ── COMMAND HANDLER ────────────────────────────────────────────────────────

@ultroid_cmd(pattern="analy[sz]e(?: (.*))?$")
async def _log_analyst(ult):
    # Determine the instruction (text after command)
    instruction = (ult.pattern_match.group(1) or "").strip()
    
    # Must reply to a file/document
    reply = await ult.get_reply_message()
    if not (reply and reply.document):
        return await ult.eor("`Reply to a .log, .txt, or .gz file to analyze.`")

    msg = await ult.eor("`[..] Downloading Log...`")
    
    try:
        # 1. Download File
        media = await ult.client.download_media(reply.document, BytesIO())
        media.seek(0)
        
        # 2. Handle Gzip
        file_name = reply.file.name or "log.txt"
        if file_name.endswith(".gz") or reply.file.mime_type == "application/gzip":
            await msg.edit("`[..] Decompressing Gzip...`")
            try:
                content = gzip.decompress(media.read()).decode("utf-8", errors="replace")
            except Exception:
                return await msg.edit("`[FAIL] Could not decompress Gzip file.`")
        else:
            content = media.read().decode("utf-8", errors="replace")

        if not content.strip():
            return await msg.edit("`[FAIL] Log file is empty.`")

        # 3. Detect Type & Sample
        await msg.edit("`[..] Sampling & Detecting Patterns...`")
        log_type = _detect_type(content)
        digest = _smart_sample(content)
        
        # 4. AI Process
        await msg.edit("`[..] AI Processing Root Cause...`")
        start_time = time.time()
        analysis, usage = await _call_log_ai(digest, log_type, instruction)
        duration = round(time.time() - start_time, 2)
        
        if not analysis:
            return await msg.edit(f"`[AI FAIL] {usage}`")

        # 5. Output (Zero Gimmick / Professional)
        # We don't use fancy boxes unless necessary, keep it clear.
        header = f"[LOG ANALYSIS]\nType: {log_type}\n"
        footer = f"\n\n---\n`time: {duration}s | tokens: {usage}`"
        
        final_output = f"{header}\n{analysis}{footer}"
        
        if len(final_output) > 4096:
            # Fallback to Telegraph or snippet
            from pyUltroid.fns.ai_engine import fast_telegraph
            url = await fast_telegraph(f"Analysis: {file_name}", final_output)
            if url:
                return await msg.edit(f"`[REPORT]` Analysis is too long. [Read Full Report]({url})", link_preview=True)

        await msg.edit(final_output)

    except Exception as e:
        LOGS.exception(e)
        await msg.edit(f"`[ERROR] {str(e)}`")
