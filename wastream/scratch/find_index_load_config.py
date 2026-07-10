with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'deduplicate_results' in line or 'show_only_cached' in line:
            if idx > 3500:
                print(f'{idx}: {line.strip()}')
