with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\services\stream.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'deduplicate_results' in line or 'display_name' in line.lower() and 'seen' in line.lower():
            print(f'{idx}: {line.rstrip()}')
        if 'seen_name' in line or 'seen_display' in line or 'seen_hash' in line:
            print(f'{idx}: {line.rstrip()}')
