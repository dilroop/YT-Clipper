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
from pathlib import Path
from moviepy import VideoFileClip, concatenate_videoclips

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

def remove_silences(input_path: str, output_path: str, threshold_ms: int, keep_ms: int):
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
    seg_start = max(0.0, last_end - keep_s / 2.0)
    seg_end = total_duration
    if seg_end > seg_start:
        keep_segments.append((seg_start, seg_end))
        
    print(f"[INFO] Concatenating {len(keep_segments)} audio segments...")
    
    subclips = [clip.subclipped(s, e) for s, e in keep_segments]
    final_clip = concatenate_videoclips(subclips)
    
    print(f"[INFO] Writing output ({final_clip.duration:.2f}s) → {output_path}")
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True
    )
    
    clip.close()
    final_clip.close()

def main():
    parser = argparse.ArgumentParser(description="Workflow 3: Skip Silences")
    parser.add_argument("--input", help="Path to input video")
    parser.add_argument("--output", help="Path to output video")
    parser.add_argument("--threshold", type=int, default=500, help="Min silence length in ms (default: 500)")
    parser.add_argument("--keep", type=int, default=100, help="Silence to keep after removal in ms (default: 100)")
    
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
        remove_silences(args.input, args.output, args.threshold, args.keep)
        print(f"\n[SUCCESS] Done! Output saved to: {args.output}")
    except Exception as e:
        print(f"\n[ERROR] Workflow failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
