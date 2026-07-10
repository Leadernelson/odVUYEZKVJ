with open(r'C:\Users\Lukas\Desktop\Instantio\wastream\api\routes.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if '/admin/api' in line or 'router.get' in line or 'router.post' in line:
            print(f'{idx}: {line.strip()}')
