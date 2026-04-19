from PIL import Image, ImageFont, ImageDraw
import os

def test_getmask():
    font_size = 52
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    chars = ["A", "g", "📖", "👽", "🚨"]
    for c in chars:
        mask = font.getmask(c)
        bbox = mask.getbbox()
        print(f"Char: {c}, BBox: {bbox}")

if __name__ == "__main__":
    test_getmask()
