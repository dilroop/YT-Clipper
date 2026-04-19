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

from video_cropper import VideoCropper
import tempfile


# ─────────────────────────────────────────────────────────────────────────────
# Font helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont:
    """Return a Pillow font, trying the user path then common system paths."""
    font_map = {
        "Arial":           "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Helvetica":       "/System/Library/Fonts/Helvetica.ttc",
        "Times New Roman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "Impact":          "/System/Library/Fonts/Supplemental/Impact.ttf",
        "Courier New":     "/System/Library/Fonts/Supplemental/Courier New.ttf",
    }
    candidates = [
        font_path,
        font_map.get(font_path or "", None),
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    print("[WARNING] Could not load a TrueType font — falling back to default.")
    return ImageFont.load_default()


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

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """
    Word-wrap *text* so that no rendered line exceeds *max_width* pixels.
    Existing newlines in the source text are preserved.
    Returns the wrapped string with \\n separators.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    result_lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            result_lines.append("")
            continue
        current_line: list[str] = []
        for word in words:
            test_line = " ".join(current_line + [word])
            dummy = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy)
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
            except AttributeError:
                w, _ = draw.textsize(test_line, font=font)  # type: ignore[attr-defined]
            if w <= max_width or not current_line:
                current_line.append(word)
            else:
                result_lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            result_lines.append(" ".join(current_line))
    return "\n".join(result_lines)


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
    wrapped = wrap_text(text, font, max_width)
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    try:
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align=align)
    except AttributeError:
        w, h = draw.multiline_textsize(wrapped, font=font)  # type: ignore
        bbox = (0, 0, w, h)

    tw = int(bbox[2] - bbox[0])
    th = int(bbox[3] - bbox[1])
    off_x = int(bbox[0])
    off_y = int(bbox[1])
    img_w = max(1, tw)
    img_h = max(1, th)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = color
    try:
        draw.multiline_text(
            (-off_x, -off_y),
            wrapped,
            font=font,
            fill=(r, g, b, 255),
            align=align,
        )
    except TypeError:
        draw.multiline_text(
            (-off_x, -off_y),
            wrapped,
            font=font,
            fill=(r, g, b, 255),
        )
    return np.array(img)


# ─────────────────────────────────────────────────────────────────────────────
# Highlighted-text renderer  (words in [brackets] get a different color)
# ─────────────────────────────────────────────────────────────────────────────

_BRACKET_RE = re.compile(r'\[([^\]]+)\]')


def _parse_segments(text: str) -> list[tuple[str, bool]]:
    """Split text into (segment, is_highlighted) pairs on [bracket] markers."""
    result: list[tuple[str, bool]] = []
    last = 0
    for m in _BRACKET_RE.finditer(text):
        if m.start() > last:
            result.append((text[last:m.start()], False))
        result.append((m.group(1), True))
        last = m.end()
    if last < len(text):
        result.append((text[last:], False))
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

    # Flatten segments into token list: (word, is_highlighted)  |  ('__NL__', False)
    segments = _parse_segments(text)
    tokens: list[tuple[str, bool]] = []
    for seg, is_hl in segments:
        parts = seg.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                tokens.append(("__NL__", False))
            for word in part.split():
                tokens.append((word, is_hl))

    # Measure helpers
    dummy = Image.new("RGBA", (1, 1))
    draw_m = ImageDraw.Draw(dummy)

    def _w(s: str) -> int:
        try:
            bbox = draw_m.textbbox((0, 0), s, font=font)
            return int(bbox[2] - bbox[0])
        except AttributeError:
            w, _ = draw_m.textsize(s, font=font)  # type: ignore
            return int(w)

    def _lh() -> int:
        try:
            bbox = draw_m.textbbox((0, 0), "Ag", font=font)
            return int(bbox[3] - bbox[1])
        except AttributeError:
            _, h = draw_m.textsize("Ag", font=font)  # type: ignore
            return int(h)

    space_w = _w(" ")
    lh = _lh()

    # Word-wrap into lines: list[list[(word, is_hl)]]
    lines: list[list[tuple[str, bool]]] = []
    cur_line: list[tuple[str, bool]] = []
    cur_w = 0
    for word, is_hl in tokens:
        if word == "__NL__":
            lines.append(cur_line)
            cur_line = []
            cur_w = 0
            continue
        ww = _w(word)
        needed = (space_w + ww) if cur_line else ww
        if cur_line and cur_w + needed > max_width:
            lines.append(cur_line)
            cur_line = [(word, is_hl)]
            cur_w = ww
        else:
            cur_line.append((word, is_hl))
            cur_w += needed
    lines.append(cur_line)

    def _line_w(ln: list[tuple[str, bool]]) -> int:
        total = 0
        for i, (wd, _) in enumerate(ln):
            if i:
                total += space_w
            total += _w(wd)
        return total

    canvas_w = max((_line_w(ln) for ln in lines), default=10)
    canvas_h = len(lines) * lh + max(0, len(lines) - 1) * line_spacing

    img = Image.new("RGBA", (max(1, canvas_w), max(1, canvas_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = color
    hr, hg, hb = highlight_color

    for li, ln in enumerate(lines):
        y = li * (lh + line_spacing)
        lw = _line_w(ln)
        if align == "center":
            x = (canvas_w - lw) // 2
        elif align == "right":
            x = canvas_w - lw
        else:
            x = 0
        for i, (wd, is_hl) in enumerate(ln):
            if i:
                x += space_w
            fill = (hr, hg, hb, 255) if is_hl else (r, g, b, 255)
            draw.text((x, y), wd, font=font, fill=fill)
            x += _w(wd)

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
) -> str:
    """
    Build the story-card video and write it to *output_path*.
    Returns *output_path* on success, raises on failure.
    """
    print(f"[INFO] Loading main video: {video_path}")
    probe = VideoFileClip(video_path)
    duration = duration_override or probe.duration
    probe.close()
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
    # Layout pass:  calculate Y positions for every element
    # ─────────────────────────────────────────────────────────────────────────
    def center_x(arr_width: int) -> int:
        return max(0, (OUTPUT_WIDTH - arr_width) // 2)

    current_y = top_margin
    positions: list[tuple[str, int, int]] = []  # (name, x, y)

    # 1. Header image
    h_arr_h, h_arr_w = header_arr.shape[:2]
    positions.append(("header", center_x(h_arr_w), current_y))
    current_y += h_arr_h + padding

    # 2. Story text
    s_arr_h, s_arr_w = story_arr.shape[:2]
    positions.append(("story", center_x(s_arr_w), current_y))
    current_y += s_arr_h + padding

    # 3. Video
    positions.append(("video", 0, current_y))
    current_y += video_h + padding

    # 4. Suffix text 1
    sf1_arr_h, sf1_arr_w = suffix1_arr.shape[:2]
    positions.append(("suffix1", center_x(sf1_arr_w), current_y))
    current_y += sf1_arr_h + padding

    # 5. Suffix text 2
    sf2_arr_h, sf2_arr_w = suffix2_arr.shape[:2]
    positions.append(("suffix2", center_x(sf2_arr_w), current_y))
    current_y += sf2_arr_h

    total_h = current_y
    print(f"[INFO] Total stacked content height: {total_h}px  (canvas: {OUTPUT_HEIGHT}px)")
    if total_h > OUTPUT_HEIGHT:
        print(f"[WARNING] Content ({total_h}px) exceeds canvas height ({OUTPUT_HEIGHT}px). "
              "Consider reducing padding, font size, or header height.")

    # ─────────────────────────────────────────────────────────────────────────
    # MoviePy pass: build layers
    # ─────────────────────────────────────────────────────────────────────────
    bg_rgb = hex_to_rgb(bg_color)
    canvas = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=bg_rgb, duration=duration)

    layers: list = [canvas]

    def pos_of(name: str) -> tuple[int, int]:
        for n, x, y in positions:
            if n == name:
                return x, y
        raise KeyError(name)

    # Header
    hx, hy = pos_of("header")
    header_clip = ImageClip(header_arr).with_duration(duration).with_position((hx, hy))
    layers.append(header_clip)
    print(f"[INFO] Header image  → ({hx}, {hy})  {h_arr_w}×{h_arr_h}px")

    # Story
    sx, sy = pos_of("story")
    story_clip = ImageClip(story_arr).with_duration(duration).with_position((sx, sy))
    layers.append(story_clip)
    print(f"[INFO] Story text    → ({sx}, {sy})  {s_arr_w}×{s_arr_h}px")

    # Video
    vx, vy = pos_of("video")
    # Capture audio reference BEFORE any further transformations
    raw_audio = video_clip.audio
    video_clip = video_clip.with_position((vx, vy))
    layers.append(video_clip)
    print(f"[INFO] Main video    → ({vx}, {vy})  {OUTPUT_WIDTH}×{video_h}px")

    # Suffix 1
    sf1x, sf1y = pos_of("suffix1")
    suffix1_clip = ImageClip(suffix1_arr).with_duration(duration).with_position((sf1x, sf1y))
    layers.append(suffix1_clip)
    print(f"[INFO] Suffix text1  → ({sf1x}, {sf1y})  {sf1_arr_w}×{sf1_arr_h}px")

    # Suffix 2
    sf2x, sf2y = pos_of("suffix2")
    suffix2_clip = ImageClip(suffix2_arr).with_duration(duration).with_position((sf2x, sf2y))
    layers.append(suffix2_clip)
    print(f"[INFO] Suffix text2  → ({sf2x}, {sf2y})  {sf2_arr_w}×{sf2_arr_h}px")

    # ─────────────────────────────────────────────────────────────────────────
    # Composite & export
    # ─────────────────────────────────────────────────────────────────────────
    print("[INFO] Compositing final video...")
    final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT))
    final = final.with_duration(duration)

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
        suffix_text1  = input("Suffix text 1 (e.g. 'Sorry story too long...'): ").strip()
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
        print(f"[INFO] Cropping main video with head tracking (9:8 ratio)...")
        cropper = VideoCropper()
        tmp_cropped_path = os.path.join(tmp_dir, "cropped_main_9x8.mp4")
        crop_res = cropper.crop_to_9x8(video, tmp_cropped_path, mode=detection_mode)
        
        if not crop_res['success']:
            print(f"[ERROR] Head tracking crop failed: {crop_res.get('error')}")
            sys.exit(1)
            
        final_video_input = crop_res['output_path']

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
        )


if __name__ == "__main__":
    main()
