with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'data-i18n' in line and 'function' in line or 'translate' in line:
            print(f'{idx}: {line.strip()}')
