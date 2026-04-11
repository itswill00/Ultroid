import ast
import os
import re
from pathlib import Path

def extract_strings_from_node(node):
    strings = []
    if isinstance(node, ast.Str):
        strings.append(node.s)
    elif isinstance(node, ast.JoinedStr):
        for value in node.values:
            if isinstance(value, ast.Str):
                strings.append(value.s)
    return strings

def analyze_file(filepath):
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if func_name in ('eor', 'edit', 'reply', 'send_message', 'answer'):
                        for arg in node.args:
                            strs = extract_strings_from_node(arg)
                            for s in strs:
                                if len(s.strip()) > 2:
                                    results.append((node.lineno, func_name, s.strip()))
    except Exception as e:
        pass
        
    return results

def main():
    root_dir = Path("f:/ultroid/plugins")
    findings = []
    
    # List of un-professional patterns
    unprofessional_patterns = [
        re.compile(r'[✨⭐🔥💥⚡🌋🙋🤷❌✅✘✔🎉🎊🎶😁😂😅😆😉😊😋😎😍💖]'), # Emoticons/Emojis
        re.compile(r'\b(oops|uh oh|yay|woohoo|lol|lmao|hehe|haha)\b', re.IGNORECASE), # Conversational
        re.compile(r'(~|_|-)'), # Gimmicky formatting (maybe too broad, we'll see)
    ]
    
    for filepath in root_dir.glob("**/*.py"):
        extracted = analyze_file(filepath)
        for lineno, func, text in extracted:
            for pattern in unprofessional_patterns:
                if pattern.search(text):
                    if "_" not in text and "-" not in text: # Skip simple underscores
                        findings.append(f"{filepath.name}:{lineno} [{func}] -> {textrepr(text)}")
                    elif pattern.pattern.startswith('[✨'): # Must include emojis
                        findings.append(f"{filepath.name}:{lineno} [{func}] -> {textrepr(text)}")

    # Dedup and sort
    with open("scratch/audit_report.txt", "w", encoding="utf-8") as out:
        for f in set(findings):
            out.write(f + "\n")
            
def textrepr(text):
    if len(text) > 80:
        return text[:77] + "..."
    return text

if __name__ == "__main__":
    main()
