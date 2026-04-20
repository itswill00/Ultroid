# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available

• `{i}health`
    Get a random daily health tip.

• `{i}bmi <weight_kg> <height_cm>`
    Calculate your Body Mass Index (BMI).
"""

import random

from . import ultroid_cmd

HEALTH_TIPS = [
    "Minum setidaknya 8 gelas air setiap hari untuk menjaga hidrasi tubuh.",
    "Berjalan kaki selama 30 menit setiap hari dapat meningkatkan kesehatan jantung.",
    "Kurangi konsumsi gula berlebih untuk menghindari risiko diabetes.",
    "Pastikan tidur selama 7-8 jam setiap malam untuk pemulihan otak.",
    "Sediakan waktu untuk meditasi atau relaksasi guna mengurangi stres.",
    "Konsumsi lebih banyak sayuran hijau dan buah-buaran setiap hari.",
    "Jangan lewatkan sarapan pagi untuk memberikan energi pada aktivitas Anda.",
    "Kurangi penggunaan perangkat elektronik sebelum tidur untuk kualitas tidur yang lebih baik.",
    "Lakukan peregangan singkat setiap 1 jam jika Anda bekerja di depan komputer.",
    "Cuci tangan dengan sabun secara rutin untuk mencegah penularan penyakit."
]

@ultroid_cmd(pattern="health$")
async def health_tips(event):
    tip = random.choice(HEALTH_TIPS)
    await event.eor(f"🍏 **Health Tip of the Day:**\n\n`{tip}`")

@ultroid_cmd(pattern="bmi( (.*)|$)")
async def calculate_bmi(event):
    input_str = event.pattern_match.group(1).strip()
    if not input_str or " " not in input_str:
        return await event.eor("Usage: `{i}bmi <weight_kg> <height_cm>`\nExample: `{i}bmi 70 175`", time=5)

    try:
        weight, height = map(float, input_str.split())
        height_m = height / 100
        bmi = weight / (height_m * height_m)

        category = ""
        if bmi < 18.5: category = "Underweight (Kekurangan berat badan)"
        elif 18.5 <= bmi < 25: category = "Normal weight (Ideal)"
        elif 25 <= bmi < 30: category = "Overweight (Kelebihan berat badan)"
        else: category = "Obese (Obesitas)"

        res = "📊 **BMI Calculator**\n\n"
        res += f"• **Weight:** {weight} kg\n"
        res += f"• **Height:** {height} cm\n"
        res += f"• **BMI Score:** `{bmi:.2f}`\n"
        res += f"• **Category:** `{category}`"

        await event.eor(res)
    except Exception:
        await event.eor("Please provide valid numbers for weight and height.")
