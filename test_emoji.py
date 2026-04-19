import os
import re
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

EMOJI_RE = re.compile(
    r'['
    r'\U00002600-\U000027BF' # Misc Symbols & Dingbats
    r'\U0001F300-\U0001F6FF' # Misc Symbols and Pictographs, Emoticons, Transport
    r'\U0001F900-\U0001F9FF' # Supplemental Symbols and Pictographs
    r'\U0001FA70-\U0001FAFF' # Symbols and Pictographs Extended-A
    r'\U0000FE00-\U0000FE0F' # Variation Selectors
    r']', flags=re.UNICODE
)

def is_char_emoji(char: str) -> bool:
    if EMOJI_RE.search(char):
        return True
    return unicodedata.category(char) == 'So'

def get_emoji_font(font_size: int):
    mac_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if mac_path.exists():
        return ImageFont.truetype(str(mac_path), font_size)
    return None

def _draw_text_with_fallback(draw, pos, text, font, fill, emoji_font=None, **kwargs):
    x, y = pos
    for char in text:
        use_font = font
        is_emoji = is_char_emoji(char)
        if is_emoji and emoji_font:
            use_font = emoji_font
            draw.text((int(x), int(y)), char, font=use_font, embedded_color=True, **kwargs)
        else:
            draw.text((int(x), int(y)), char, font=use_font, fill=fill, **kwargs)
        
        try:
            bbox = draw.textbbox((x, y), char, font=use_font)
            w = bbox[2] - bbox[0]
            if w == 0 and is_emoji:
                w = use_font.size
        except Exception:
            w, _ = draw.textsize(char, font=use_font)
        x += w
    return x

def test():
    font_size = 52
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
        
    emoji_font = get_emoji_font(font_size)
    print(f"Emoji font loaded: {emoji_font is not None}")
    
    img = Image.new("RGBA", (800, 200), (40, 40, 40, 255))
    draw = ImageDraw.Draw(img)
    
    # Text with emojis
    test_text = "quite thick 📖 🚨 👽"
    _draw_text_with_fallback(draw, (50, 50), test_text, font, (255, 255, 255, 255), emoji_font=emoji_font)
    
    output = "test_emoji_render_v2.png"
    img.save(output)
    print(f"Saved to {output}")

if __name__ == "__main__":
    test()
