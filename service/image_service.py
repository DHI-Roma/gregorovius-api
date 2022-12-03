from pathlib import Path

def generate_image_map():
    img_dir = Path('./img/webp')
    img_map = {}
    for img in img_dir.iterdir():
        parts = img.stem.split("_")
        letter_id = "_".join(parts[:-1])
        position = int(parts[-1])
        if letter_id not in img_map:
            img_map[letter_id] = {}
        img_map[letter_id][position] = img.name

    return img_map
