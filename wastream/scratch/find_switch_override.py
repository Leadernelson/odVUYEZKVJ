with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\templates\dashboard.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'originalSwitchPage' in line or 'switchPage = function' in line or 'switchPage(' in line:
            if idx > 6500:
                print(f'{idx}: {line.strip()}')
