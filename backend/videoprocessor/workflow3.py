"""
workflow3.py — Silence Removal Workflow
=======================================

Automatically detects silent sections in a video and removes them, 
shortening pauses to a user-defined minimum duration.

Usage (CLI):
    python workflow3.py --input video.mp4 --threshold 500 --keep 100 --output out.mp4

Interactive Mode:
    python workflow3.py

Requirements:
    moviepy, ffmpeg-python or subprocess for ffmpeg access
"""

import argparse
import os
import re
import sys
import subprocess
import numpy as np
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, concatenate_videoclips, ImageClip, CompositeVideoClip

# --- Global Constants & Package Setup -----------------------------------------
try:
    from backend.core.constants import BASE_DIR
except (ImportError, ModuleNotFoundError):
    # Fallback for standalone script execution
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(BASE_DIR))
    from backend.core.constants import BASE_DIR

# ─── Emoji Support ────────────────────────────────────────────────────────────
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
    """Check if a character is likely an emoji or special symbol."""
    if EMOJI_RE.search(char):
        return True
    cat = unicodedata.category(char)
    if cat.startswith('S'):
         return True
    if '\U0001F000' <= char <= '\U0001FFFF':
        return True
    return False

_EMOJI_FONT_CACHE = {}
# Known bitmap sizes supported by Apple Color Emoji on macOS
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

def _draw_text_with_fallback(draw, pos, text, font, fill, emoji_font=None, **kwargs):
    """Draw text character by character, switching to emoji_font if needed."""
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
            try:
                w, _ = draw.textsize(char, font=use_font) # type: ignore
            except:
                w = use_font.size
        x += w
    return x

def _measure_text_with_fallback(text: str, font, emoji_font=None, **kwargs) -> tuple[int, int]:
    """Measure text width and height with emoji fallback."""
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    lines = text.split('\n')
    max_w = 0
    try:
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        lh = int(bbox[3] - bbox[1])
    except:
        w, h = draw.textsize("Ag", font=font) # type: ignore
        lh = int(h)
    
    for ln in lines:
        cur_x = 0
        for char in ln:
            use_font = font
            if is_char_emoji(char) and emoji_font: use_font = emoji_font
            try:
                bbox = draw.textbbox((cur_x, 0), char, font=use_font)
                w = bbox[2] - bbox[0]
                if w == 0 and is_char_emoji(char): w = use_font.size
            except:
                try: w, _ = draw.textsize(char, font=use_font) # type: ignore
                except: w = use_font.size
            cur_x += w
        max_w = max(max_w, cur_x)
    total_h = len(lines) * lh + (len(lines) - 1) * 10
    return int(max_w), int(total_h)

def render_text(text: str, font: ImageFont.FreeTypeFont, text_color=(255, 255, 255, 255), padding=20) -> np.ndarray:
    """Render text with emoji support for workflow3."""
    text = text.replace('\\n', '\n')
    emoji_font = get_emoji_font(font.size)
    text_w, text_h = _measure_text_with_fallback(text, font, emoji_font=emoji_font)
    
    canvas_w = text_w + padding * 2
    canvas_h = text_h + padding * 2
    
    img = Image.new("RGBA", (int(canvas_w), int(canvas_h)), (0, 0, 0, 160))
    draw = ImageDraw.Draw(img)
    
    lines = text.split('\n')
    try:
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        lh = int(bbox[3] - bbox[1])
    except:
        _, h = draw.textsize("Ag", font=font) # type: ignore
        lh = int(h)
        
    for i, ln in enumerate(lines):
        lw, _ = _measure_text_with_fallback(ln, font, emoji_font=emoji_font)
        x = padding + (text_w - lw) // 2
        y = padding + i * (lh + 10)
        _draw_text_with_fallback(draw, (x, y), ln, font, text_color, emoji_font=emoji_font)
        
    return np.array(img)

def get_silence_intervals(input_path: str, threshold_db: float = -30, min_silence_len_s: float = 0.5):
    """
    Run ffmpeg silencedetect filter and return a list of (start, end) tuples for silent intervals.
    """
    print(f"[INFO] Detecting silences (threshold={threshold_db}dB, min_len={min_silence_len_s}s)...")
    
    # ffmpeg -i input -af silencedetect=n=-30dB:d=0.5 -f null -
    cmd = [
        "ffmpeg", "-i", input_path,
        "-af", f"silencedetect=n={threshold_db}dB:d={min_silence_len_s}",
        "-f", "null", "-"
    ]
    
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    _, stderr = process.communicate()
    
    silences = []
    start_time = None
    
    # Regex to match: [silencedetect @ 0x...] silence_start: 1.234
    # and: [silencedetect @ 0x...] silence_end: 4.567 | silence_duration: 3.333
    start_re = re.compile(r"silence_start:\s+(\d+(\.\d+)?)")
    end_re = re.compile(r"silence_end:\s+(\d+(\.\d+)?)\s+\|\s+silence_duration:\s+(\d+(\.\d+)?)")
    
    for line in stderr.splitlines():
        if "silence_start:" in line:
            match = start_re.search(line)
            if match:
                start_time = float(match.group(1))
        elif "silence_end:" in line:
            match = end_re.search(line)
            if match and start_time is not None:
                end_time = float(match.group(1))
                silences.append((start_time, end_time))
                start_time = None
                
    return silences

def remove_silences(input_path: str, output_path: str, threshold_ms: int, keep_ms: int, text: str = None, font_size: int = 70):
    """
    Remove silent sections and save to output_path.
    """
    threshold_s = threshold_ms / 1000.0
    keep_s = keep_ms / 1000.0
    
    silences = get_silence_intervals(input_path, min_silence_len_s=threshold_s)
    
    if not silences:
        print("[INFO] No silences found matching the threshold. Copying original file...")
        import shutil
        shutil.copy2(input_path, output_path)
        return
    
    print(f"[INFO] Found {len(silences)} silent intervals.")
    
    clip = VideoFileClip(input_path)
    total_duration = clip.duration
    
    # Calculate intervals to KEEP
    # We want to keep audio segments, including 'keep_s/2' buffer from the silence at each end
    keep_segments = []
    last_end = 0.0
    
    for start, end in silences:
        # Segment from last silence end to this silence start
        # We add half the 'keep' buffer to each side
        seg_start = max(0.0, last_end - keep_s / 2.0)
        seg_end = min(total_duration, start + keep_s / 2.0)
        
        if seg_end > seg_start:
            keep_segments.append((seg_start, seg_end))
        
        last_end = end
        
    # Last segment after final silence
    # We add a tiny buffer (0.1s) to the end to ensure MoviePy captures the final frames
    seg_start = max(0.0, last_end - keep_s / 2.0)
    seg_end = total_duration 
    if seg_end > seg_start:
        keep_segments.append((seg_start, seg_end))
        
    print(f"[INFO] Concatenating {len(keep_segments)} audio segments...")
    
    subclips = [clip.subclipped(s, e) for s, e in keep_segments]
    final_clip = concatenate_videoclips(subclips)
    
    if text:
        from moviepy import vfx
        print(f"[INFO] Adding text overlay: '{text}'")
        try:
            # Simple Arial fallback for Mac
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
            if not os.path.exists(font_path): font_path = None
            font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            
        text_arr = render_text(text, font)
        text_clip = ImageClip(text_arr).with_duration(final_clip.duration)
        
        # Position at bottom center
        text_pos = (
            (final_clip.w - text_arr.shape[1]) // 2,
            int(final_clip.h * 0.8)
        )
        text_clip = text_clip.with_position(text_pos)
        final_clip = CompositeVideoClip([final_clip, text_clip])

    print(f"[INFO] Writing output ({final_clip.duration:.2f}s) → {output_path}")
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        fps=clip.fps
    )
    
    clip.close()
    final_clip.close()

def main():
    parser = argparse.ArgumentParser(description="Workflow 3: Skip Silences")
    parser.add_argument("--input", help="Path to input video")
    parser.add_argument("--output", help="Path to output video")
    parser.add_argument("--threshold", type=int, default=500, help="Min silence length in ms (default: 500)")
    parser.add_argument("--keep", type=int, default=100, help="Silence to keep after removal in ms (default: 100)")
    parser.add_argument("--text", help="Optional text overlay for the final video")
    parser.add_argument("--font-size", type=int, default=70, help="Font size for text overlay")
    
    args = parser.parse_args()
    
    if not args.input:
        print("--- Interactive Mode ---")
        args.input = input("Enter path to input video: ").strip()
        if args.input.startswith('"') and args.input.endswith('"'): args.input = args.input[1:-1]
        
        try:
            args.threshold = int(input("Min silence length (threshold) in ms [500]: ") or 500)
            args.keep = int(input("Silence to keep in ms [100]: ") or 100)
        except ValueError:
            print("[ERROR] Invalid input. Using defaults.")
            args.threshold = 500
            args.keep = 100
            
        if not args.output:
            p = Path(args.input)
            args.output = str(p.parent / f"{p.stem}_no_silence{p.suffix}")
            print(f"Output will be saved to: {args.output}")

    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)
        
    if not args.output:
        p = Path(args.input)
        args.output = str(p.parent / f"{p.stem}_no_silence{p.suffix}")

    try:
        remove_silences(args.input, args.output, args.threshold, args.keep, text=args.text, font_size=args.font_size)
        print(f"\n[SUCCESS] Done! Output saved to: {args.output}")
    except Exception as e:
        print(f"\n[ERROR] Workflow failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
