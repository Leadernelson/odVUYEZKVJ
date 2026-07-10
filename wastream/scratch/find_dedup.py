with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\services\stream.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'dedup' in line.lower() or 'duplicate' in line.lower() or 'seen' in line.lower():
            print(f'{idx}: {line.rstrip()}')
