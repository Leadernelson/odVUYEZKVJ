with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\utils\helpers.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'season' in line.lower() or 'episode' in line.lower() or 's0' in line.lower() or 'e0' in line.lower():
            print(f'{idx}: {line.rstrip()}')
