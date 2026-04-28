import os
import re
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    from backend.core.constants import BASE_DIR, FONTS_DIR
except ImportError:
    # Fallback for standalone
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    FONTS_DIR = BASE_DIR / "fonts"

# --- Emoji Support ---
EMOJI_RE = re.compile(
    r'['
    r'\U00002100-\U000027BF' # Symbols, arrows, dingbats
    r'\U00002B00-\U00002BFF' # Misc symbols and arrows
    r'\U0001F000-\U0001F6FF' # Emoticons, transport, symbols
    r'\U0001F900-\U0001F9FF' # Supplemental symbols
    r'\U0001FA70-\U0001FAFF' # Symbols-a
    r'\U0000FE00-\U0000FE0F' # Variation selectors
    r']', flags=re.UNICODE
)

def is_char_emoji(char: str) -> bool:
    if EMOJI_RE.search(char):
        return True
    cat = unicodedata.category(char)
    if cat.startswith('S'):
         return True
    if '\U0001F000' <= char <= '\U0001FFFF':
        return True
    return False

_EMOJI_FONT_CACHE = {}
_SUPPORTED_EMOJI_SIZES = [160, 96, 64, 52, 48, 40, 32, 20]

def get_emoji_font(font_size: int) -> ImageFont.FreeTypeFont | None:
    if font_size in _EMOJI_FONT_CACHE:
        return _EMOJI_FONT_CACHE[font_size]
        
    custom_path = BASE_DIR / "assets" / "fonts" / "custom_emoji.ttf"
    mac_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    
    for path in [custom_path, mac_path]:
        if not path.exists():
            continue
            
        try_sizes = [font_size]
        if "Apple Color Emoji" in str(path):
            fallbacks = sorted(_SUPPORTED_EMOJI_SIZES, key=lambda s: abs(s - font_size))
            try_sizes.extend(fallbacks)

        for s in try_sizes:
            try:
                font = ImageFont.truetype(str(path), s)
                _EMOJI_FONT_CACHE[font_size] = font
                return font
            except Exception:
                continue
    return None

def get_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont:
    """Return a Pillow font, trying the user-supplied path then common system paths."""
    
    font_map = {
        "Arial": "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Helvetica": "/System/Library/Fonts/Helvetica.ttc",
        "Times New Roman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "Impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
        "Courier New": "/System/Library/Fonts/Supplemental/Courier New.ttf"
    }
    
    candidates = [
        font_path,
        str(FONTS_DIR / font_path) if font_path and (font_path.endswith('.ttf') or font_path.endswith('.ttc')) else None,
        str(FONTS_DIR / f"{font_path}.ttf") if font_path and not (font_path.endswith('.ttf') or font_path.endswith('.ttc')) else None,
        font_map.get(font_path) if font_path else None,
        "/System/Library/Fonts/Supplemental/Arial.ttf",          # macOS
        "/System/Library/Fonts/Helvetica.ttc",                    # macOS (alt)
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Linux
        "C:\\Windows\\Fonts\\arialbd.ttf",                        # Windows Bold
        "C:\\Windows\\Fonts\\arial.ttf",                          # Windows
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    print(f"[WARNING] Could not load font '{font_path}' - falling back to default.")
    return ImageFont.load_default()

def draw_text_with_fallback(draw, pos, text, font, fill, emoji_font=None, **kwargs):
    if not text: return pos[0]
    x, y = pos
    
    # Segment text into chunks of either emojis or regular text to preserve kerning
    segments = []
    if not emoji_font:
        segments = [(text, font, False)]
    else:
        curr_segment = ""
        curr_is_emoji = is_char_emoji(text[0]) if text else False
        for char in text:
            is_emoji = is_char_emoji(char)
            if is_emoji != curr_is_emoji:
                segments.append((curr_segment, emoji_font if curr_is_emoji else font, curr_is_emoji))
                curr_segment = char
                curr_is_emoji = is_emoji
            else:
                curr_segment += char
        segments.append((curr_segment, emoji_font if curr_is_emoji else font, curr_is_emoji))

    for seg_text, seg_font, is_emoji in segments:
        if not seg_text: continue
        if is_emoji:
            draw.text((int(x), int(y)), seg_text, font=seg_font, embedded_color=True, **kwargs)
        else:
            draw.text((int(x), int(y)), seg_text, font=seg_font, fill=fill, **kwargs)
        
        # Advance x by the length of the string segment
        # We use a safety max with bbox to handle large strokes that might bleed out
        sw = kwargs.get('stroke_width', 0)
        bbox = draw.textbbox((0, 0), seg_text, font=seg_font, stroke_width=sw)
        advance = draw.textlength(seg_text, font=seg_font)
        x += max(advance, bbox[2])

    return x

def measure_text_with_fallback(text: str, font, emoji_font=None, **kwargs) -> tuple[int, int]:
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    
    lines = text.split('\n')
    max_w = 0
    
    try:
        ascent, descent = font.getmetrics()
        sw = kwargs.get('stroke_width', 0)
        lh = ascent + descent + int(sw * 2)
    except:
        try:
            bbox = draw.textbbox((0, 0), "Ag", font=font)
            lh = int(bbox[3] - bbox[1])
        except:
            w, h = draw.textsize("Ag", font=font) # type: ignore
            lh = int(h)
    
    for ln in lines:
        if not ln: continue
        # Similar segmenting for measurement
        line_w = 0
        segments = []
        if not emoji_font:
            segments = [(ln, font, False)]
        else:
            curr_segment = ""
            curr_is_emoji = is_char_emoji(ln[0]) if ln else False
            for char in ln:
                is_emoji = is_char_emoji(char)
                if is_emoji != curr_is_emoji:
                    segments.append((curr_segment, emoji_font if curr_is_emoji else font, curr_is_emoji))
                    curr_segment = char
                    curr_is_emoji = is_emoji
                else:
                    curr_segment += char
            segments.append((curr_segment, emoji_font if curr_is_emoji else font, curr_is_emoji))

        for seg_text, seg_font, is_emoji in segments:
            if not seg_text: continue
            sw = kwargs.get('stroke_width', 0)
            bbox = draw.textbbox((0, 0), seg_text, font=seg_font, stroke_width=sw)
            advance = draw.textlength(seg_text, font=seg_font)
            line_w += max(advance, bbox[2])
            
        max_w = max(max_w, line_w)
    
    total_h = len(lines) * lh + (len(lines) - 1) * 10
    return int(max_w), int(total_h)
