with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'sort' in line.lower():
            if idx > 1500:
                print(f'{idx}: {line.strip()}')
