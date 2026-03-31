import sys
import os
from pathlib import Path
import asyncio

# Setup path so backend is importable
sys.path.append(str(Path('.').absolute()))

from backend.videoprocessor.subtitle_burner import SubtitleBurner

def test_fallback():
    # Provide path to a previously generated reels clip
    video_path = "temp/processed_clip_1_478059218.mp4"
    ass_path = "temp/dummy.ass"
    out_path = "temp/test_png_out.mp4"
    
    if not os.path.exists(video_path):
        print(f"File {video_path} does not exist.")
        return
        
    burner = SubtitleBurner()
    
    # Create a dummy ASS file
    import cv2
    cap = cv2.VideoCapture(video_path)
    c_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    c_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    dummy_words = [{'word': 'HELLO', 'start': 0, 'end': 2}, {'word': 'WORLD', 'start': 2, 'end': 4}]
    burner.create_ass_subtitles(dummy_words, ass_path, clip_start_time=0, video_width=c_width, video_height=c_height)

    
    try:
        res = burner.burn_captions_with_pngs(video_path, ass_path, out_path)
        print("Result:", res)
    except Exception as e:
        print("Exception:", str(e))

if __name__ == "__main__":
    test_fallback()
