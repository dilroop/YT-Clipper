"""
workflow2.py  —  9:16 story-card video generator
=================================================

Stacks the following components vertically on a 1080×1920 (9:16) canvas:

    ┌─────────────────────┐
    │     Header Image     │  ← --header-image
    ├─────────────────────┤  ← --padding gap
    │     Story Text       │  ← --story-text
    ├─────────────────────┤  ← --padding gap
    │  16:9 Main Video     │  ← --video
    ├─────────────────────┤  ← --padding gap
    │    Suffix Text 1     │  ← --suffix-text1
    ├─────────────────────┤  ← --padding gap
    │    Suffix Text 2     │  ← --suffix-text2
    └─────────────────────┘

Usage (CLI):
    python workflow2.py \\
        --video main.mp4 \\
        --header-image header.png \\
        --story-text "This couple saw a UAP..." \\
        --suffix-text1 "Part 1 of 3" \\
        --suffix-text2 "Follow for more" \\
        [--top-margin 60] \\
        [--padding 40] \\
        [--bg-color "#000000"] \\
        [--font Arial] \\
        [--story-size 52] [--story-color "#FFFFFF"] \\
        [--suffix1-size 38] [--suffix1-color "#AAAAAA"] \\
        [--suffix2-size 44] [--suffix2-color "#22DD66"] \\
        [--header-height 160] \\
        [--output out.mp4] \\
        [--fps 30]

Run with no arguments for interactive mode.

Requirements:
    moviepy, Pillow, numpy
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shlex
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ColorClip, CompositeVideoClip, ImageClip, VideoFileClip

# ─── Canvas constants ─────────────────────────────────────────────────────────
OUTPUT_WIDTH  = 1080
OUTPUT_HEIGHT = 1920
SIDE_PADDING  = 48          # horizontal margin left / right for text blocks
VIDEO_EXTS    = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

import unicodedata

# --- Global Constants & Package Setup -----------------------------------------
try:
    from backend.core.constants import BASE_DIR, FONTS_DIR
    from backend.videoprocessor.font_utils import (
        get_font, get_emoji_font, draw_text_with_fallback, is_char_emoji
    )
except (ImportError, ModuleNotFoundError):
    # Fallback for standalone script execution
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(BASE_DIR))
    from backend.core.constants import BASE_DIR, FONTS_DIR
    from backend.videoprocessor.font_utils import (
        get_font, get_emoji_font, draw_text_with_fallback, is_char_emoji
    )

# Sibling imports depend on being in the same package context or directory in sys.path
from video_cropper import VideoCropper
import tempfile
import re


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """Convert #RRGGBB hex to (R, G, B)."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 6:
        r, g, b = int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
        return (r, g, b)
    return (255, 255, 255)


# ─────────────────────────────────────────────────────────────────────────────
# Text utilities
# ─────────────────────────────────────────────────────────────────────────────

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, emoji_font: ImageFont.FreeTypeFont | None = None) -> str:
    """
    Word-wrap *text* so that no rendered line exceeds *max_width* pixels.
    Uses fallback emoji measurement if provided.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    result_lines: list[str] = []
    
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)

def render_text_block(
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    max_width: int,
    align: str = "center",
) -> np.ndarray:
    """
    Render wrapped, centred text onto a transparent RGBA canvas.
    Returns a uint8 NumPy RGBA array exactly sized to the text content.
    """
    emoji_font = get_emoji_font(font.size)
    wrapped = wrap_text(text, font, max_width, emoji_font=emoji_font)
    
    # Calculate bounding box for the whole block line-by-line using fallback measurement
    lines = wrapped.split("\n")
    lh = int(font.size * 1.2)
    line_widths = []
    
    dummy = Image.new("RGBA", (1, 1))
    draw_m = ImageDraw.Draw(dummy)
    
    def _measure_line(line: str) -> int:
        lw = 0
        for char in line:
            f = emoji_font if is_char_emoji(char) and emoji_font else font
            bbox = draw_m.textbbox((0, 0), char, font=f)
            lw += int(bbox[2] - bbox[0])
            if lw == 0 and is_char_emoji(char):
                lw += int(f.size)
        return lw

    line_widths = [_measure_line(l) for l in lines]
    img_w = max(line_widths) if line_widths else 1
    img_h = len(lines) * lh
    
    v_pad = int(font.size * 0.15)
    img_h += v_pad * 2

    img = Image.new("RGBA", (int(img_w), int(img_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for i, line in enumerate(lines):
        lx = 0
        if align == "center":
            lx = (img_w - line_widths[i]) // 2
        elif align == "right":
            lx = img_w - line_widths[i]
            
        draw_text_with_fallback(draw, (lx, i * lh + v_pad), line, font, (color[0], color[1], color[2], 255), emoji_font=emoji_font)
        
    return np.array(img)


# ─────────────────────────────────────────────────────────────────────────────
# Highlighted-text renderer  (words in [brackets] get a different color)
# ─────────────────────────────────────────────────────────────────────────────

_BRACKET_RE = re.compile(r'\[([^\]]+)\]')


def _parse_segments(text: str) -> list[tuple[str, bool, bool]]:
    """Split text into (segment, is_highlighted, no_leading_space) triples.

    The ``no_leading_space`` flag is ``True`` for punctuation that immediately
    trails a closing bracket (e.g. the "." in "[word].") so the renderer does
    *not* insert a word-gap space before it.
    """
    _SEGMENT_RE = re.compile(
        r'\[([^\]]*)\]([^\s\[]*)'
        r'|([^\[]+)'
    )
    result: list[tuple[str, bool, bool]] = []
    for m in _SEGMENT_RE.finditer(text):
        if m.group(1) is not None:
            hl_text = m.group(1)
            suffix = m.group(2)  # e.g. "." "," "!" that immediately follow ]
            if hl_text:
                result.append((hl_text, True, False))
            if suffix:
                result.append((suffix, False, True))  # glued punctuation
        else:
            result.append((m.group(3), False, False))
    return result


def render_text_block_highlighted(
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    highlight_color: tuple[int, int, int],
    max_width: int,
    align: str = "center",
    line_spacing: int = 10,
) -> np.ndarray:
    """
    Like render_text_block, but words wrapped in [square brackets] are drawn
    in *highlight_color* while the rest use *color*.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")

    # Flatten segments into token list: (word, is_highlighted, no_leading_space)
    # | ('__NL__', False, False)
    segments = _parse_segments(text)
    tokens: list[tuple[str, bool, bool]] = []
    for seg, is_hl, no_space in segments:
        parts = seg.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                tokens.append(("__NL__", False, False))
            if no_space:
                # Punctuation glued to previous token — emit as single no-space token
                if part.strip():
                    tokens.append((part.strip(), is_hl, True))
            else:
                for word in part.split():
                    tokens.append((word, is_hl, False))

    # Measure helpers
    dummy = Image.new("RGBA", (1, 1))
    draw_m = ImageDraw.Draw(dummy)
    emoji_font = get_emoji_font(font.size)

    def _w(s: str) -> int:
        # Sum character widths with fallback
        total = 0
        for char in s:
            use_font = font
            if is_char_emoji(char) and emoji_font:
                use_font = emoji_font
            try:
                bbox = draw_m.textbbox((0, 0), char, font=use_font)
                w = int(bbox[2] - bbox[0])
                if w == 0 and is_char_emoji(char):
                    w = int(use_font.size)
                total += w
            except Exception:
                tw, _ = draw_m.textsize(char, font=use_font) # type: ignore
                total += int(tw)
        return total

    def _lh() -> int:
        try:
            # Use 'Ag' to get a good span of ascenders and descenders
            bbox = draw_m.textbbox((0, 0), "Ag", font=font)
            return int(bbox[3] - bbox[1])
        except AttributeError:
            # Fallback for old Pillow
            w, h = draw_m.textsize("Ag", font=font)  # type: ignore
            return int(h)

    space_w = _w(" ")
    lh = _lh()

    # Word-wrap into lines: list[list[(word, is_hl, no_leading_space)]]
    lines: list[list[tuple[str, bool, bool]]] = []
    cur_line: list[tuple[str, bool, bool]] = []
    cur_w = 0
    for word, is_hl, no_space in tokens:
        if word == "__NL__":
            lines.append(cur_line)
            cur_line = []
            cur_w = 0
            continue
        ww = _w(word)
        if no_space:
            # Glue to current line without space
            cur_line.append((word, is_hl, True))
            cur_w += ww
        else:
            needed = (space_w + ww) if cur_line else ww
            if cur_line and cur_w + needed > max_width:
                lines.append(cur_line)
                cur_line = [(word, is_hl, False)]
                cur_w = ww
            else:
                cur_line.append((word, is_hl, False))
                cur_w += needed
    lines.append(cur_line)

    def _line_w(ln: list[tuple[str, bool, bool]]) -> int:
        total = 0
        for i, (wd, _, no_space) in enumerate(ln):
            if i and not no_space:
                total += space_w
            total += _w(wd)
        return total

    canvas_w = max((_line_w(ln) for ln in lines), default=10)
    canvas_h = len(lines) * lh + max(0, len(lines) - 1) * line_spacing
    
    # Add vertical padding to prevent descender clipping
    v_pad = int(lh * 0.2)
    canvas_h += v_pad * 2

    img = Image.new("RGBA", (max(1, canvas_w), max(1, canvas_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = color
    hr, hg, hb = highlight_color

    for li, ln in enumerate(lines):
        y = li * (lh + line_spacing) + v_pad
        lw = _line_w(ln)
        if align == "center":
            x = (canvas_w - lw) // 2
        elif align == "right":
            x = canvas_w - lw
        else:
            x = 0
        for i, (wd, is_hl, no_space) in enumerate(ln):
            if i and not no_space:
                x += space_w
            fill = (hr, hg, hb, 255) if is_hl else (r, g, b, 255)
            x = draw_text_with_fallback(draw, (x, y), wd, font, fill, emoji_font=emoji_font)

    return np.array(img)


# ─────────────────────────────────────────────────────────────────────────────
# Header image helper
# ─────────────────────────────────────────────────────────────────────────────

def load_header_image(path: str, target_width: int, max_height: int) -> np.ndarray:
    """
    Load an image, scale it to *target_width* while preserving aspect ratio
    (height capped at *max_height*), and return an RGBA NumPy array.
    """
    img = Image.open(path).convert("RGBA")
    orig_w, orig_h = img.size
    scale = target_width / orig_w
    new_h = int(orig_h * scale)
    if new_h > max_height:
        scale = max_height / orig_h
        new_w = int(orig_w * scale)
        img = img.resize((new_w, new_h if new_h <= max_height else max_height), Image.LANCZOS)
    else:
        img = img.resize((target_width, new_h), Image.LANCZOS)
    return np.array(img)


# ─────────────────────────────────────────────────────────────────────────────
# Video loader & sizer
# ─────────────────────────────────────────────────────────────────────────────

def load_and_fit_video(
    video_path: str,
    target_width: int,
    duration: float,
) -> tuple[VideoFileClip, int]:
    """
    Load a 16:9 video, scale to *target_width* wide, return (clip, rendered_height).
    The clip is truncated / held to *duration* seconds.
    """
    clip = VideoFileClip(video_path)
    ar = clip.w / clip.h
    target_height = int(target_width / ar)
    clip = clip.resized(width=target_width)
    clip = clip.with_duration(min(clip.duration, duration))
    return clip, target_height


# ─────────────────────────────────────────────────────────────────────────────
# Core compositor
# ─────────────────────────────────────────────────────────────────────────────

def build_story_video(
    video_path: str,
    header_image_path: str,
    story_text: str,
    suffix_text1: str,
    suffix_text2: str,
    output_path: str,
    # Layout
    top_margin: int = 60,
    padding: int = 40,
    header_max_height: int = 160,
    # Canvas
    bg_color: str = "#000000",
    # Font
    font_name: str | None = None,
    # Story text
    story_size: int = 52,
    story_color: str = "#FFFFFF",
    highlight_color: str = "#22DD66",
    # Suffix 1
    suffix1_size: int = 38,
    suffix1_color: str = "#AAAAAA",
    # Suffix 2
    suffix2_size: int = 44,
    suffix2_color: str = "#22DD66",
    # Export
    fps: int = 30,
    duration_override: float | None = None,
    # New Features
    auto_scale: bool = False,
    preview: bool = False,
) -> str:
    """
    Build the story-card video and write it to *output_path*.
    Returns *output_path* on success, raises on failure.
    """
    print(f"[INFO] Loading main video: {video_path}")
    probe = VideoFileClip(video_path)
    duration = duration_override or probe.duration
    probe.close()

    # ── Scaling ───────────────────────────────────────────────────────────────
    # If we are in preview mode, we only care about t=0, so duration is tiny
    if preview:
        duration = 0.5

    print(f"[INFO] Output duration: {duration:.2f}s  |  Canvas: {OUTPUT_WIDTH}×{OUTPUT_HEIGHT}")

    # ── fonts ─────────────────────────────────────────────────────────────────
    story_font   = get_font(font_name, story_size)
    suffix1_font = get_font(font_name, suffix1_size)
    suffix2_font = get_font(font_name, suffix2_size)

    # ── text widths available (inside side padding) ───────────────────────────
    text_max_w = OUTPUT_WIDTH - SIDE_PADDING * 2

    # ── pre-render all text blocks ────────────────────────────────────────────
    # Story text uses highlighted renderer (plain text falls back gracefully)
    story_arr   = render_text_block_highlighted(
        story_text, story_font,
        hex_to_rgb(story_color), hex_to_rgb(highlight_color),
        text_max_w
    )
    suffix1_arr = render_text_block(suffix_text1, suffix1_font, hex_to_rgb(suffix1_color), text_max_w)
    suffix2_arr = render_text_block(suffix_text2, suffix2_font, hex_to_rgb(suffix2_color), text_max_w)

    # ── header image ──────────────────────────────────────────────────────────
    header_arr  = load_header_image(header_image_path, OUTPUT_WIDTH, header_max_height)

    # ── main video clip ───────────────────────────────────────────────────────
    video_clip, video_h = load_and_fit_video(video_path, OUTPUT_WIDTH, duration)

    # ─────────────────────────────────────────────────────────────────────────
    # Layout pass:  calculate positions
    # ─────────────────────────────────────────────────────────────────────────
    def center_x(arr_width: int) -> int:
        return max(0, (OUTPUT_WIDTH - arr_width) // 2)

    # First pass: calculate "pure" content height (starting from 0)
    # We ignore top_margin for now to find the actual block height
    rel_y = 0
    rel_positions: list[tuple[str, int, int, int]] = [] # (name, x, y, h)

    # 1. Header
    h_arr_h, h_arr_w = header_arr.shape[:2]
    rel_positions.append(("header", center_x(h_arr_w), rel_y, h_arr_h))
    rel_y += h_arr_h + padding

    # 2. Story
    s_arr_h, s_arr_w = story_arr.shape[:2]
    rel_positions.append(("story", center_x(s_arr_w), rel_y, s_arr_h))
    rel_y += s_arr_h + padding

    # 3. Video
    rel_positions.append(("video", 0, rel_y, video_h))
    rel_y += video_h + padding

    # 4. Suffix 1
    sf1_arr_h, sf1_arr_w = suffix1_arr.shape[:2]
    rel_positions.append(("suffix1", center_x(sf1_arr_w), rel_y, sf1_arr_h))
    rel_y += sf1_arr_h + padding

    # 5. Suffix 2
    sf2_arr_h, sf2_arr_w = suffix2_arr.shape[:2]
    rel_positions.append(("suffix2", center_x(sf2_arr_w), rel_y, sf2_arr_h))
    rel_y += sf2_arr_h

    content_h = rel_y
    print(f"[INFO] Total pure content height: {content_h}px  (canvas: {OUTPUT_HEIGHT}px)")

    # ─────────────────────────────────────────────────────────────────────────
    # Auto-scaling & Centering logic
    # ─────────────────────────────────────────────────────────────────────────
    global_scale = 1.0
    start_y = top_margin

    if auto_scale:
        # Scale to fit if content is too tall
        if content_h > OUTPUT_HEIGHT:
            global_scale = OUTPUT_HEIGHT / content_h
            print(f"[INFO] Auto-scale (fit) enabled. Scale factor: {global_scale:.3f}")
        
        # Calculate start_y for vertical centering
        scaled_content_h = content_h * global_scale
        start_y = int((OUTPUT_HEIGHT - scaled_content_h) / 2)
        print(f"[INFO] Auto-scale (center) enabled. Vertical offset: {start_y}px")
    else:
        # If not auto-scaling, we still scale down ONLY if total height (inc margin) overflows
        total_h_with_margin = top_margin + content_h
        if total_h_with_margin > OUTPUT_HEIGHT:
            global_scale = (OUTPUT_HEIGHT - top_margin) / content_h
            print(f"[INFO] Overflow protection active. Scale factor: {global_scale:.3f}")

    # Final positions pass
    positions: list[tuple[str, int, int]] = []
    for name, rx, ry, rh in rel_positions:
        # If we have a global scale, we must also scale the relative Y and the center X
        scaled_y = start_y + int(ry * global_scale)
        scaled_x = rx # Usually already centered, but scaled images might need re-centering
        # (add_layer handles image-level scaling and x-centering)
        positions.append((name, scaled_x, scaled_y))

    total_h = start_y + int(content_h * global_scale)

    # ─────────────────────────────────────────────────────────────────────────
    # MoviePy pass: build layers
    # ─────────────────────────────────────────────────────────────────────────
    bg_rgb = hex_to_rgb(bg_color)
    
    # SAFETY: To prevent MoviePy broadcast errors on off-screen clips,
    # we create a composite that is at least as tall as the content, 
    # then crop it back to the final 1080x1920.
    composition_height = max(OUTPUT_HEIGHT, total_h + 100)
    canvas = ColorClip(size=(OUTPUT_WIDTH, composition_height), color=bg_rgb, duration=duration)

    layers: list = [canvas]

    def pos_of(name: str) -> tuple[int, int]:
        for n, x, y in positions:
            if n == name:
                return x, y
        raise KeyError(name)

    def add_layer(clip, name, arr_w, arr_h):
        cx, cy = pos_of(name)
        
        # Apply global scale if needed
        if global_scale < 1.0:
            clip = clip.resized(global_scale)
            arr_w = int(arr_w * global_scale)
            arr_h = int(arr_h * global_scale)
            cx = (OUTPUT_WIDTH - arr_w) // 2

        # Check if the clip is entirely off-screen to avoid MoviePy broadcast errors
        # (Though we fixed the crash with the taller canvas, this is still good for logging)
        if cy >= OUTPUT_HEIGHT:
            print(f"[WARNING] Skipping {name}: Position ({cx}, {cy}) is off-screen.")
        
        layers.append(clip.with_position((cx, cy)))
        print(f"[INFO] {name.capitalize():<12} → ({cx}, {cy})  {arr_w}×{arr_h}px")

    # Header
    h_arr_h, h_arr_w = header_arr.shape[:2]
    header_clip = ImageClip(header_arr).with_duration(duration)
    add_layer(header_clip, "header", h_arr_w, h_arr_h)

    # Story
    s_arr_h, s_arr_w = story_arr.shape[:2]
    story_clip = ImageClip(story_arr).with_duration(duration)
    add_layer(story_clip, "story", s_arr_w, s_arr_h)

    # Video
    # Capture audio reference BEFORE any further transformations
    raw_audio = video_clip.audio
    add_layer(video_clip, "video", OUTPUT_WIDTH, video_h)

    # Suffix 1
    sf1_arr_h, sf1_arr_w = suffix1_arr.shape[:2]
    suffix1_clip = ImageClip(suffix1_arr).with_duration(duration)
    add_layer(suffix1_clip, "suffix1", sf1_arr_w, sf1_arr_h)

    # Suffix 2
    sf2_arr_h, sf2_arr_w = suffix2_arr.shape[:2]
    suffix2_clip = ImageClip(suffix2_arr).with_duration(duration)
    add_layer(suffix2_clip, "suffix2", sf2_arr_w, sf2_arr_h)

    # ─────────────────────────────────────────────────────────────────────────
    # Composite & export
    # ─────────────────────────────────────────────────────────────────────────
    print("[INFO] Compositing final video...")
    
    final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, composition_height))
    final = final.with_duration(duration)

    # Crop to final 9:16 aspect ratio
    from moviepy.video.fx import Crop
    final = Crop(x1=0, y1=0, x2=OUTPUT_WIDTH, y2=OUTPUT_HEIGHT).apply(final)

    if preview:
        print(f"[INFO] Writing preview frame → {output_path}")
        final.save_frame(output_path, t=0)
        print(f"\n[SUCCESS] Preview captured: {output_path}")
        return output_path

    # Attach audio from the main video (reader is still open — do NOT close before write)
    if raw_audio is not None:
        final = final.with_audio(raw_audio.with_duration(duration))

    print(f"[INFO] Writing → {output_path}")
    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
    )
    print(f"\n[SUCCESS] Done! Output saved to: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a 9:16 story-card video stacking image, text, and video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Required inputs
    p.add_argument("--video",         required=True, metavar="FILE",   help="Main 16:9 video.")
    p.add_argument("--header-image",  required=True, metavar="FILE",   help="Header/profile image.")
    p.add_argument("--story-text",    required=True,                   help="Main story paragraph.")
    p.add_argument("--suffix-text1",  required=True,                   help="First line of suffix text.")
    p.add_argument("--suffix-text2",  required=True,                   help="Second line of suffix text (highlighted).")

    # Output
    p.add_argument("--output",        default=None, metavar="FILE",    help="Output path (default: <video>_story.mp4).")
    p.add_argument("--fps",           type=int,   default=30,          help="Output FPS (default: 30).")
    p.add_argument("--duration",      type=float, default=None,        help="Override output duration in seconds.")

    # Layout
    p.add_argument("--top-margin",    type=int,   default=60,          help="Pixels from top before first element (default: 60).")
    p.add_argument("--padding",       type=int,   default=40,          help="Vertical gap between elements in pixels (default: 40).")
    p.add_argument("--header-height", type=int,   default=160,         help="Max header image height in pixels (default: 160).")

    # Canvas
    p.add_argument("--bg-color",      default="#000000",               help="Canvas background hex color (default: #000000).")

    # Font
    p.add_argument("--font",          default=None,                    help="Font name or .ttf path (default: system Arial).")

    # Story text style
    p.add_argument("--story-size",       type=int,   default=52,       help="Story font size (default: 52).")
    p.add_argument("--story-color",      default="#FFFFFF",            help="Story text hex color (default: #FFFFFF).")
    p.add_argument("--highlight-color",  default="#22DD66",            help="Color for [bracketed] words in story (default: #22DD66).")

    # Suffix 1 style
    p.add_argument("--suffix1-size",  type=int,   default=38,          help="Suffix-1 font size (default: 38).")
    p.add_argument("--suffix1-color", default="#AAAAAA",               help="Suffix-1 hex color (default: #AAAAAA).")

    # Suffix 2 style
    p.add_argument("--suffix2-size",  type=int,   default=44,          help="Suffix-2 font size (default: 44).")
    p.add_argument("--suffix2-color", default="#22DD66",               help="Suffix-2 hex color (default: #22DD66 green).")

    p.add_argument("--detection-mode", choices=["face", "torso"], default="face",
                        help="Tracking mode for the 9:8 main video crop (default: 'face').")
    p.add_argument("--crop-mode", choices=["9:8", "original"], default="9:8",
                        help="Crop the main video to 9:8 aspect ratio or keep original (default: '9:8').")

    p.add_argument("--preview", action="store_true", help="Generate a single frame PNG preview at t=0.")
    p.add_argument("--auto-scale", action="store_true", help="Automatically scale content to fit within 1920px height.")

    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Interactive mode helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_path(prompt: str, required: bool = True) -> str:
    while True:
        raw = input(prompt).strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        elif raw.startswith("'") and raw.endswith("'"):
            raw = raw[1:-1]
        try:
            tokens = shlex.split(raw)
            if len(tokens) == 1:
                raw = os.path.expanduser(tokens[0])
        except ValueError:
            raw = os.path.expanduser(raw)
        if (not required) or os.path.exists(raw):
            return raw
        print(f"  File not found: '{raw}'.  Please try again.")


def _prompt_str(prompt: str, default: str = "") -> str:
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else default


def _prompt_int(prompt: str, default: int) -> int:
    while True:
        val = input(f"{prompt} [{default}]: ").strip()
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            print("  Please enter a whole number.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) == 1:
        # ── Interactive dialogue mode ─────────────────────────────────────────
        print("\n=== workflow2.py — interactive mode ===\n")

        video         = _prompt_path("Path to main 16:9 video: ")
        header_image  = _prompt_path("Path to header/profile image: ")
        story_text    = input("Story text (use \\n for line breaks): ").strip()
        suffix_text1  = input("Suffix text 1 (e.g. 'Wait till the end...'): ").strip()
        suffix_text2  = input("Suffix text 2 (e.g. 'Part 1'): ").strip()

        print("\n── Layout ──────────────────────────────")
        top_margin    = _prompt_int("Top margin (px)", 60)
        padding       = _prompt_int("Padding between elements (px)", 40)
        header_height = _prompt_int("Max header image height (px)", 160)
        bg_color      = _prompt_str("Canvas background color (#hex)", "#000000")

        print("\n── Text styling (press Enter to keep defaults) ──")
        font            = _prompt_str("Font name or path", "Arial")
        story_size      = _prompt_int("Story font size", 52)
        story_color     = _prompt_str("Story text color (#hex)", "#FFFFFF")
        highlight_color = _prompt_str("Highlight color for [bracketed] words (#hex)", "#22DD66")
        suffix1_size    = _prompt_int("Suffix-1 font size", 38)
        suffix1_color   = _prompt_str("Suffix-1 color (#hex)", "#AAAAAA")
        suffix2_size    = _prompt_int("Suffix-2 font size", 44)
        suffix2_color   = _prompt_str("Suffix-2 color (#hex)", "#22DD66")
        detection_mode  = _prompt_str("Detection mode [face/torso]", "face")
        preview         = input("Preview mode? [y/N]: ").lower().startswith("y")
        auto_scale      = input("Auto-scale to fit? [y/N]: ").lower().startswith("y")

        print("\n── Output ──────────────────────────────")
        default_out   = str(Path(video).with_suffix("")) + "_story.mp4"
        output        = _prompt_str("Output path", default_out)
        fps           = _prompt_int("FPS", 30)

    else:
        # ── CLI mode ──────────────────────────────────────────────────────────
        args          = parse_args()
        video         = args.video
        header_image  = args.header_image
        story_text    = args.story_text
        suffix_text1  = args.suffix_text1
        suffix_text2  = args.suffix_text2
        output        = args.output or (str(Path(video).with_suffix("")) + "_story.mp4")
        fps           = args.fps
        top_margin    = args.top_margin
        padding       = args.padding
        header_height = args.header_height
        bg_color      = args.bg_color
        font            = args.font
        story_size      = args.story_size
        story_color     = args.story_color
        highlight_color = args.highlight_color
        suffix1_size    = args.suffix1_size
        suffix1_color   = args.suffix1_color
        suffix2_size    = args.suffix2_size
        suffix2_color   = args.suffix2_color
        detection_mode  = args.detection_mode
        crop_mode       = args.crop_mode
        preview         = args.preview
        auto_scale      = args.auto_scale

    # ── Validate ──────────────────────────────────────────────────────────────
    for label, path in [("--video", video), ("--header-image", header_image)]:
        if not os.path.exists(path):
            print(f"[ERROR] {label} file not found: {path}")
            sys.exit(1)
    if Path(video).suffix.lower() not in VIDEO_EXTS:
        print(f"[ERROR] --video must be a video file, got: {video}")
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp_dir:
        
        # Decide if we need to crop the main video
        if crop_mode == "9:8":
            print(f"[INFO] Cropping main video with head tracking (9:8 ratio)...")
            cropper = VideoCropper()
            tmp_cropped_path = os.path.join(tmp_dir, "cropped_main_9x8.mp4")
            crop_res = cropper.crop_to_9x8(video, tmp_cropped_path, mode=detection_mode, preview=preview)
            
            if not crop_res['success']:
                print(f"[ERROR] Head tracking crop failed: {crop_res.get('error')}")
                sys.exit(1)
                
            final_video_input = crop_res['output_path']
        else:
            print(f"[INFO] Using original video aspect ratio (--crop-mode {crop_mode})")
            final_video_input = video

        build_story_video(
            video_path        = final_video_input,
            header_image_path = header_image,
            story_text        = story_text,
            suffix_text1      = suffix_text1,
            suffix_text2      = suffix_text2,
            output_path       = output,
            top_margin        = top_margin,
            padding           = padding,
            header_max_height = header_height,
            bg_color          = bg_color,
            font_name         = font if font and font != "Arial" else None,
            story_size        = story_size,
            story_color       = story_color,
            highlight_color   = highlight_color,
            suffix1_size      = suffix1_size,
            suffix1_color     = suffix1_color,
            suffix2_size      = suffix2_size,
            suffix2_color     = suffix2_color,
            fps               = fps,
            auto_scale        = auto_scale,
            preview           = preview,
        )


if __name__ == "__main__":
    main()
