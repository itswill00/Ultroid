# Contributing to Ultroid

Thank you for taking the time to contribute! 🎉

## About This Fork

This is a hardened, production-ready fork of [TeamUltroid/Ultroid](https://github.com/TeamUltroid/Ultroid).
Key differences from upstream:
- Rewritten media downloader with yt-dlp attestation, parallel MTProto transfer, and auto-listener.
- Multi-tier authorization system (Owner → Full Sudo → Scoped Sudo → Public + Captcha).
- Optimized database layer with security-aware TTL for auth keys.
- Runtime mode switching (`RUNTIME_MODE=user|bot|dual`).

## How to Contribute

### Opening an Issue
- Search for existing similar issues first.
- For bug reports: include your Python version, platform (VPS/Termux/Docker), and the full traceback from `ultroid.log`.
- For feature requests: describe the use-case concisely.

### Submitting a Pull Request

1. **Fork** this repository.
2. **Create a branch** with a descriptive name: `fix/upload-cache-leak` or `feat/auto-yt-detect`.
3. **Make your changes** — keep commits focused (one concern per commit).
4. **Sign off** your commits with `git commit -s` (DCO compliance).
5. **Open a Pull Request** with a clear title and a description of what changed and why.

### Code Style
- Format: follow the existing style (no reformatting of unrelated lines).
- Async: always use `asyncio.get_running_loop()`, not `get_event_loop()`.
- Imports: absolute imports preferred; avoid importing inside hot loops.
- Logging: use `LOGS.info/warning/error` — never bare `print()` in production paths.
- Tests: if your change touches the downloader or extractor, test with at least one YT and one TikTok URL.

### Commit Message Format
```
type(scope): short description

Longer explanation if needed.

Signed-off-by: Your Name <your@email.com>
```
Types: `fix`, `feat`, `perf`, `refactor`, `docs`, `chore`.

---

Thanks again — every contribution makes this better. 💫
