import asyncio
import os
import subprocess
import sys

_vars = ["API_ID", "API_HASH", "SESSION", "REDIS_URI", "REDIS_PASSWORD"]

def _check(z):
    new = []
    for var in _vars:
        ent = os.environ.get(var + z, "")
        new.append(ent)
    # At minimum API_ID, API_HASH, SESSION must be present
    if not all(new[:3]):
        return False, new
    return True, new

for z in range(5):
    n = str(z + 1)
    suffix = "" if z == 0 else str(z)
    fine, out = _check(suffix)
    if fine:
        subprocess.Popen(
            [sys.executable, "-m", "pyUltroid", out[0], out[1], out[2], out[3], out[4], n],
            stdin=None,
            stderr=None,
            stdout=None,
            cwd=None,
        )

loop = asyncio.get_event_loop()

try:
    loop.run_forever()
except Exception as er:
    print(er)
finally:
    loop.close()


