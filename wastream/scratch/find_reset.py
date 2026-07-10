with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\index.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'renderSortOrderList(null)' in line:
            print(f'{idx}: {line.strip()}')
        if 'resetForm' in line or 'reset_form' in line or 'resetConfig' in line:
            print(f'{idx}: {line.strip()}')
