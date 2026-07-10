with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'sources' in line or 'source' in line or 'wawacity' in line:
            print(f'{idx}: {line.strip()}')
