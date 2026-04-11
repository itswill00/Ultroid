from pyUltroid.dB._core import HELP
print("HELP Categories:", list(HELP.keys()))
if "Inline" in HELP:
    print("Inline Plugins:", list(HELP["Inline"].keys()))
