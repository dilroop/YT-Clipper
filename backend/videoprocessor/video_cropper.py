"""
Video Cropper Module
Intelligent video cropping (9:16 or 9:8) with face tracking using MediaPipe.

Rules for 9:16 (Reels):
  - 0 faces  → smooth left-right pan across full frame (3s cycles)
  - 1 face   → center a 9:16 crop window on the face (no stretch/skew)
  - 2 faces  → two stacked 9:8 blocks, each centered on their face
  - >2 faces → vertical centre-split, each half scaled to 9:8, then vstacked

Rules for 9:8 (Workflow main block):
  - 0 count  → smooth left-right pan (3s cycles)
  - 1 count  → center a 9:8 crop window on the target (face/torso)
  - 2 count  → each target gets a 4.5:8 crop; hstacked to fill 9:8
  - >2 count → smooth left-right pan (same as 0 count)
"""

import cv2
import subprocess
import mediapipe as mp
import urllib.request
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ──────────────────────────────────────────────────────────────────────────────
# Module-level constants
# ──────────────────────────────────────────────────────────────────────────────

FACE_CHECK_INTERVAL_FRAMES = 4    # Sample every N frames for performance
MIN_SEGMENT_DURATION_S     = 1.5  # Shorter segments are merged to avoid flicker
PAN_CYCLE_SECONDS          = 6.0  # Full cycle: left→right (3s) then right→left (3s)


class VideoCropper:
    """
    Crop a video to 9:16 (for Reels) or 9:8 (for Workflow stacked block)
    using MediaPipe face detection to drive the crop window.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Initialisation & model helpers
    # ──────────────────────────────────────────────────────────────────────────

    def __init__(self):
        pass

    def _get_face_detection_model(self) -> bytes:
        """Download (once) and return the MediaPipe face-detection model bytes."""
        # Using full-range for better distance detection as planned
        model_name = "blaze_face_full_range.tflite"
        model_path = Path.home() / ".cache" / "mediapipe" / model_name
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if not model_path.exists():
            print(f"[CROPPER] Downloading MediaPipe face detection model ({model_name})…")
            url = (
                "https://storage.googleapis.com/mediapipe-models/"
                "face_detector/blaze_face_full_range/float16/1/"
                "blaze_face_full_range.tflite"
            )
            urllib.request.urlretrieve(url, model_path)
            print("[CROPPER] Model downloaded.")
        with open(model_path, "rb") as f:
            return f.read()

    def _get_pose_model(self) -> bytes:
        """Download (once) and return the MediaPipe pose landmarker model bytes."""
        model_name = "pose_landmarker_lite.task"
        model_path = Path.home() / ".cache" / "mediapipe" / model_name
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if not model_path.exists():
            print(f"[CROPPER] Downloading MediaPipe pose landmarker model ({model_name})…")
            url = (
                "https://storage.googleapis.com/mediapipe-models/"
                "pose_landmarker/pose_landmarker_lite/float16/1/"
                "pose_landmarker_lite.task"
            )
            urllib.request.urlretrieve(url, model_path)
            print("[CROPPER] Model downloaded.")
        with open(model_path, "rb") as f:
            return f.read()

    # ──────────────────────────────────────────────────────────────────────────
    # Face detection
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_valid_faces(self, detections, width: int, height: int) -> List[Dict]:
        """
        Filter raw MediaPipe detections to valid, prominent faces.
        Returns a list of dicts with 'center_x', 'center_y', 'width', 'height'.
        """
        min_face_size = int(height * 0.04)
        edge_margin   = int(width  * 0.02)
        faces = []

        for det in (detections or []):
            bbox = det.bounding_box
            x, y, fw, fh = int(bbox.origin_x), int(bbox.origin_y), int(bbox.width), int(bbox.height)
            cx = x + fw // 2

            if fw < min_face_size or fh < min_face_size:
                continue
            if cx < edge_margin or cx > width - edge_margin:
                continue
            conf = det.categories[0].score if det.categories else 0.0
            if conf < 0.35: # Slightly more lenient
                continue
            ratio = fw / fh if fh > 0 else 0
            if ratio < 0.4 or ratio > 2.0:
                continue

            faces.append({"center_x": cx, "center_y": y + fh // 2, "width": fw, "height": fh})

        faces.sort(key=lambda f: f["center_x"])

        # Merge faces that are too close together
        merged: List[Dict] = []
        for f in faces:
            if not merged or (f["center_x"] - merged[-1]["center_x"] > width * 0.10):
                merged.append(f)

        if len(merged) == 2:
            w1, w2 = merged[0]["width"], merged[1]["width"]
            if min(w1, w2) / max(w1, w2) < 0.30:
                merged = [max(merged, key=lambda f: f["width"])]

        return merged

    def _detect_valid_torsos(self, pose_result, width: int, height: int) -> List[Dict]:
        """
        Extract torso/person centers from pose landmarks.
        Uses shoulder midpoint (landmark 11 & 12) as proxy for 'head/chest' center.
        """
        if not pose_result or not pose_result.pose_landmarks:
            return []

        torsos = []
        edge_margin = int(width * 0.02)

        for landmarks in pose_result.pose_landmarks:
            # 11: Left Shoulder, 12: Right Shoulder
            l_sh = landmarks[11]
            r_sh = landmarks[12]
            
            # MediaPipe landmarks are normalized [0, 1]
            if l_sh.visibility < 0.4 or r_sh.visibility < 0.4:
                continue
                
            cx = int(((l_sh.x + r_sh.x) / 2) * width)
            cy = int(((l_sh.y + r_sh.y) / 2) * height)
            
            # Estimate a 'width' for sorting and merging based on shoulder distance
            sh_dist = abs(l_sh.x - r_sh.x) * width
            tw = int(sh_dist * 2.5) # Approximate person width
            th = int(height * 0.3)  # Dummy height

            if cx < edge_margin or cx > width - edge_margin:
                continue
                
            torsos.append({"center_x": cx, "center_y": cy, "width": tw, "height": th})

        torsos.sort(key=lambda f: f["center_x"])

        # Merge torsos that are too close together
        merged: List[Dict] = []
        for t in torsos:
            if not merged or (t["center_x"] - merged[-1]["center_x"] > width * 0.15):
                merged.append(t)
        
        return merged

    def detect_segments(self, video_path: str, mode: str = "face") -> List[Dict]:
        """
        Scan the video and return a merged list of segments.
        mode can be 'face' or 'torso'.
        """
        if mode == "torso":
            model_bytes = self._get_pose_model()
            base_options = python.BaseOptions(model_asset_buffer=model_bytes)
            vid_options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_poses=5,
                min_pose_detection_confidence=0.3,
                min_pose_presence_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            detector = vision.PoseLandmarker.create_from_options(vid_options)
        else:
            model_bytes = self._get_face_detection_model()
            base_options = python.BaseOptions(model_asset_buffer=model_bytes)
            vid_options = vision.FaceDetectorOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                min_detection_confidence=0.3,
                min_suppression_threshold=0.3,
            )
            detector = vision.FaceDetector.create_from_options(vid_options)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps          = cap.get(cv2.CAP_PROP_FPS)
        width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        raw_segments: List[Dict] = []
        current: Dict | None     = None
        
        # Hysteresis variables for smoothing flickering detections
        hysteresis_frames = 6 # ~0.2s at 30fps
        consecutive_misses = 0

        for frame_idx in range(0, total_frames, FACE_CHECK_INTERVAL_FRAMES):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int((frame_idx / fps) * 1000)
            res  = detector.detect_for_video(img, ts_ms)

            if mode == "torso":
                targets = self._detect_valid_torsos(res, width, height)
            else:
                targets = self._detect_valid_faces(res.detections, width, height)
            
            tc = len(targets)
            timestamp = frame_idx / fps

            # Apply stickiness: if we had targets and now we don't, wait a few frames
            if current is not None and current["face_count"] > 0 and tc == 0:
                consecutive_misses += 1
                if consecutive_misses < hysteresis_frames:
                    # Keep the previous targets for this frame
                    # We don't advance the segment yet
                    continue
            
            consecutive_misses = 0

            if current is None or current["face_count"] != tc:
                if current is not None:
                    current["end_time"]  = timestamp
                    current["end_frame"] = frame_idx
                    raw_segments.append(current)
                current = {
                    "face_count":  tc, # Using face_count key for backward compatibility in Rules
                    "start_time":  timestamp,
                    "start_frame": frame_idx,
                    "faces":       [targets] if targets else [],
                }
            else:
                if targets:
                    current["faces"].append(targets)

        if current is not None:
            # Use a very large number for the last segment to ensure we hit the true end of the file
            # instead of relying on potentially inaccurate total_frames/fps calculations.
            current["end_time"]  = 99999.0
            current["end_frame"] = total_frames
            raw_segments.append(current)

        cap.release()
        return self._merge_segments(raw_segments)

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """Merge short segments (< MIN_SEGMENT_DURATION_S) into their neighbor."""
        if not segments:
            return []

        # Pass 1: absorb tiny segments into previous
        filtered: List[Dict] = []
        for i, seg in enumerate(segments):
            dur = seg["end_time"] - seg["start_time"]
            if dur >= MIN_SEGMENT_DURATION_S or i == len(segments) - 1:
                filtered.append(seg)
            elif filtered:
                filtered[-1]["end_time"] = seg["end_time"]
                filtered[-1]["faces"].extend(seg.get("faces", []))
        if not filtered:
            return []

        # Pass 2: merge adjacent segments with same face_count
        merged: List[Dict] = []
        curr = filtered[0].copy()
        for seg in filtered[1:]:
            if seg["face_count"] == curr["face_count"]:
                curr["end_time"] = seg["end_time"]
                curr["faces"].extend(seg.get("faces", []))
            else:
                merged.append(curr)
                curr = seg.copy()
        merged.append(curr)
        return merged

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────────────────────────────────

    def convert_to_reels(self, video_path: str, output_path: str = None, mode: str = "face", **kwargs) -> Dict:
        """Convert video to 9:16 (1080×1920) using face/torso rules."""
        return self._process(video_path, output_path, ratio="9:16", out_w=1080, out_h=1920, mode=mode)

    def crop_to_9x8(self, video_path: str, output_path: str = None, mode: str = "face") -> Dict:
        """Convert video to 9:8 (1080×960) using face/torso rules."""
        return self._process(video_path, output_path, ratio="9:8",  out_w=1080, out_h=960, mode=mode)

    # ──────────────────────────────────────────────────────────────────────────
    # Core processor
    # ──────────────────────────────────────────────────────────────────────────

    def _process(self, video_path: str, output_path: str | None, ratio: str, out_w: int, out_h: int, mode: str = "face") -> Dict:
        v_path = Path(video_path)
        o_path = Path(output_path) if output_path else v_path.parent / f"{v_path.stem}_{ratio.replace(':','x')}.mp4"

        print(f"[CROPPER] {v_path.name}  →  {ratio} ({out_w}×{out_h})")

        cap = cv2.VideoCapture(str(v_path))
        src_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Native crop window size matching target aspect
        crop_w = int(src_h * out_w / out_h)
        crop_h = src_h
        # Clamp if video is narrower than the target aspect
        if crop_w > src_w:
            crop_w = src_w
            crop_h = int(src_w * out_h / out_w)

        segments = self.detect_segments(str(v_path), mode=mode)
        if not segments:
            segments = [{"face_count": 0, "start_time": 0.0, "end_time": 1e9, "faces": []}]

        t_dir   = Path(tempfile.mkdtemp())
        proc_files: List[Path] = []

        try:
            # Check for audio presence
            a_check = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0", 
                 "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(v_path)],
                capture_output=True, text=True
            )
            has_audio = len(a_check.stdout.strip()) > 0

            # -- Process each face segment --
            for i, seg in enumerate(segments):
                raw_seg = t_dir / f"seg_{i}_raw.mp4"
                proc_seg = t_dir / f"seg_{i}_proc.mp4"

                # 1) Extract segment with sync preserved (both video and audio)
                raw_cmd = [
                    "ffmpeg", "-i", str(v_path),
                    "-ss", str(seg["start_time"]), "-to", str(seg["end_time"]),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"
                ]
                if has_audio:
                    raw_cmd.extend(["-c:a", "aac"])
                else:
                    raw_cmd.append("-an")
                raw_cmd.extend(["-y", str(raw_seg)])

                subprocess.run(raw_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # 2) Build filter and crop
                vf = self._build_filter(
                    seg, ratio=ratio,
                    src_w=src_w, src_h=src_h,
                    crop_w=crop_w, crop_h=crop_h,
                    out_w=out_w, out_h=out_h,
                )

                proc_cmd = [
                    "ffmpeg", "-i", str(raw_seg), "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20"
                ]
                if has_audio:
                    proc_cmd.extend(["-c:a", "copy"])
                else:
                    proc_cmd.append("-an")
                proc_cmd.extend(["-y", str(proc_seg)])

                subprocess.run(proc_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                proc_files.append(proc_seg)

            # -- Concatenate processed segments --
            # Both Audio and Video will be perfectly concatenated in sync
            concat_list = t_dir / "list.txt"
            concat_list.write_text("\n".join(f"file '{p}'" for p in proc_files))

            subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                 "-c", "copy", "-y", str(o_path)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

            print(f"[CROPPER] Done → {o_path}")
            return {"success": True, "output_path": str(o_path)}

        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(exc)}

        finally:
            shutil.rmtree(t_dir, ignore_errors=True)

    # ──────────────────────────────────────────────────────────────────────────
    # FFmpeg filter builders
    # ──────────────────────────────────────────────────────────────────────────

    def _build_filter(
        self,
        seg: Dict,
        ratio: str,
        src_w: int, src_h: int,
        crop_w: int, crop_h: int,
        out_w: int, out_h: int,
    ) -> str:
        fc    = seg["face_count"]
        faces = seg.get("faces", [])

        if ratio == "9:16":
            return self._filter_9x16(fc, faces, src_w, src_h, crop_w, crop_h, out_w, out_h)
        else:
            return self._filter_9x8(fc, faces, src_w, src_h, crop_w, crop_h, out_w, out_h)

    # ---------- helpers ----------

    def _pan_expr(self, src_w: int, crop_w: int) -> str:
        """
        Smooth sinusoidal pan expression for FFmpeg.
        Starts at the LEFT edge (x=0), reaches the RIGHT edge at t=3s,
        then sweeps back — full cycle is PAN_CYCLE_SECONDS (6s).
        Uses (1 - cos) which equals 0 at t=0 and 1 at t=half_period.
        """
        pan_range = max(0, src_w - crop_w)
        half = PAN_CYCLE_SECONDS / 2  # 3.0 — the left→right travel time
        return f"(1-cos(t*2*PI/{PAN_CYCLE_SECONDS:.1f}))/2*{pan_range}"

    def _avg_center_x(self, faces: List[List[Dict]], face_idx: int, fallback: float) -> float:
        """Average the center_x of face[face_idx] across all sample frames."""
        xs = [
            frame_faces[face_idx]["center_x"]
            for frame_faces in faces
            if len(frame_faces) > face_idx
        ]
        return sum(xs) / len(xs) if xs else fallback

    def _clamp_cx(self, cx: float, crop_w: int, src_w: int) -> int:
        return max(0, min(int(cx - crop_w / 2), src_w - crop_w))

    # ---------- 9:16 rules ----------

    def _filter_9x16(
        self,
        fc: int, faces: List[List[Dict]],
        src_w: int, src_h: int,
        crop_w: int, crop_h: int,
        out_w: int, out_h: int,
    ) -> str:

        if fc == 0:
            # Animate left-to-right pan
            pan = self._pan_expr(src_w, crop_w)
            return f"crop={crop_w}:{crop_h}:'{pan}':0,scale={out_w}:{out_h}"

        if fc == 1:
            avg_x = self._avg_center_x(faces, 0, src_w / 2)
            cx    = self._clamp_cx(avg_x, crop_w, src_w)
            return f"crop={crop_w}:{crop_h}:{cx}:0,scale={out_w}:{out_h}"

        if fc == 2:
            # Two stacked 9:8 blocks
            half_h    = out_h // 2           # 960 px
            blk_crop_w = int(src_h * out_w / half_h)   # 9:8 width in source pixels
            blk_crop_h = src_h
            if blk_crop_w > src_w:
                blk_crop_w = src_w
                blk_crop_h = int(src_w * half_h / out_w)

            cx0 = self._clamp_cx(self._avg_center_x(faces, 0, src_w / 3),   blk_crop_w, src_w)
            cx1 = self._clamp_cx(self._avg_center_x(faces, 1, src_w * 2/3), blk_crop_w, src_w)
            cy  = (src_h - blk_crop_h) // 2

            return (
                f"[0:v]split=2[a][b];"
                f"[a]crop={blk_crop_w}:{blk_crop_h}:{cx0}:{cy},scale={out_w}:{half_h}[ta];"
                f"[b]crop={blk_crop_w}:{blk_crop_h}:{cx1}:{cy},scale={out_w}:{half_h}[tb];"
                f"[ta][tb]vstack"
            )

        # >2 faces: split vertically down the middle, stack each half
        half_out_h = out_h // 2
        half_src_w = src_w // 2
        return (
            f"[0:v]split=2[l][r];"
            f"[l]crop={half_src_w}:{src_h}:0:0,scale={out_w}:{half_out_h}[tl];"
            f"[r]crop={half_src_w}:{src_h}:{half_src_w}:0,scale={out_w}:{half_out_h}[tr];"
            f"[tl][tr]vstack"
        )

    # ---------- 9:8 rules ----------

    def _filter_9x8(
        self,
        fc: int, faces: List[List[Dict]],
        src_w: int, src_h: int,
        crop_w: int, crop_h: int,
        out_w: int, out_h: int,
    ) -> str:

        if fc == 0 or fc > 2:
            # Animate left-to-right pan (both 0 and >2 faces)
            pan = self._pan_expr(src_w, crop_w)
            return f"crop={crop_w}:{crop_h}:'{pan}':0,scale={out_w}:{out_h}"

        if fc == 1:
            avg_x = self._avg_center_x(faces, 0, src_w / 2)
            cx    = self._clamp_cx(avg_x, crop_w, src_w)
            return f"crop={crop_w}:{crop_h}:{cx}:0,scale={out_w}:{out_h}"

        # fc == 2: each face gets 4.5:8 (half of 9:8), hstacked
        half_out_w  = out_w // 2           # 540 px
        half_crop_w = int(src_h * half_out_w / out_h)   # 4.5:8 width in source
        if half_crop_w > src_w // 2:
            half_crop_w = src_w // 2

        cx0 = self._clamp_cx(self._avg_center_x(faces, 0, src_w / 3),   half_crop_w, src_w)
        cx1 = self._clamp_cx(self._avg_center_x(faces, 1, src_w * 2/3), half_crop_w, src_w)

        return (
            f"[0:v]split=2[a][b];"
            f"[a]crop={half_crop_w}:{src_h}:{cx0}:0,scale={half_out_w}:{out_h}[la];"
            f"[b]crop={half_crop_w}:{src_h}:{cx1}:0,scale={half_out_w}:{out_h}[lb];"
            f"[la][lb]hstack"
        )
