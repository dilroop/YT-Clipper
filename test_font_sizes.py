from PIL import ImageFont, Image
from pathlib import Path

def test_font_sizes():
    mac_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    sizes = [38, 44, 52, 54, 60, 64, 128]
    for size in sizes:
        try:
            font = ImageFont.truetype(mac_path, size)
            print(f"Success loading size {size}")
        except Exception as e:
            print(f"Failed loading size {size}: {e}")

if __name__ == "__main__":
    test_font_sizes()
