with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\services\stream.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'def _get_sources_for_service' in line:
            print(f'{idx}: {line.strip()}')
