import glob
import ast

def fix_indent(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changed = True
    while changed:
        changed = False
        try:
            ast.parse("".join(lines))
        except IndentationError as e:
            # e.lineno is 1-indexed
            if e.lineno is not None:
                err_line = e.lineno - 1
                # Try to dedent this line and all subsequent identically-indented lines
                target_indent = len(lines[err_line]) - len(lines[err_line].lstrip(' '))
                if target_indent >= 4:
                    # Let's dedent by 4 spaces
                    for i in range(err_line, len(lines)):
                        curr_indent = len(lines[i]) - len(lines[i].lstrip(' '))
                        if curr_indent >= target_indent and lines[i].strip():
                            lines[i] = lines[i][4:]
                        elif lines[i].strip():
                            break
                    changed = True

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Fixed {filepath}")

for f in glob.glob('canvas/can_bus/*_ecu.py'):
    try:
        ast.parse(open(f, 'r', encoding='utf-8').read())
    except SyntaxError:
        fix_indent(f)
