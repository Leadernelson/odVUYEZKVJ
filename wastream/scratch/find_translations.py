import os
for root, dirs, files in os.walk(r'C:\Users\Lukas\Desktop\Instantio'):
    for file in files:
        if file == 'translations.js':
            print(os.path.join(root, file))
