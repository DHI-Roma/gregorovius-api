import re
from pathlib import Path

def generate_image_map():
    img_dir = Path('./img/webp')
    img_map = {}
    for img in img_dir.iterdir():
        parts = img.stem.split("_")

        identifier_parts_delimiter = -1

        if "_quer_" in img.stem:
            identifier_parts_delimiter = -2

        letter_id = "_".join(parts[:identifier_parts_delimiter])
        position_label = parts[-1]

        if position_label.isnumeric():
            position = int(position_label)
        elif "r" in position_label:
            position = ((int(re.sub(r'[a-z]', "", position_label)) - 1) * 2) + 1
        elif "v" in position_label:
            position = int(re.sub(r'[a-z]', "", position_label)) * 2

        if letter_id not in img_map:
            img_map[letter_id] = {}
        img_map[letter_id][position] = {
            'name': img.name,
            'label': position_label
        }

    return img_map
