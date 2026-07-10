with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'translations[' in line or 'data-i18n' in line:
            if idx > 3800:
                print(f'{idx}: {line.strip()}')
