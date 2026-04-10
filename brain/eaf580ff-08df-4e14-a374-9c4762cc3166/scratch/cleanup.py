import os

plugins_dir = "plugins"
files_to_remove = [
    "aiwrapper.py", "autopic.py", "audiotools.py", "chatbot.py", 
    "echo.py", "fakeaction.py", "fontgen.py", "giftools.py", 
    "glitch.py", "logo.py", "pdftools.py", "qrcode.py", 
    "unsplash.py", "_wspr.py"
]

for file in files_to_remove:
    path = os.path.join(plugins_dir, file)
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Removed: {path}")
        except Exception as e:
            print(f"Error removing {path}: {e}")
    else:
        print(f"Not found: {path}")
