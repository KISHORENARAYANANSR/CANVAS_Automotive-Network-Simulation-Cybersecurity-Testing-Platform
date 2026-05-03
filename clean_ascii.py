import os
import re

replacements = {
    '→': '->',
    '✅': '[OK]',
    '⚠️': '[WARN]',
    '🔴': '[ERROR]',
    '⚡': '[POW]',
    '🌡️': '[TEMP]',
    '🚨': '[CRIT]',
    '🔋': '[BATT]',
    '🔄': '[RUN]',
    '🚗': '[CAR]',
    '🔑': '[KEY]',
    '👋': '[BYE]',
    '⚙️': '[CONFIG]',
    '📄': '[LOG]',
    '🚀': '[BOOST]',
    '⛽': '[GAS]',
    '⏱': '[TIME]',
    '🔥': '[HOT]',
    '⚡': '[POW]',
    '✓': '[DONE]',
    '⬤': '*',
    '─': '-',
    '═': '=',
    '│': '|',
    '●': '*',
    '\u2192': '->',
    '\u2705': '[OK]',
}

def clean_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return

    original_content = content
    for non_ascii, ascii_val in replacements.items():
        content = content.replace(non_ascii, ascii_val)
    
    # Generic sweep for remaining non-ASCII characters
    def replace_non_ascii(match):
        char = match.group(0)
        return replacements.get(char, ' ')

    content = re.sub(r'[^\x00-\x7F]', replace_non_ascii, content)

    if content != original_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Cleaned {path}')

for root, dirs, files in os.walk('canvas'):
    for file in files:
        if file.endswith('.py'):
            clean_file(os.path.join(root, file))
