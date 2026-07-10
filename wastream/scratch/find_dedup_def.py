import os
for root, dirs, files in os.walk(r'C:\Users\Lukas\Desktop\Instantio\wastream'):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                if 'def deduplicate' in line:
                    print(f'{fpath}:{idx}: {line.rstrip()}')
