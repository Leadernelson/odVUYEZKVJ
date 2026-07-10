with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\config\settings.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'MOVIX' in line:
            print(f'{idx}: {line.strip()}')
