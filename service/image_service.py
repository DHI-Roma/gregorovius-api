import re
from pathlib import Path

def generate_image_map():
    img_dir = Path('./img/webp')
    img_map = {}
    position_map = {}
    for img in sorted(img_dir.iterdir()):
        parts = img.stem.split("_")

        identifier_parts_delimiter = -1

        if "_quer_" in img.stem:
            identifier_parts_delimiter = -2

        letter_id = "_".join(parts[:identifier_parts_delimiter])
        label = parts[-1]

        if letter_id not in img_map:
            img_map[letter_id] = {}
            position_map[letter_id] = 0

        img_map[letter_id][position_map[letter_id]] = {
            'name': img.name,
            'label': label
        }

        position_map[letter_id] += 1

    return img_map

