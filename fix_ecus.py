import os

can_bus_dir = r'canvas/can_bus'
files = [f for f in os.listdir(can_bus_dir) if f.endswith('_ecu.py')]
print(f'Found files: {files}')

for filename in files:
    filepath = os.path.join(can_bus_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    
    new_lines = []
    in_step_function = False
    fixed_count = 0
    
    for line in lines:
        # Detect start of a step function
        if '_step(self):' in line or 'decide_drive_mode_step(self):' in line or 'calculate_energy_recovery_step(self):' in line:
            in_step_function = True
            new_lines.append(line)
            continue
        
        if in_step_function:
            # Detect end of a method
            if line.startswith('    def ') or line.startswith('class '):
                in_step_function = False
                new_lines.append(line)
                continue
            
            # Detect 12 spaces that should be 8
            if line.startswith('            '):
                new_lines.append(line[4:])
                fixed_count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    if fixed_count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f'Fixed {filename} ({fixed_count} lines)')
    else:
        print(f'No changes needed for {filename}')
