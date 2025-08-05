import os
import csv
import time
import queue
from PIL import Image

def initialize_data_files(app):
    """延迟初始化数据文件，首次需要反馈时执行"""
    if not app.data_initialized:
        if not os.path.exists(app.data_folder):
            os.makedirs(app.data_folder)
        
        if not os.path.exists(app.metadata_file):
            with open(app.metadata_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['file_name', 'text', 'feedback'])
        
        app.data_initialized = True

def save_data(app, image, text, feedback):
    file_name = f"{int(time.time())}.png"
    file_path = os.path.join(app.data_folder, file_name)
    image.save(file_path, 'PNG')

    rows = []
    with open(app.metadata_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    updated = False
    for row in rows[1:]:
        if row[1] == text:
            row[2] = feedback
            updated = True
            break

    if not updated:
        rows.append([file_name, text, feedback])

    with open(app.metadata_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def check_repetition(s, repeats=12):
    for pattern_length in range(1, len(s) // repeats + 1):
        for start in range(len(s) - repeats * pattern_length + 1):
            pattern = s[start:start + pattern_length]
            if s[start:start + repeats * pattern_length] == pattern * repeats:
                return True
    return False

def load_scaled_image(image_path, dpi_scale=1.0):
    if not os.path.exists(image_path):
        import sys
        alt_path = os.path.join(os.path.dirname(sys.executable), os.path.basename(image_path))
        if os.path.exists(alt_path):
            image_path = alt_path
        else:
            print(f"找不到图像文件: {image_path}")
            return Image.new('RGB', (64, 64), (200, 200, 200))

    image = Image.open(image_path)
    new_width = int(image.width * dpi_scale)
    new_height = int(image.height * dpi_scale)
    return image.resize((new_width, new_height), Image.LANCZOS)

def pad_image(img, out_size):
    x_img, y_img = out_size
    background = Image.new('RGB', (x_img, y_img), (255, 255, 255))
    width, height = img.size
    
    if width < x_img and height < y_img:
        x = (x_img - width) // 2
        y = (y_img - height) // 2
        background.paste(img, (x, y))
    else:
        scale = min(x_img / width, y_img / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        x = (x_img - new_width) // 2
        y = (y_img - new_height) // 2
        background.paste(img_resized, (x, y))
        
    return background
