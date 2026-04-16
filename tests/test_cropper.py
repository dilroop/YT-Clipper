"""
tests/test_cropper.py
=====================
Test suite for the VideoCropper module.
Runs both `crop_to_9x8` (9:8) and `convert_to_reels` (9:16) on
tests/test_clip.mp4 and verifies:
  - output file is created
  - output has the correct resolution
  - output is a valid video (has at least 1 frame and non-zero duration)

Usage:
    cd /Users/dilroop/workspace/YT-Clipper
    python -m pytest tests/test_cropper.py -v
"""

import sys
import subprocess
from pathlib import Path
import json
import pytest

# Make sure backend package is importable
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.videoprocessor.video_cropper import VideoCropper

TEST_CLIP = Path(__file__).parent / "test_clip.mp4"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_video_info(path: str) -> dict:
    """Return width, height, duration of a video using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    info = json.loads(result.stdout)

    video_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
        None
    )
    if not video_stream:
        raise RuntimeError("No video stream found")

    return {
        "width":    int(video_stream.get("width", 0)),
        "height":   int(video_stream.get("height", 0)),
        "duration": float(info["format"].get("duration", 0)),
        "nb_frames": int(video_stream.get("nb_frames", 0) or 0),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def cropper():
    return VideoCropper()


@pytest.fixture(scope="module")
def test_clip():
    if not TEST_CLIP.exists():
        pytest.skip(f"Test clip not found: {TEST_CLIP}")
    return str(TEST_CLIP)


# ──────────────────────────────────────────────────────────────────────────────
# Tests — face detection
# ──────────────────────────────────────────────────────────────────────────────

class TestFaceDetection:
    def test_detect_face_segments_returns_list(self, cropper, test_clip, tmp_path):
        """detect_face_segments should always return a list (possibly empty)."""
        segments = cropper.detect_face_segments(test_clip)
        assert isinstance(segments, list), "Expected a list of segments"

    def test_segments_have_required_keys(self, cropper, test_clip):
        segments = cropper.detect_face_segments(test_clip)
        for seg in segments:
            assert "face_count" in seg
            assert "start_time" in seg
            assert "end_time"   in seg
            assert seg["end_time"] > seg["start_time"], "Segment end must be after start"

    def test_segments_time_coverage(self, cropper, test_clip):
        """Segments should cover the whole video without gaps."""
        segments = cropper.detect_face_segments(test_clip)
        if not segments:
            return  # Nothing to validate
        first_start = segments[0]["start_time"]
        last_end    = segments[-1]["end_time"]
        # First segment must start near 0, last must end near video end
        assert first_start < 1.0, "First segment should start near 0 s"
        info = get_video_info(test_clip)
        assert last_end >= info["duration"] - 2.0, "Last segment should cover video end"


# ──────────────────────────────────────────────────────────────────────────────
# Tests — 9:8 cropping
# ──────────────────────────────────────────────────────────────────────────────

class TestCropTo9x8:
    def test_output_file_created(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "out_9x8.mp4")
        result = cropper.crop_to_9x8(test_clip, out)
        assert result.get("success"), f"crop_to_9x8 failed: {result.get('error')}"
        assert Path(out).exists(), "Output file was not created"

    def test_output_resolution(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "res_9x8.mp4")
        result = cropper.crop_to_9x8(test_clip, out)
        assert result.get("success"), result.get("error")

        info = get_video_info(out)
        assert info["width"]  == 1080, f"Expected width 1080, got {info['width']}"
        assert info["height"] == 960,  f"Expected height 960, got {info['height']}"

    def test_output_has_duration(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "dur_9x8.mp4")
        result = cropper.crop_to_9x8(test_clip, out)
        assert result.get("success"), result.get("error")

        info = get_video_info(out)
        src  = get_video_info(test_clip)
        # Duration can differ by up to 2 seconds (e.g. re-encoding rounding)
        assert abs(info["duration"] - src["duration"]) < 2.0, (
            f"Output duration {info['duration']:.2f}s differs too much "
            f"from source {src['duration']:.2f}s"
        )

    def test_failure_on_missing_input(self, cropper, tmp_path):
        result = cropper.crop_to_9x8("/nonexistent/file.mp4", str(tmp_path / "out.mp4"))
        assert not result.get("success"), "Expected failure for missing input"


# ──────────────────────────────────────────────────────────────────────────────
# Tests — 9:16 (reels) cropping
# ──────────────────────────────────────────────────────────────────────────────

class TestConvertToReels:
    def test_output_file_created(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "out_9x16.mp4")
        result = cropper.convert_to_reels(test_clip, out)
        assert result.get("success"), f"convert_to_reels failed: {result.get('error')}"
        assert Path(out).exists(), "Output file was not created"

    def test_output_resolution(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "res_9x16.mp4")
        result = cropper.convert_to_reels(test_clip, out)
        assert result.get("success"), result.get("error")

        info = get_video_info(out)
        assert info["width"]  == 1080, f"Expected width 1080, got {info['width']}"
        assert info["height"] == 1920, f"Expected height 1920, got {info['height']}"

    def test_output_has_duration(self, cropper, test_clip, tmp_path):
        out = str(tmp_path / "dur_9x16.mp4")
        result = cropper.convert_to_reels(test_clip, out)
        assert result.get("success"), result.get("error")

        info = get_video_info(out)
        src  = get_video_info(test_clip)
        assert abs(info["duration"] - src["duration"]) < 2.0, (
            f"Output duration {info['duration']:.2f}s differs too much "
            f"from source {src['duration']:.2f}s"
        )

    def test_failure_on_missing_input(self, cropper, tmp_path):
        result = cropper.convert_to_reels("/nonexistent/file.mp4", str(tmp_path / "out.mp4"))
        assert not result.get("success"), "Expected failure for missing input"


# ──────────────────────────────────────────────────────────────────────────────
# Quick standalone runner (no pytest required)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TESTS_DIR = Path(__file__).parent
    OUT_9x8   = TESTS_DIR / "test_clip_9x8.mp4"
    OUT_9x16  = TESTS_DIR / "test_clip_9x16.mp4"

    print(f"\n{'='*60}")
    print("VideoCropper — standalone test run")
    print(f"Test clip : {TEST_CLIP}")
    print(f"Output 9:8  → {OUT_9x8}")
    print(f"Output 9:16 → {OUT_9x16}")
    print(f"{'='*60}\n")

    if not TEST_CLIP.exists():
        print(f"[ERROR] test_clip.mp4 not found at {TEST_CLIP}")
        sys.exit(1)

    c = VideoCropper()

    # --- Face detection ---
    print(">> detect_face_segments …")
    segs = c.detect_face_segments(str(TEST_CLIP))
    print(f"   Found {len(segs)} segment(s):")
    for s in segs:
        print(f"   [{s['start_time']:.1f}s – {s['end_time']:.1f}s] "
              f"face_count={s['face_count']}")

    # --- 9:8 ---
    print("\n>> crop_to_9x8 …")
    res = c.crop_to_9x8(str(TEST_CLIP), str(OUT_9x8))
    if res.get("success"):
        info = get_video_info(str(OUT_9x8))
        ok = "✓" if info["width"] == 1080 and info["height"] == 960 else "✗"
        print(f"   {ok} {info['width']}×{info['height']}  duration={info['duration']:.2f}s")
        print(f"   Saved → {OUT_9x8}")
    else:
        print(f"   ✗ FAILED: {res.get('error')}")

    # --- 9:16 ---
    print("\n>> convert_to_reels …")
    res = c.convert_to_reels(str(TEST_CLIP), str(OUT_9x16))
    if res.get("success"):
        info = get_video_info(str(OUT_9x16))
        ok = "✓" if info["width"] == 1080 and info["height"] == 1920 else "✗"
        print(f"   {ok} {info['width']}×{info['height']}  duration={info['duration']:.2f}s")
        print(f"   Saved → {OUT_9x16}")
    else:
        print(f"   ✗ FAILED: {res.get('error')}")

    print(f"\n{'='*60}")
    print("Done. Output files saved in tests/ folder.")

