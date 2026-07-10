import ast, sys

# Search for model_type or source_type field in stream results / scrapers
files = [
    r'C:\Users\Lukas\Desktop\Instantio\wastream\services\stream.py',
    r'C:\Users\Lukas\Desktop\Instantio\wastream\scrapers\torznab\base.py',
]

for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                low = line.lower()
                if 'model_type' in low or 'source_type' in low or '"type"' in low or 'is_torrent' in low or "'torrent'" in low:
                    print(f'{fpath}:{idx}: {line.rstrip()}')
    except FileNotFoundError:
        print(f'NOT FOUND: {fpath}')
