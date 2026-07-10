with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'document.getElementById' in line and 'key' in line:
            print(f'{idx}: {line.strip()}')
        if 'Object.keys(els)' in line or 'for (const key in els)' in line:
            print(f'{idx}: {line.strip()}')
