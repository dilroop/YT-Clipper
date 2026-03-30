"""
Media Stacker Module
Joins two 9:8 media parts (videos or photos) together to create a 9:16 video.
Used for the 'stacked_photo' and 'stacked_video' reel formats.

Input: Video path (bottom tracked clip), optional top media path (photo/video), output path.
Output: Stacked 9:16 video (two 1080x960 boxes stacked = 1080x1920).
"""

import subprocess
import cv2
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont


# ==================== FACE TRACKING SETTINGS (mirrors video_cropper constants) ====================
FACE_CHECK_INTERVAL_FRAMES = 4
USE_SMOOTH_INTERPOLATION = True
SMOOTHING_STRENGTH = 0.5
ENABLE_ZERO_FACE_PANNING = True
PAN_LEFT_BOUNDARY = 0.15
PAN_RIGHT_BOUNDARY = 0.85
PAN_CYCLE_DURATION = 8.0
# ===================================================================================================


class MediaStacker:
    def __init__(self):
        """Initialize media stacker"""
        pass

    def convert_stacked_format(
        self,
        video_path: str,
        output_path: str,
        ai_content_type: str = "photo",
        ai_content_path: str = None,
        caption_text: str = None
    ) -> Dict:
        """
        Convert video to stacked 9:8 format (AI content on top + face-tracked highlight on bottom).
        Two 1080x960 boxes stacked = 1080x1920 final output.

        Input:
            video_path: Path to source clip (any aspect ratio)
            output_path: Destination for stacked 9:16 output
            ai_content_type: "photo" or "video" for the top box
            ai_content_path: Optional path to user-provided AI content for top box
            caption_text: Unused (reserved for future caption overlay)

        Output:
            dict with 'success' and 'output_path'
        """
        try:
            print(f"[DEBUG] Converting to stacked {ai_content_type} format")

            temp_dir = Path(tempfile.mkdtemp())
            v_path = Path(video_path)
            o_path = Path(output_path)

            # Get video properties
            cap = cv2.VideoCapture(str(v_path))
            if not cap.isOpened():
                return {'success': False, 'error': f"Cannot open video: {video_path}"}

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            cap.release()

            # Final output: 1080x1920 — each 9:8 box is 1080x960
            box_width = 1080
            box_height = 960

            # ── Step 1: Create bottom box (face-tracked 9:8 crop of source video) ──
            print(f"[DEBUG] Creating bottom 9:8 box with face tracking...")
            bottom_box_path = temp_dir / "bottom_box.mp4"

            timeline = self._get_face_positions_timeline(str(v_path), FACE_CHECK_INTERVAL_FRAMES)
            positions = timeline['positions']

            # 9:8 crop dimensions from source
            crop_height = height
            crop_width = int(crop_height * 9 / 8)

            is_zero_face = (
                len(positions) == 2 and
                positions[0][1] == width // 2 and
                positions[1][1] == width // 2
            )

            if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                print(f"[DEBUG] No faces detected - using smooth panning")
                smooth_positions = self._generate_panning_positions(duration, fps, width, crop_width)
            else:
                print(f"[DEBUG] Interpolating {len(positions)} face positions")
                smooth_positions = self._bezier_interpolate(positions, total_frames, SMOOTHING_STRENGTH)

            crop_x_expr = self._build_crop_expression(
                smooth_positions, fps, width, crop_width, is_zero_face
            )

            vf_filter = f"crop=w={crop_width}:h={crop_height}:x='{crop_x_expr}':y=0,scale={box_width}:{box_height}"
            cmd = [
                'ffmpeg', '-i', str(v_path),
                '-vf', vf_filter,
                '-c:v', 'libx264', '-c:a', 'aac',
                '-preset', 'medium', '-crf', '23', '-y',
                str(bottom_box_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] Bottom box created: {box_width}x{box_height}")

            # ── Step 2: Create or load top box (AI content) ──
            print(f"[DEBUG] Creating top 9:8 box with {ai_content_type}...")
            top_box_path = temp_dir / f"top_box_{ai_content_type}.mp4"

            if ai_content_path and Path(ai_content_path).exists():
                print(f"[DEBUG] Using AI content from: {ai_content_path}")
                cmd = [
                    'ffmpeg', '-i', str(ai_content_path),
                    '-vf', f'scale={box_width}:{box_height}:force_original_aspect_ratio=decrease,'
                           f'pad={box_width}:{box_height}:(ow-iw)/2:(oh-ih)/2',
                    '-t', str(duration),
                    '-c:v', 'libx264', '-an',
                    '-preset', 'medium', '-crf', '23', '-y',
                    str(top_box_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                # Generate Pillow-based placeholder
                self.generate_placeholder(box_width, box_height, duration, fps, str(top_box_path), ai_content_type)

            print(f"[DEBUG] Top box created/prepared: {box_width}x{box_height}")

            # ── Step 3: Stack vertically ──
            print(f"[DEBUG] Stacking boxes vertically...")
            stacked_path = temp_dir / "stacked.mp4"

            cmd = [
                'ffmpeg',
                '-i', str(top_box_path),
                '-i', str(bottom_box_path),
                '-filter_complex', '[0:v][1:v]vstack[stacked]',
                '-map', '[stacked]',
                '-map', '1:a?',
                '-c:v', 'libx264', '-c:a', 'aac',
                '-preset', 'medium', '-crf', '23', '-y',
                str(stacked_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] Stacked video created: 1080x1920")

            shutil.copy(stacked_path, o_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"[DEBUG] Stacked {ai_content_type} format complete: {o_path}")
            return {
                'success': True,
                'output_path': str(o_path),
                'mode': f'stacked_{ai_content_type}',
                'format': f'{box_width}x{box_height * 2} (two {box_width}x{box_height} boxes stacked)'
            }

        except subprocess.CalledProcessError as e:
            err = e.stderr.decode() if e.stderr else str(e)
            return {'success': False, 'error': f"Error in stacked conversion: {err}"}
        except Exception as e:
            return {'success': False, 'error': f"Error in stacked conversion: {str(e)}"}

    def create_stacked_video(
        self,
        top_path: str,
        bottom_path: str,
        output_path: str,
        duration: float,
        width: int = 1080,
        height: int = 1920
    ) -> Dict:
        """
        Stack two pre-processed videos/images vertically.

        Input: Two media paths (top and bottom), output path, duration.
        Output: Stacked 9:16 video.
        """
        box_w, box_h = width, height // 2
        t_path, b_path, o_path = Path(top_path), Path(bottom_path), Path(output_path)

        cmd = [
            'ffmpeg',
            '-i', str(t_path),
            '-i', str(b_path),
            '-filter_complex', f'[0:v]scale={box_w}:{box_h}[top];[1:v]scale={box_w}:{box_h}[bot];[top][bot]vstack[stacked]',
            '-map', '[stacked]',
            '-map', '1:a?',
            '-t', str(duration),
            '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(o_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return {'success': True, 'output_path': str(o_path)}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f"Stacking failed: {e.stderr.decode()}"}

    def generate_placeholder(self, width: int, height: int, duration: float, fps: float, output_path: str, content_type: str):
        """Generate a placeholder image using Pillow and convert to video"""
        print(f"[DEBUG] Generating {content_type} placeholder with Pillow...")
        bg_color = (46, 52, 64) if content_type == "photo" else (59, 66, 82)
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 60)
            small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        draw.text((width // 2, height // 2 - 40), "TODO: Generate with AI", fill=(216, 222, 233), font=font, anchor="mm")
        draw.text((width // 2, height // 2 + 40), f"({content_type.upper()} PLACEHOLDER)", fill=(136, 192, 208), font=small_font, anchor="mm")

        temp_img = Path(output_path).with_suffix('.png')
        img.save(temp_img)

        cmd = [
            'ffmpeg', '-loop', '1', '-i', str(temp_img),
            '-t', str(duration),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(fps),
            '-preset', 'ultrafast', '-y', str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        if temp_img.exists():
            temp_img.unlink()

    # ── Internal helpers (mirrors reels_processor.py exactly) ──────────────────

    def _get_face_positions_timeline(self, video_path: str, check_every_n_frames: int = 8) -> Dict:
        """Get face positions throughout video as a timeline"""
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        import numpy as np
        import urllib.request

        model_path = Path.home() / '.cache' / 'mediapipe' / 'blaze_face_short_range.tflite'
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if not model_path.exists():
            url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            urllib.request.urlretrieve(url, model_path)
        with open(model_path, 'rb') as f:
            model_data = f.read()

        base_options = python.BaseOptions(model_asset_buffer=model_data)
        video_options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_detection_confidence=0.5,
            min_suppression_threshold=0.3
        )
        video_detector = vision.FaceDetector.create_from_options(video_options)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        positions = []
        min_face_size = int(height * 0.08)
        edge_margin = int(width * 0.05)

        frame_idx = 0
        while frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_idx / fps) * 1000)
            detection_result = video_detector.detect_for_video(mp_image, timestamp_ms)

            timestamp = frame_idx / fps
            best_face_x = None
            if detection_result.detections:
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    x_min = int(bbox.origin_x)
                    w = int(bbox.width)
                    h = int(bbox.height)
                    if w < min_face_size or h < min_face_size:
                        continue
                    face_center_x = x_min + w // 2
                    if face_center_x < edge_margin or face_center_x > width - edge_margin:
                        continue
                    confidence = detection.categories[0].score if detection.categories else 0.0
                    if confidence < 0.6:
                        continue
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio < 0.6 or aspect_ratio > 1.4:
                        continue
                    best_face_x = face_center_x
                    break

            if best_face_x is not None:
                positions.append((timestamp, best_face_x))

            frame_idx += check_every_n_frames

        cap.release()
        if not positions:
            positions = [(0.0, width // 2), (total_frames / fps, width // 2)]

        return {
            'positions': positions,
            'fps': fps,
            'width': width,
            'height': height,
            'total_frames': total_frames
        }

    def _bezier_interpolate(self, points: List[Tuple], num_samples: int, smoothness: float = 0.5) -> List[Tuple]:
        """Interpolate between points using CubicSpline for smooth curves"""
        import numpy as np
        from scipy import interpolate

        if len(points) < 2:
            return points

        times = np.array([p[0] for p in points])
        values = np.array([p[1] for p in points])
        t_min, t_max = times[0], times[-1]
        interp_times = np.linspace(t_min, t_max, num_samples)
        cs = interpolate.CubicSpline(times, values, bc_type='natural')
        interp_values = cs(interp_times)

        if smoothness > 0.3:
            from scipy.ndimage import gaussian_filter1d
            interp_values = gaussian_filter1d(interp_values, sigma=smoothness * 2)

        return list(zip(interp_times, interp_values))

    def _generate_panning_positions(self, duration: float, fps: float, width: int, crop_width: int) -> List[Tuple]:
        """Generate smooth panning positions for zero-face segments"""
        import math
        left_boundary_px = int(width * PAN_LEFT_BOUNDARY)
        right_boundary_px = int(width * PAN_RIGHT_BOUNDARY) - crop_width
        right_boundary_px = max(left_boundary_px, min(right_boundary_px, width - crop_width))
        center_x = (left_boundary_px + right_boundary_px) / 2
        amplitude = (right_boundary_px - left_boundary_px) / 2

        num_frames = int(duration * fps)
        positions = []
        for frame in range(num_frames):
            time = frame / fps
            angle = (2 * math.pi * time) / PAN_CYCLE_DURATION
            x_position = center_x + amplitude * math.sin(angle - math.pi / 2)
            x_position = max(left_boundary_px, min(x_position, right_boundary_px))
            positions.append((time, x_position))
        return positions

    def _build_crop_expression(self, smooth_positions: List[Tuple], fps: float, width: int, crop_width: int, is_zero_face: bool) -> str:
        """Build piecewise-linear FFmpeg crop x-expression from smooth position timeline"""
        sample_interval = fps
        sampled_indices = range(0, len(smooth_positions), int(sample_interval))
        expr_parts = []

        for i, idx in enumerate(sampled_indices):
            if idx >= len(smooth_positions):
                break
            time, face_x = smooth_positions[idx]
            frame_num = int(time * fps)
            crop_x = int(face_x) if is_zero_face else int(face_x - crop_width // 2)
            crop_x = max(0, min(crop_x, width - crop_width))

            if i == 0:
                expr_parts.append(f"if(lt(n,{frame_num}),{crop_x}")
            else:
                if i < len(list(sampled_indices)) - 1:
                    next_idx = list(sampled_indices)[i + 1]
                    if next_idx < len(smooth_positions):
                        next_time, next_face_x = smooth_positions[min(next_idx, len(smooth_positions) - 1)]
                        next_frame = int(next_time * fps)
                        next_crop_x = int(next_face_x) if is_zero_face else int(next_face_x - crop_width // 2)
                        next_crop_x = max(0, min(next_crop_x, width - crop_width))
                        if next_frame > frame_num:
                            expr_parts.append(f",if(lt(n,{next_frame}),{crop_x}+(n-{frame_num})*({next_crop_x}-{crop_x})/{next_frame - frame_num}")
                else:
                    expr_parts.append(f",{crop_x}")

        expr_parts.append(")" * (len(expr_parts) - 1))
        return "".join(expr_parts)
