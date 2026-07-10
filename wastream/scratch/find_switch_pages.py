with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\dashboard.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'switchPageMobile' in line or 'function switchPage' in line:
            print(f'{idx}: {line.strip()}')
