with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\services\stream.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'deduplicate_results' in line or 'dedup' in line.lower():
            print(f'{idx}: {line.rstrip()}')
