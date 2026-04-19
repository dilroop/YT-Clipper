"""
workflow.py  —  9:16 stacked video generator
============================================

Usage:
    python workflow.py --main VIDEO --second PHOTO_OR_VIDEO --text "Your Text"
                       [--circle VIDEO]
                       [--main-position top|bottom]   # or prompted interactively
                       [--output out.mp4]
                       [--font /path/to/font.ttf]
                       [--font-size 70]
                       [--circle-size 300]
                       [--watermark-text "@MrSinghExperience"]
                       [--watermark-size 45]
                       [--watermark-alpha 0.6]
                       [--duration SECONDS]

Requirements (install via requirements.txt):
    moviepy, Pillow, numpy
"""

import argparse
import os
import sys
import tempfile
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip
from video_cropper import VideoCropper

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
BOX_HEIGHT = OUTPUT_HEIGHT // 2  # 960  — each half of the 9:16 canvas

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


# ──────────────────────────────────────────────────────────────────────────────
# Font helper
# ──────────────────────────────────────────────────────────────────────────────
def get_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont:
    """Return a Pillow font, trying the user-supplied path then common system paths."""
    
    # Map common web fonts to Mac OS safe equivalents
    font_map = {
        "Arial": "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Helvetica": "/System/Library/Fonts/Helvetica.ttc",
        "Times New Roman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "Impact": "/System/Library/Fonts/Supplemental/Impact.ttf",
        "Courier New": "/System/Library/Fonts/Supplemental/Courier New.ttf"
    }
    
    candidates = [
        font_path,
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
    print("[WARNING] Could not load a TrueType font - falling back to default (small).")
    return ImageFont.load_default()

def hex_to_rgba(hex_code: str, alpha: int = 255) -> tuple:
    """Convert hex color (#RRGGBB) to RGBA tuple."""
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 6:
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
    elif len(hex_code) == 8:
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4, 6))
    return (255, 255, 255, alpha)


# ──────────────────────────────────────────────────────────────────────────────
# Text renderer  (Pillow → RGBA NumPy array)
# ──────────────────────────────────────────────────────────────────────────────
def render_text(text: str, font: ImageFont.FreeTypeFont, outline_width: int = 6, 
                padding_x: int = 40, padding_y: int = 25, radius: int = 20, 
                bg_color=(0, 0, 0, 180), text_color=(255, 255, 255, 255)) -> np.ndarray:
    """
    Render *text* on a transparent canvas with a thick black outline and a 
    rounded rectangle background. Returns an RGBA uint8 NumPy array.
    """
    # Normalize line endings: browsers send \r\n in textarea form data
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Also convert literal \n escape sequences typed by the user
    text = text.replace('\\n', '\n')
    dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    
    # Calculate exact text bounds
    if hasattr(draw, 'multiline_textbbox'):
        bbox = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=outline_width, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        offset_x = bbox[0]
        offset_y = bbox[1]
    elif hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=outline_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        offset_x = bbox[0]
        offset_y = bbox[1]
    else:
        # Fallback for old Pillow
        text_w, text_h = draw.textsize(text, font=font)
        text_w += outline_width * 2
        text_h += outline_width * 2
        offset_x = 0
        offset_y = 0

    img_w = int(text_w + padding_x * 2)
    img_h = int(text_h + padding_y * 2)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle background
    if hasattr(draw, 'rounded_rectangle'):
        draw.rounded_rectangle([0, 0, img_w, img_h], radius=radius, fill=bg_color)
    else:
        draw.rectangle([0, 0, img_w, img_h], fill=bg_color)

    # Draw text centered exactly inside the padding
    text_pos_x = padding_x - offset_x
    text_pos_y = padding_y - offset_y

    if hasattr(draw, 'multiline_text'):
        draw.multiline_text(
            (text_pos_x, text_pos_y),
            text,
            font=font,
            fill=text_color,
            stroke_width=outline_width,
            stroke_fill=(0, 0, 0, 255),
            align="center",
        )
    else:
        draw.text(
            (text_pos_x, text_pos_y),
            text,
            font=font,
            fill=text_color,
            stroke_width=outline_width,
            stroke_fill=(0, 0, 0, 255),
        )
    return np.array(img)


def render_watermark(text: str, font: ImageFont.FreeTypeFont, alpha_opacity: float = 0.6) -> np.ndarray:
    """Render watermark text with outline based on opacity."""
    outline_width = max(1, font.size // 15)
    
    dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    
    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=outline_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        offset_x = bbox[0]
        offset_y = bbox[1]
    else:
        text_w, text_h = draw.textsize(text, font=font)
        text_w += outline_width * 2
        text_h += outline_width * 2
        offset_x = 0
        offset_y = 0

    img = Image.new("RGBA", (int(text_w + 10), int(text_h + 10)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    opacity_int = int(255 * max(0.0, min(1.0, alpha_opacity)))
    
    draw.text(
        (5 - offset_x, 5 - offset_y),
        text,
        font=font,
        fill=(255, 255, 255, opacity_int),
        stroke_width=outline_width,
        stroke_fill=(0, 0, 0, opacity_int),
    )
    return np.array(img)


# ──────────────────────────────────────────────────────────────────────────────
# Circular-mask helper  (Pillow compositing → RGBA NumPy array)
# ──────────────────────────────────────────────────────────────────────────────
def apply_circle_mask_to_frame(frame: np.ndarray, size: int) -> np.ndarray:
    """Crop *frame* to *size*×*size* square, then apply a circular alpha mask."""
    # Convert to PIL, resize to exact square
    img = Image.fromarray(frame).resize((size, size), Image.LANCZOS)
    img = img.convert("RGBA")

    # Circular alpha mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return np.array(img)


def make_circle_clip(source_path: str, size: int, duration: float) -> ImageClip:
    """
    Load a video or image from *source_path*, apply a circular mask, and
    return a MoviePy clip of *duration* seconds sized *size*×*size*.
    Automatically loops if the source is a shorter video.
    """
    is_video = Path(source_path).suffix.lower() in VIDEO_EXTS
    print(f"[INFO] Loading circle overlay: {source_path} (video={is_video})")

    if is_video:
        raw = VideoFileClip(source_path)
        # Loop if shorter than target duration
        if raw.duration < duration:
            from moviepy import vfx
            raw = raw.with_effects([vfx.Loop(duration=duration)])
        else:
            raw = raw.subclipped(0, duration)

        masked = raw.image_transform(
            lambda frame: apply_circle_mask_to_frame(frame, size)
        )
        return masked.with_duration(duration)

    else:
        raw_img = Image.open(source_path).convert("RGB")
        rgba = apply_circle_mask_to_frame(np.array(raw_img), size)
        return ImageClip(rgba, duration=duration)


# ──────────────────────────────────────────────────────────────────────────────
# Media loader
# ──────────────────────────────────────────────────────────────────────────────
def load_media(path: str, label: str) -> tuple:
    """
    Load image or video from *path*.
    Returns (clip, is_video).
    The clip is NOT yet sized — sizing happens later.
    """
    ext = Path(path).suffix.lower()
    is_video = ext in VIDEO_EXTS
    print(f"[INFO] Loading {label}: {path} ({'video' if is_video else 'image'})")
    if is_video:
        return VideoFileClip(path), True
    else:
        return ImageClip(path), False


def fit_to_box(clip, width: int, height: int, is_video: bool, duration: float, loop: bool = False):
    """
    Scale + centre-crop a clip to exactly *width*×*height*.
    For images, set duration. For videos, optionally loop.
    """
    if is_video and loop and clip.duration < duration:
        print(f"[INFO] Looping video to match duration: {duration:.2f}s")
        from moviepy import vfx
        clip = clip.with_effects([vfx.Loop(duration=duration)])

    # Scale so the clip covers the box (scale-to-fill / cover)
    clip_ar = clip.w / clip.h
    box_ar = width / height

    if clip_ar > box_ar:
        # Clip is wider → match height, then crop width
        clip = clip.resized(height=height)
    else:
        # Clip is taller → match width, then crop height
        clip = clip.resized(width=width)

    # Centre-crop to exact box
    from moviepy.video.fx import Crop
    x1 = (clip.w - width) // 2
    y1 = (clip.h - height) // 2
    clip = Crop(x1=x1, y1=y1, x2=x1 + width, y2=y1 + height).apply(clip)

    if not is_video:
        clip = clip.with_duration(duration)

    return clip.with_duration(duration)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a 9:16 stacked video (1080×1920) with text and optional circle overlay.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--main", required=True, metavar="FILE",
                        help="Main video (must be a video).")
    parser.add_argument("--second", required=True, metavar="FILE",
                        help="Second media — photo or video.")
    parser.add_argument("--circle", metavar="FILE", default=None,
                        help="(Optional) Video or image for circular bottom-right overlay.")
    parser.add_argument("--text", required=True,
                        help="Text shown in the middle seam between the two halves.")
    parser.add_argument("--main-position", choices=["top", "bottom"], default=None,
                        help="Place main video at 'top' or 'bottom'. If omitted, you will be asked.")
    parser.add_argument("--output", default=None, metavar="FILE",
                        help="Output file path (defaults to <main_video_dir>/<main_video_name>_stacked.mp4).")
    parser.add_argument("--font", default=None, metavar="TTF_PATH_OR_NAME",
                        help="Path to a .ttf font file, or a known system font name (Arial, Impact, etc.).")
    parser.add_argument("--font-color", default="#FFFFFF",
                        help="Hex color code for the text (e.g. #FFFFFF).")
    parser.add_argument("--bg-color", default="#000000",
                        help="Hex color code for the text background (e.g. #000000).")
    parser.add_argument("--font-size", type=int, default=70, metavar="N",
                        help="Font size in pixels (default: 70).")
    parser.add_argument("--text-x", type=float, default=50.0,
                        help="X coordinate position as a percentage (default: 50.0).")
    parser.add_argument("--text-y", type=float, default=50.0,
                        help="Y coordinate position as a percentage (default: 50.0).")
    parser.add_argument("--outline-width", type=int, default=6, metavar="N",
                        help="Stroke/outline width for text (default: 6).")
    parser.add_argument("--circle-size", type=int, default=280, metavar="PX",
                        help="Diameter of the circular overlay in pixels (default: 280).")
    parser.add_argument("--circle-margin", type=int, default=40, metavar="PX",
                        help="Margin from the bottom-right edge for the circle (default: 40).")
    parser.add_argument("--watermark-text", default="@MrSinghExperience",
                        help="Watermark text (default: '@MrSinghExperience'). Empty string means no watermark.")
    parser.add_argument("--watermark-font", default=None, metavar="TTF_PATH",
                        help="Path to a .ttf font file for the watermark.")
    parser.add_argument("--watermark-size", type=int, default=45, metavar="N",
                        help="Font size for the watermark (default: 45).")
    parser.add_argument("--watermark-alpha", type=float, default=0.6,
                        help="Opacity of the watermark (0.0 to 1.0, default: 0.6).")
    parser.add_argument("--watermark-top", type=int, default=100,
                        help="Distance from the top edge in pixels (default: 100).")
    parser.add_argument("--watermark-right", type=int, default=40,
                        help="Distance from the right edge in pixels (default: 40).")
    parser.add_argument("--duration", type=float, default=None,
                        help="Override output duration in seconds.")
    parser.add_argument("--fps", type=int, default=30,
                        help="Output frames per second (default: 30).")
    parser.add_argument("--detection-mode", choices=["face", "torso"], default="face",
                        help="Tracking mode: 'face' or 'torso' (default: 'face').")
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
import shlex

def main():
    if len(sys.argv) == 1:
        print("--- Interactive Mode ---")
        
        def _clean_path(p):
            p = p.strip()
            if os.name == 'posix':
                try:
                    tokens = shlex.split(p)
                    if len(tokens) == 1:
                        return os.path.expanduser(tokens[0])
                except ValueError:
                    pass
            # Fallback
            if p.startswith('"') and p.endswith('"'): p = p[1:-1]
            if p.startswith("'") and p.endswith("'"): p = p[1:-1]
            return os.path.expanduser(p)

        def _clean_text(t):
            t = t.strip()
            if t.startswith('"') and t.endswith('"'): t = t[1:-1]
            elif t.startswith("'") and t.endswith("'"): t = t[1:-1]
            return t

        class Args: pass
        args = Args()
        args.main = _clean_path(input("Enter path to main content: "))
        args.second = _clean_path(input("Enter path to secondary content: "))
        while True:
            pos = input("Main video position? [t/b]: ").strip().lower()
            if pos in ["t", "b", "top", "bottom"]:
                args.main_position = "top" if pos in ["t", "top"] else "bottom"
                break
            print("  Please type 't' for top or 'b' for bottom.")
        args.text = _clean_text(input("Enter text for the middle seam: "))
        args.circle = None
        args.output = None
        args.font = None
        args.font_size = 70
        args.outline_width = 6
        args.circle_size = 280
        args.circle_margin = 40
        args.watermark_text = "@MrSinghExperience"
        args.watermark_font = None
        args.watermark_size = 45
        args.watermark_alpha = 0.6
        args.watermark_top = 100
        args.watermark_right = 40
        args.duration = None
        args.fps = 30
        args.detection_mode = "face"
    else:
        args = parse_args()

    # ── Validate inputs ───────────────────────────────────────────────────────
    if not os.path.exists(args.main):
        print(f"[ERROR] --main file not found: {args.main}")
        sys.exit(1)
    if not os.path.exists(args.second):
        print(f"[ERROR] --second file not found: {args.second}")
        sys.exit(1)
    if Path(args.main).suffix.lower() not in VIDEO_EXTS:
        print(f"[ERROR] --main must be a video file, got: {args.main}")
        sys.exit(1)
    if args.circle and not os.path.exists(args.circle):
        print(f"[ERROR] --circle file not found: {args.circle}")
        sys.exit(1)

    # ── Set default output path if none provided ─────────────────────────────
    if getattr(args, "output", None) is None:
        main_path = Path(args.main)
        args.output = str(main_path.parent / f"{main_path.stem}_stacked.mp4")

    # ── Ask where to place the main video ────────────────────────────────────
    main_position = args.main_position
    if not main_position:
        while True:
            answer = input("\nWhere should the MAIN video go? [top / bottom / t / b]: ").strip().lower()
            if answer in ("top", "bottom", "t", "b"):
                main_position = "top" if answer in ("top", "t") else "bottom"
                break
            print("  Please type 't' or 'b'.")

    print(f"\n[INFO] Main video position: {main_position.upper()}")

    # ── Crop main video with head tracking ──────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp_dir:
        cropper = VideoCropper()
        print(f"\n[INFO] Cropping main video with head tracking (9:8 ratio)...")
        
        # We save it into the temp folder so it gets deleted automatically
        tmp_main_path = os.path.join(tmp_dir, "cropped_main_9x8.mp4")
        crop_result = cropper.crop_to_9x8(args.main, output_path=tmp_main_path, mode=args.detection_mode)
        
        if not crop_result['success']:
            print(f"[ERROR] Head tracking crop failed: {crop_result.get('error')}")
            sys.exit(1)
            
        main_9x8_file = crop_result['output_path']

        # ── Load media ────────────────────────────────────────────────────────────
        # Now we load the newly cropped 9:8 main video
        main_clip, _ = load_media(main_9x8_file, "main (cropped)")
        second_clip, is_second_video = load_media(args.second, "second")

        # ── Determine duration ────────────────────────────────────────────────────
        # Use the max of video and audio duration to prevent clipping final words
        if args.duration:
            duration = args.duration
        else:
            duration = main_clip.duration
            if main_clip.audio:
                duration = max(duration, main_clip.audio.duration)
        
        print(f"[INFO] Output duration: {duration:.2f}s")

        # ── Fit each clip to its 1080×960 slot ───────────────────────────────────
        # main_fitted is already 1080x960 from cropper, but fit_to_box ensures duration
        main_fitted   = fit_to_box(main_clip,   OUTPUT_WIDTH, BOX_HEIGHT, True,          duration, loop=False)
        second_fitted = fit_to_box(second_clip, OUTPUT_WIDTH, BOX_HEIGHT, is_second_video, duration, loop=True)

        # ── Assign top / bottom ───────────────────────────────────────────────────
        if main_position == "top":
            top_clip, bot_clip = main_fitted, second_fitted
            audio_clip = main_clip           # audio follows the main video
        else:
            top_clip, bot_clip = second_fitted, main_fitted
            audio_clip = main_clip

        top_clip = top_clip.with_position((0, 0))
        bot_clip = bot_clip.with_position((0, BOX_HEIGHT))

        # ── Build base (stacked) composite ───────────────────────────────────────
        print("[INFO] Compositing base stacked video...")
        base = CompositeVideoClip([top_clip, bot_clip], size=(OUTPUT_WIDTH, OUTPUT_HEIGHT))

        # ── Text overlay ─────────────────────────────────────────────────────────
        print(f"[INFO] Rendering text: '{args.text}'")
        font = get_font(args.font, args.font_size)
        
        # We always enforce slight transparency on the background color for aesthetics
        bg_rgba = hex_to_rgba(args.bg_color, alpha=180) 
        text_rgba = hex_to_rgba(args.font_color, alpha=255)
        
        text_arr = render_text(args.text, font, args.outline_width, bg_color=bg_rgba, text_color=text_rgba)
        
        # Calculate dynamic position based on percentages
        import math
        box_width = text_arr.shape[1]
        box_height = text_arr.shape[0]
        
        x_px = (args.text_x / 100.0) * OUTPUT_WIDTH
        y_px = (args.text_y / 100.0) * OUTPUT_HEIGHT
        
        # Offset by half the boundary box to ensure the coordinate marks the *center* of the text
        top_left_x = math.floor(max(0, min(OUTPUT_WIDTH - box_width, x_px - (box_width / 2))))
        top_left_y = math.floor(max(0, min(OUTPUT_HEIGHT - box_height, y_px - (box_height / 2))))

        text_clip = (
            ImageClip(text_arr)
            .with_duration(duration)
            .with_position((top_left_x, top_left_y))
        )

        # ── Layers ───────────────────────────────────────────────────────────────
        layers = [base, text_clip]

        # ── Watermark (optional) ─────────────────────────────────────────────────
        if getattr(args, "watermark_text", None):
            cleaned_text = args.watermark_text.strip()
            if cleaned_text:
                print(f"[INFO] Rendering watermark: '{cleaned_text}'")
                w_font = get_font(args.watermark_font, args.watermark_size)
                w_arr = render_watermark(cleaned_text, w_font, args.watermark_alpha)
                
                w_w = w_arr.shape[1]
                w_x = OUTPUT_WIDTH - args.watermark_right - w_w
                w_y = args.watermark_top
                
                watermark_clip = (
                    ImageClip(w_arr)
                    .with_duration(duration)
                    .with_position((max(0, w_x), max(0, w_y)))
                )
                layers.append(watermark_clip)

        # ── Circle overlay (optional) ─────────────────────────────────────────────
        if args.circle:
            print("[INFO] Building circular overlay...")
            csize = args.circle_size
            cmarg = args.circle_margin
            circle = make_circle_clip(args.circle, csize, duration)
            circle_pos = (OUTPUT_WIDTH - csize - cmarg, OUTPUT_HEIGHT - csize - cmarg)
            circle = circle.with_position(circle_pos)
            layers.append(circle)

        # ── Final composite ───────────────────────────────────────────────────────
        print("[INFO] Final composite...")
        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT))
        final = final.with_duration(duration)

        # Attach audio from the cropped main video (preserves audio)
        if audio_clip.audio:
            final = final.with_audio(audio_clip.audio.with_duration(duration))

        # ── Write output ──────────────────────────────────────────────────────────
        print(f"[INFO] Writing output → {args.output}")
        final.write_videofile(
            args.output,
            fps=args.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
        )
        print(f"\n[SUCCESS] Done! Output saved to: {args.output}")


if __name__ == "__main__":
    main()