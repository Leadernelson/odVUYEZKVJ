with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\debrid\torbox.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'def group_identical' in line:
            print(f'Found at line {idx}')
            break
