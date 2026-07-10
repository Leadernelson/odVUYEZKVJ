with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\utils\helpers.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'extract_language_from_tokens' in line or 'def ' in line:
            if 'extract_language' in line or 'vostfr' in line.lower() or 'multi' in line.lower():
                print(f'{idx}: {line.strip()}')
