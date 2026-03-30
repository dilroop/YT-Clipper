"""
Video Processor Package
Contains specialized modules for various video processing tasks:
- Transcription
- Cropping
- Sectioning/Cutting
- Media Stacking
- Subtitle Burning
- Watermarking
"""

from .transcriber import AudioTranscriber
from .video_cropper import VideoCropper
from .section_cutter import SectionCutter
from .media_stacker import MediaStacker
from .subtitle_burner import SubtitleBurner
from .watermarker import Watermarker
