# Ultroid ~ UserBot
# Copyright (C) 2023-2024 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
**Get Weather Data using OpenWeatherMap API**
❍  Commands Available -

• `{i}weather` <city name>
    Shows the Weather of Cities

• `{i}air` <city name>
    Shows the Air Condition of Cities
"""

import datetime
import time
from datetime import timedelta

import aiohttp
import pytz

from . import async_searcher, get_string, udB, ultroid_cmd


async def get_timezone(offset_seconds, use_utc=False):
    offset = timedelta(seconds=offset_seconds)
    hours, remainder = divmod(offset.seconds, 3600)
    sign = "+" if offset.total_seconds() >= 0 else "-"
    timezone = "UTC" if use_utc else "GMT"
    if use_utc:
        for m in pytz.all_timezones:
            tz = pytz.timezone(m)
            now = datetime.datetime.now(tz)
            if now.utcoffset() == offset:
                return f"{m} ({timezone}{sign}{hours:02d})"
    else:
        for m in pytz.all_timezones:
            tz = pytz.timezone(m)
            if m.startswith("Australia/"):
                now = datetime.datetime.now(tz)
                if now.utcoffset() == offset:
                    return f"{m} ({timezone}{sign}{hours:02d})"
        for m in pytz.all_timezones:
            tz = pytz.timezone(m)
            now = datetime.datetime.now(tz)
            if now.utcoffset() == offset:
                return f"{m} ({timezone}{sign}{hours:02d})"
        return "Timezone not found"

async def getWindinfo(speed: str, degree: str) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = round(degree / (360.00 / len(dirs)))
    kmph = str(float(speed) * 3.6) + " km/h"
    return f"[{dirs[ix % len(dirs)]}] {kmph}"

async def get_air_pollution_data(latitude, longitude, api_key):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if "list" in data:
                air_pollution = data["list"][0]
                return air_pollution
            else:
                return None


@ultroid_cmd(pattern="weather ?(.*)")
async def weather(event):
    if event.fwd_from:
        return
    msg = await event.eor(get_string("com_1"))
    x = udB.get_key("OPENWEATHER_API")
    if x is None:
        await event.eor(
            "No API found. Get One from [Here](https://api.openweathermap.org)\nAnd Add it in OPENWEATHER_API Redis Key",
            time=8,
        )
        return
    input_str = event.pattern_match.group(1)
    if not input_str:
        await event.eor("No Location was Given...", time=5)
        return
    elif input_str == "butler":
        await event.eor("search butler,au for australila", time=5)
    sample_url = f"https://api.openweathermap.org/data/2.5/weather?q={input_str}&APPID={x}&units=metric"
    try:
        response_api = await async_searcher(sample_url, re_json=True)
        if response_api["cod"] == 200:
            country_time_zone = int(response_api["timezone"])
            tz = f"{await get_timezone(country_time_zone)}"
            sun_rise_time = int(response_api["sys"]["sunrise"]) + country_time_zone
            sun_set_time = int(response_api["sys"]["sunset"]) + country_time_zone
            await msg.edit(
                f"🌍 **{response_api['name']}, {response_api['sys']['country']}**\n"
                f"---"
                f"\n🌤️ **Weather:** {response_api['weather'][0]['description'].title()}"
                f"\n🌐 **Timezone:** {tz}"
                f"\n🌅 **Sunrise:** {time.strftime('%H:%M:%S', time.gmtime(sun_rise_time))}"
                f"\n🌇 **Sunset:** {time.strftime('%H:%M:%S', time.gmtime(sun_set_time))}"
                f"\n💨 **Wind:** {await getWindinfo(response_api['wind']['speed'], response_api['wind']['deg'])}"
                f"\n🌡️ **Temp:** {response_api['main']['temp']}°C (Feels {response_api['main']['feels_like']}°C)"
                f"\n📉 **Min:** {response_api['main']['temp_min']}°C | **Max:** {response_api['main']['temp_max']}°C"
                f"\n🎈 **Pressure:** {response_api['main']['pressure']} hPa"
                f"\n💧 **Humidity:** {response_api['main']['humidity']}%"
                f"\n👁️ **Visibility:** {response_api['visibility']}m"
                f"\n☁️ **Clouds:** {response_api['clouds']['all']}%"
            )
        else:
            await msg.edit(response_api["message"])
    except Exception as e:
        await event.eor(f"An unexpected error occurred: {str(e)}", time=5)


@ultroid_cmd(pattern="air ?(.*)")
async def air_pollution(event):
    if event.fwd_from:
        return
    msg = await event.eor(get_string("com_1"))
    x = udB.get_key("OPENWEATHER_API")
    if x is None:
        await event.eor(
            "No API found. Get One from [Here](https://api.openweathermap.org)\nAnd Add it in OPENWEATHER_API Redis Key",
            time=8,
        )
        return
    input_str = event.pattern_match.group(1)
    if not input_str:
        await event.eor("`No Location was Given...`", time=5)
        return
    if input_str.lower() == "perth":
        geo_url = f"https://geocode.xyz/perth%20au?json=1"
    else:
        geo_url = f"https://geocode.xyz/{input_str}?json=1"
    geo_data = await async_searcher(geo_url, re_json=True)
    try:
        longitude = geo_data["longt"]
        latitude = geo_data["latt"]
    except KeyError as e:
        LOGS.info(e)
        await event.eor("`Unable to find coordinates for the given location.`", time=5)
        return
    try:
        city = geo_data["standard"]["city"]
        prov = geo_data["standard"]["prov"]
    except KeyError as e:
        LOGS.info(e)
        await event.eor("`Unable to find city for the given coordinates.`", time=5)
        return
    air_pollution_data = await get_air_pollution_data(latitude, longitude, x)
    if air_pollution_data is None:
        await event.eor(
            "`Unable to fetch air pollution data for the given location.`", time=5
        )
        return
    await msg.edit(
        f"🏙️ **{city}, {prov}**\n"
        f"---"
        f"\n🍃 **AQI:** {air_pollution_data['main']['aqi']}"
        f"\n🧪 **CO:** {air_pollution_data['components']['co']}µg/m³"
        f"\n🧪 **NO:** {air_pollution_data['components']['no']}µg/m³"
        f"\n🧪 **NO₂:** {air_pollution_data['components']['no2']}µg/m³"
        f"\n🌤️ **Ozone:** {air_pollution_data['components']['o3']}µg/m³"
        f"\n🧪 **SO₂:** {air_pollution_data['components']['so2']}µg/m³"
        f"\n🧪 **NH₃:** {air_pollution_data['components']['nh3']}µg/m³"
        f"\n🌫️ **PM₂.₅:** {air_pollution_data['components']['pm2_5']}"
        f"\n🌫️ **PM₁₀:** {air_pollution_data['components']['pm10']}"
    )
