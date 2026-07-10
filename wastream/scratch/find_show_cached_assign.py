with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'showOnlyCached' in line and '=' in line:
            if idx > 2500:
                print(f'{idx}: {line.strip()}')
