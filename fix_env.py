#!/usr/bin/env python3
"""
Ultroid .env Validator & Cleaner
Jalankan di direktori bot: python3 fix_env.py

Fungsi:
- Deteksi dan hapus CRLF (Windows line endings)
- Hapus trailing whitespace/spasi tersembunyi di setiap baris
- Deteksi keys dengan value kosong
- Deteksi value yang mengandung karakter aneh (\r, tab, dll)
- Cetak ringkasan semua key yang terbaca
"""

import os
import sys
import re

ENV_FILE = ".env"
MANDATORY_KEYS = ["API_ID", "API_HASH", "SESSION"]
INT_KEYS = ["API_ID", "LOG_CHANNEL"]
SENSITIVE_KEYS = ["SESSION", "BOT_TOKEN", "GROQ_API_KEY", "API_HASH"]


def mask(val: str, key: str) -> str:
    if key in SENSITIVE_KEYS and val and len(val) > 8:
        return val[:6] + "..." + val[-4:]
    return val


def fix_and_validate(path: str):
    if not os.path.exists(path):
        print(f"[ERROR] File tidak ditemukan: {path}")
        sys.exit(1)

    with open(path, "rb") as f:
        raw = f.read()

    # Deteksi CRLF
    crlf_count = raw.count(b"\r\n")
    has_crlf = crlf_count > 0

    if has_crlf:
        print(f"[WARN]  File punya {crlf_count} CRLF line endings (Windows format).")
        fixed = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        with open(path, "wb") as f:
            f.write(fixed)
        print(f"[FIX]   CRLF dihapus. File disimpan ulang dengan Unix LF.\n")
        raw = fixed

    lines = raw.decode("utf-8", errors="replace").splitlines()

    parsed = {}
    warnings = []
    errors = []

    for i, line in enumerate(lines, 1):
        # Hapus trailing whitespace / spasi tersembunyi
        clean = line.rstrip()

        # Abaikan komentar dan baris kosong
        stripped = clean.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Harus ada tanda =
        if "=" not in stripped:
            warnings.append(f"Baris {i}: format tidak valid (tidak ada '='): {clean!r}")
            continue

        key, _, val = stripped.partition("=")
        key = key.strip()
        val = val.strip()

        # Cek value mengandung karakter aneh
        if "\r" in val:
            warnings.append(f"Baris {i}: key '{key}' masih punya \\r di value!")
            val = val.replace("\r", "")

        if "\t" in val:
            warnings.append(f"Baris {i}: key '{key}' punya TAB di value — akan dibersihkan.")
            val = val.replace("\t", "")

        # Cek kutip berlebih
        if (val.startswith('"') and val.endswith('"')) or \
           (val.startswith("'") and val.endswith("'")):
            warnings.append(
                f"Baris {i}: key '{key}' punya tanda kutip — decouple tidak perlu kutip, "
                f"akan dibersihkan."
            )
            val = val[1:-1]

        parsed[key] = val

    print("=" * 60)
    print("HASIL VALIDASI .env")
    print("=" * 60)

    # Cek mandatory keys
    for mk in MANDATORY_KEYS:
        if mk not in parsed:
            errors.append(f"[MISSING] Key wajib tidak ditemukan: '{mk}'")
        elif not parsed[mk]:
            errors.append(f"[EMPTY]   Key wajib kosong: '{mk}'")
        else:
            mv = mask(parsed[mk], mk)
            print(f"[OK]    {mk:20s} = {mv}")

    print()

    # Tampilkan semua key yang terbaca
    print(f"Semua key yang terbaca ({len(parsed)} total):")
    print("-" * 60)
    for key, val in sorted(parsed.items()):
        if key in MANDATORY_KEYS:
            continue
        status = "[EMPTY]" if not val else "[OK]   "
        display_val = "" if not val else mask(val, key)
        # Cast check untuk INT keys
        if key in INT_KEYS and val:
            try:
                int(val)
            except ValueError:
                warnings.append(f"Key '{key}' harus integer, tapi value-nya: {val!r}")
                status = "[WARN] "
        print(f"  {status} {key:30s} = {display_val}")

    print()

    if warnings:
        print("PERINGATAN:")
        for w in warnings:
            print(f"  ⚠  {w}")
        print()

    if errors:
        print("ERROR KRITIS:")
        for e in errors:
            print(f"  ✗  {e}")
        print()
        print("Bot TIDAK AKAN bisa start sebelum error di atas diperbaiki.")
    else:
        print("✓ Tidak ada error kritis ditemukan.")

    print("=" * 60)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ENV_FILE
    fix_and_validate(path)
