"""
Video Cropper Module
Intelligent video cropping (9:16 or 9:8) with face tracking using MediaPipe.

Input: Video path, output path, and tracking settings.
Output: Cropped video in 9:16 (Standard Reels) or 9:8 (Stacked part) format.
"""

import cv2
import subprocess
import numpy as np
import mediapipe as mp
import math
import os
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ==================== FACE TRACKING SETTINGS ====================
FACE_CHECK_INTERVAL_FRAMES = 2
USE_SMOOTH_INTERPOLATION = True
SMOOTHING_STRENGTH = 0.5
ENABLE_ZERO_FACE_PANNING = True
PAN_LEFT_BOUNDARY = 0.15
PAN_RIGHT_BOUNDARY = 0.85
PAN_CYCLE_DURATION = 8.0
# ================================================================

# Output formats supported by this module
FORMAT_VERTICAL_9_16 = "vertical_9x16"
# (Stacked formats are handled by MediaStacker, but Cropper provides 9:8 crops if needed)


class VideoCropper:
    def __init__(self):
        """Initialize video cropper"""
        pass

    def _get_face_detection_model(self):
        """Download and cache MediaPipe face detection model"""
        model_path = Path.home() / '.cache' / 'mediapipe' / 'blaze_face_short_range.tflite'
        model_path.parent.mkdir(parents=True, exist_ok=True)

        if not model_path.exists():
            print("[INFO] Downloading MediaPipe face detection model...")
            url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            urllib.request.urlretrieve(url, model_path)
            print("[INFO] Model downloaded successfully")

        with open(model_path, 'rb') as f:
            return f.read()

    def _bezier_interpolate(self, points: List[Tuple[float, float]], num_samples: int, smoothness: float = 0.5) -> List[Tuple[float, float]]:
        """Interpolate between points using Catmull-Rom to Bezier conversion for smooth curves"""
        if len(points) < 2:
            return points

        times = np.array([p[0] for p in points])
        values = np.array([p[1] for p in points])

        t_min, t_max = times[0], times[-1]
        interp_times = np.linspace(t_min, t_max, num_samples)

        from scipy import interpolate
        cs = interpolate.CubicSpline(times, values, bc_type='natural')
        interp_values = cs(interp_times)

        if smoothness > 0.3:
            from scipy.ndimage import gaussian_filter1d
            sigma = smoothness * 2
            interp_values = gaussian_filter1d(interp_values, sigma=sigma)

        return list(zip(interp_times, interp_values))

    def _generate_panning_positions(self, duration: float, fps: float, width: int, crop_width: int) -> List[Tuple[float, float]]:
        """Generate smooth panning positions for zero-face segments"""
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

    def _get_face_positions_timeline(self, video_path: str, check_every_n_frames: int = 8) -> Dict:
        """Get face positions throughout video as a timeline"""
        base_options = python.BaseOptions(model_asset_buffer=self._get_face_detection_model())
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

    def detect_face_segments(self, video_path: str, check_every_n_frames: int = 8) -> List[Dict]:
        """Detect faces throughout video and create segments with different face counts"""
        base_options = python.BaseOptions(model_asset_buffer=self._get_face_detection_model())
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

        segments = []
        current_segment = None

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
            face_positions = []
            min_face_size = int(height * 0.08)
            edge_margin = int(width * 0.05)

            if detection_result.detections:
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    x_min = int(bbox.origin_x)
                    y_min = int(bbox.origin_y)
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

                    face_positions.append({
                        'topLeft': {'x': x_min, 'y': y_min},
                        'rightBottom': {'x': x_min + w, 'y': y_min + h},
                        'width': w,
                        'height': h,
                        'confidence': confidence
                    })

            face_count = len(face_positions)
            if face_count == 2:
                w1, w2 = face_positions[0]['width'], face_positions[1]['width']
                if min(w1, w2) / max(w1, w2) < 0.5:
                    face_count = 1

            if current_segment is None or current_segment['face_count'] != face_count:
                if current_segment is not None:
                    current_segment['end_time'] = timestamp
                    current_segment['end_frame'] = frame_idx
                    segments.append(current_segment)
                current_segment = {
                    'face_count': face_count,
                    'start_time': timestamp,
                    'start_frame': frame_idx,
                    'faces': [face_positions] if face_positions else []
                }
            else:
                if face_positions:
                    current_segment['faces'].append(face_positions)

            frame_idx += check_every_n_frames

        if current_segment is not None:
            current_segment['end_time'] = total_frames / fps
            current_segment['end_frame'] = total_frames
            segments.append(current_segment)

        cap.release()
        return segments

    def detect_speaker_position(self, video_path: str, sample_frames: int = 10) -> Dict:
        """Detect speaker position in video by sampling frames"""
        base_options = python.BaseOptions(model_asset_buffer=self._get_face_detection_model())
        image_options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=0.5,
            min_suppression_threshold=0.3
        )
        image_detector = vision.FaceDetector.create_from_options(image_options)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame_indices = [int(total_frames * i / sample_frames) for i in range(sample_frames)]
        face_positions = []
        frames_with_two_faces = 0

        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = image_detector.detect(mp_image)

            frame_faces = []
            min_face_size = int(height * 0.08)
            edge_margin = int(width * 0.05)

            if detection_result.detections:
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    x_min, y_min, w, h = int(bbox.origin_x), int(bbox.origin_y), int(bbox.width), int(bbox.height)

                    if w < min_face_size or h < min_face_size:
                        continue
                    if (x_min + w // 2) < edge_margin or (x_min + w // 2) > width - edge_margin:
                        continue
                    if (detection.categories[0].score if detection.categories else 0.0) < 0.6:
                        continue
                    if (w/h if h > 0 else 0) < 0.6 or (w/h if h > 0 else 0) > 1.4:
                        continue

                    frame_faces.append({
                        'topLeft': {'x': x_min, 'y': y_min},
                        'rightBottom': {'x': x_min + w, 'y': y_min + h},
                        'width': w,
                        'height': h
                    })

            if len(frame_faces) == 2:
                if min(frame_faces[0]['width'], frame_faces[1]['width']) / max(frame_faces[0]['width'], frame_faces[1]['width']) >= 0.5:
                    frames_with_two_faces += 1
            if frame_faces:
                face_positions.append(frame_faces)

        cap.release()

        if frames_with_two_faces >= sample_frames * 0.9:
            return self._process_dual_face_crop(face_positions, width, height)

        all_faces = [face for frame_faces in face_positions for face in frame_faces]
        if all_faces:
            face_centers = sorted([(f['topLeft']['x'] + f['rightBottom']['x']) / 2 for f in all_faces])
            median_center_x = face_centers[len(face_centers)//2]
            crop_width = int(height * 9 / 16)
            crop_x = max(0, min(int(median_center_x - crop_width // 2), width - crop_width))
            return {'x': crop_x, 'y': 0, 'width': crop_width, 'height': height, 'face_detected': True, 'mode': 'single'}

        return self._get_default_crop_position(width, height)

    def _process_dual_face_crop(self, face_positions: List[List[Dict]], width: int, height: int) -> Dict:
        """Process dual-face detection for split-screen effect"""
        dual_face_frames = [f for f in face_positions if len(f) == 2]
        if not dual_face_frames:
            return self._get_default_crop_position(width, height)

        def calculate_face_crop(faces):
            tl_x = sum(f['topLeft']['x'] for f in faces) / len(faces)
            tl_y = sum(f['topLeft']['y'] for f in faces) / len(faces)
            rb_x = sum(f['rightBottom']['x'] for f in faces) / len(faces)
            rb_y = sum(f['rightBottom']['y'] for f in faces) / len(faces)
            w = sum(f['width'] for f in faces) / len(faces)
            h = sum(f['height'] for f in faces) / len(faces)
            box_lt_x = int(tl_x - w)
            box_lt_y = int(tl_y - h/2)
            box_rb_x = int(rb_x + w)
            box_rb_y = int(rb_y + h*0.75)
            return {'center_x': (tl_x + rb_x) / 2, 'box_lt_y': box_lt_y, 'box_width': box_rb_x - box_lt_x, 'box_height': box_rb_y - box_lt_y}

        left_faces, right_faces = [], []
        for frame in dual_face_frames:
            sorted_faces = sorted(frame, key=lambda f: f['topLeft']['x'])
            left_faces.append(sorted_faces[0])
            right_faces.append(sorted_faces[1])

        l_crop, r_crop = calculate_face_crop(left_faces), calculate_face_crop(right_faces)
        final_w = (l_crop['box_width'] + r_crop['box_width']) // 2
        final_h = int(final_w * 8 / 9)
        final_w = min(width, final_w)
        final_h = min(height, final_h)

        l_x = max(0, min(int(l_crop['center_x'] - final_w // 2), width - final_w))
        l_y = max(0, min(l_crop['box_lt_y'], height - final_h))
        r_x = max(0, min(int(r_crop['center_x'] - final_w // 2), width - final_w))
        r_y = max(0, min(r_crop['box_lt_y'], height - final_h))

        return {
            'mode': 'dual', 'face_detected': True,
            'left_face': {'x': l_x, 'y': l_y, 'width': final_w, 'height': final_h},
            'right_face': {'x': r_x, 'y': r_y, 'width': final_w, 'height': final_h},
            'scale_width': 1080, 'scale_height': 960, 'output_width': 1080, 'output_height': 1920
        }

    def _get_default_crop_position(self, width: int, height: int, position: str = "left") -> Dict:
        """Get default crop position (e.g. center)"""
        crop_height = height
        crop_width = int(crop_height * 9 / 16)
        if position == "left":
            crop_x = width // 4 - crop_width // 2
        elif position == "right":
            crop_x = (width * 3 // 4) - crop_width // 2
        else:
            crop_x = (width - crop_width) // 2
        crop_x = max(0, min(crop_x, width - crop_width))
        return {'x': crop_x, 'y': 0, 'width': crop_width, 'height': crop_height, 'face_detected': False, 'position': position, 'mode': 'single'}

    def convert_to_reels(self, video_path: str, output_path: str = None, auto_detect: bool = True, dynamic_mode: bool = True, output_format: str = None, **kwargs) -> Dict:
        """Main entry point for converting video to reels format"""
        v_path = Path(video_path)
        o_path = Path(output_path) if output_path else v_path.parent / f"{v_path.stem}_reels.mp4"
        
        # Format stacked is ignored here as it's handled by MediaStacker
        if dynamic_mode and auto_detect:
            segments = self.detect_face_segments(str(v_path), FACE_CHECK_INTERVAL_FRAMES)
            if any(s['face_count'] == 2 for s in segments):
                return self._convert_to_reels_dynamic(v_path, o_path)
            elif USE_SMOOTH_INTERPOLATION:
                return self._convert_to_reels_smooth(v_path, o_path)
            else:
                return self._convert_to_reels_dynamic(v_path, o_path)

        crop_params = self.detect_speaker_position(str(v_path)) if auto_detect else self._get_default_crop_position(*cv2.VideoCapture(str(v_path)).read()[1].shape[1::-1])
        return self._convert_dual_face_reels(v_path, o_path, crop_params) if crop_params.get('mode') == 'dual' else self._convert_single_face_reels(v_path, o_path, crop_params)

    def _convert_single_face_reels(self, video_path: Path, output_path: Path, crop_params: Dict) -> Dict:
        vf = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']},scale=1080:1920"
        cmd = ['ffmpeg', '-i', str(video_path), '-vf', vf, '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return {'success': True, 'output_path': str(output_path), 'crop_params': crop_params, 'mode': 'single'}

    def _convert_dual_face_reels(self, video_path: Path, output_path: Path, crop_params: Dict) -> Dict:
        l, r = crop_params['left_face'], crop_params['right_face']
        sw, sh = crop_params['scale_width'], crop_params['scale_height']
        vf = (f"[0:v]split=2[left][right];"
              f"[left]crop={l['width']}:{l['height']}:{l['x']}:{l['y']},scale={sw}:{sh}[ls];"
              f"[right]crop={r['width']}:{r['height']}:{r['x']}:{r['y']},scale={sw}:{sh}[rs];"
              f"[ls][rs]vstack")
        cmd = ['ffmpeg', '-i', str(video_path), '-filter_complex', vf, '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return {'success': True, 'output_path': str(output_path), 'crop_params': crop_params, 'mode': 'dual'}

    def _convert_to_reels_smooth(self, video_path: Path, output_path: Path) -> Dict:
        timeline = self._get_face_positions_timeline(str(video_path), FACE_CHECK_INTERVAL_FRAMES)
        pos, fps, w, h, frames = timeline['positions'], timeline['fps'], timeline['width'], timeline['height'], timeline['total_frames']
        c_h, c_w = h, int(h * 9 / 16)
        is_zero = len(pos) == 2 and pos[0][1] == w // 2 and pos[1][1] == w // 2
        
        if is_zero and ENABLE_ZERO_FACE_PANNING:
            smooth_pos = self._generate_panning_positions(frames/fps, fps, w, c_w)
        else:
            smooth_pos = self._bezier_interpolate(pos, frames, SMOOTHING_STRENGTH)

        # Process the points into a balanced tree to bypass FFMPEG nesting depth limits
        fixed_pos = []
        for t, f_x in smooth_pos:
            c_x = int(f_x - c_w // 2) if not is_zero else int(f_x)
            fixed_pos.append((t, c_x + c_w//2))  # The helper builder subtracts c_w//2, so we add it back here

        tree_expr = self._build_balanced_ffmpeg_expr(fixed_pos, fps, w, c_w)
        vf = f"crop=w={c_w}:h={c_h}:x='{tree_expr}':y=0,scale=1080:1920"
        
        cmd = ['ffmpeg', '-i', str(video_path), '-vf', vf, '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return {'success': True, 'output_path': str(output_path), 'mode': 'smooth'}
    def _convert_to_reels_dynamic(self, video_path: Path, output_path: Path) -> Dict:
        """Dynamic conversion by splitting into segments based on face count"""
        cap = cv2.VideoCapture(str(video_path))
        w, h, fps = int(cap.get(3)), int(cap.get(4)), cap.get(5)
        cap.release()
        segments = self._merge_segments(self.detect_face_segments(str(video_path), FACE_CHECK_INTERVAL_FRAMES))
        
        if not segments:
            return self._convert_single_face_reels(video_path, output_path, self._get_default_crop_position(w, h, "center"))
        
        import tempfile, shutil
        t_dir = Path(tempfile.mkdtemp())
        s_files = []
        try:
            a_path = t_dir / "audio.aac"
            subprocess.run(['ffmpeg', '-i', str(video_path), '-vn', '-acodec', 'copy', '-y', str(a_path)], check=True, capture_output=True)
            for i, seg in enumerate(segments):
                s_raw = t_dir / f"seg_{i}_raw.mp4"
                subprocess.run(['ffmpeg', '-i', str(video_path), '-ss', str(seg['start_time']), '-to', str(seg['end_time']), '-c:v', 'libx264', '-an', '-preset', 'ultrafast', '-y', str(s_raw)], check=True, capture_output=True)
                s_proc = t_dir / f"seg_{i}_proc.mp4"
                if seg['face_count'] == 2 and len(seg['faces']) > 0:
                    cp = self._process_dual_face_crop(seg['faces'], w, h)
                    l, r, sw, sh = cp['left_face'], cp['right_face'], cp['scale_width'], cp['scale_height']
                    vf = f"[0:v]split=2[l][r];[l]crop={l['width']}:{l['height']}:{l['x']}:{l['y']},scale={sw}:{sh}[ls];[r]crop={r['width']}:{r['height']}:{r['x']}:{r['y']},scale={sw}:{sh}[rs];[ls][rs]vstack"
                else:
                    cp = self._get_default_crop_position(w, h, "center")
                    vf = f"crop={cp['width']}:{cp['height']}:{cp['x']}:0,scale=1080:1920"
                subprocess.run(['ffmpeg', '-i', str(s_raw), '-vf', vf, '-c:v', 'libx264', '-an', '-preset', 'medium', '-crf', '23', '-y', str(s_proc)], check=True, capture_output=True)
                s_files.append(s_proc)
            
            c_list = t_dir / "list.txt"
            with open(c_list, 'w') as f:
                for sf in s_files: f.write(f"file '{sf}'\n")
            v_only = t_dir / "v_only.mp4"
            subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(c_list), '-c', 'copy', '-y', str(v_only)], check=True, capture_output=True)
            subprocess.run(['ffmpeg', '-i', str(v_only), '-i', str(a_path), '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-y', str(output_path)], check=True, capture_output=True)
            return {'success': True, 'output_path': str(output_path), 'mode': 'dynamic'}
        finally: shutil.rmtree(t_dir, ignore_errors=True)

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        if not segments: return []
        filtered = []
        for i, seg in enumerate(segments):
            if seg['end_time'] - seg['start_time'] >= 1.0 or i == len(segments) - 1:
                filtered.append(seg)
            elif filtered:
                filtered[-1]['end_time'] = seg['end_time']
                if 'faces' in seg: filtered[-1]['faces'].extend(seg['faces'])
        if not filtered: return []
        merged = []
        curr = filtered[0].copy()
        for seg in filtered[1:]:
            if seg['face_count'] == curr['face_count']:
                curr['end_time'] = seg['end_time']
                if 'faces' in seg: curr['faces'].extend(seg['faces'])
            else:
                merged.append(curr)
                curr = seg.copy()
        merged.append(curr)
        return merged

    # ──────────────────────────────────────────────────────────────────────────
    # MULTI-FACE TRACKING HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _get_multi_face_timeline(self, video_path: str, check_every_n_frames: int = 8) -> Dict:
        """Get ALL faces throughout video as a timeline"""
        base_options = python.BaseOptions(model_asset_buffer=self._get_face_detection_model())
        video_options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_detection_confidence=0.5,
            min_suppression_threshold=0.3
        )
        video_detector = vision.FaceDetector.create_from_options(video_options)

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        timeline = []
        min_face_size = int(height * 0.08)
        edge_margin = int(width * 0.05)

        for frame_idx in range(0, total_frames, check_every_n_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret: break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int((frame_idx / fps) * 1000)
            res = video_detector.detect_for_video(mp_image, ts_ms)
            
            t = frame_idx / fps
            valid_faces = []
            if res.detections:
                for d in res.detections:
                    bbox = d.bounding_box
                    w, h = int(bbox.width), int(bbox.height)
                    if w < min_face_size or h < min_face_size: continue
                    fc = int(bbox.origin_x) + w//2
                    if fc < edge_margin or fc > width - edge_margin: continue
                    conf = d.categories[0].score if d.categories else 0
                    if conf < 0.6: continue
                    ratio = w/h if h>0 else 0
                    if ratio < 0.6 or ratio > 1.4: continue
                    valid_faces.append({'x': fc, 'w': w})
            
            if valid_faces:
                # Find the maximum face width in this frame
                max_w = max(f['w'] for f in valid_faces)
                
                # Filter out background noise faces (must be at least half the size of the main face)
                filtered_faces = [f for f in valid_faces if f['w'] >= max_w * 0.5]
                
                # Sort horizontally
                filtered_faces.sort(key=lambda f: f['x'])
                
                # Merge duplicate detections referring to the identical person (< 10% screen width apart)
                merged_x = []
                for f in filtered_faces:
                    if not merged_x or (f['x'] - merged_x[-1] > width * 0.1):
                        merged_x.append(f['x'])
                
                if merged_x:
                    timeline.append((t, merged_x))

        cap.release()
        return {'timeline': timeline, 'fps': fps, 'width': width, 'total_frames': total_frames}

    def _build_balanced_ffmpeg_expr(self, smooth_pos, fps, width, crop_width) -> str:
        """Builds a mathematically balanced log(N) O-depth FFmpeg tree to bypass parsing limits."""
        sample_int = int(fps)
        segments = []
        
        for i, idx in enumerate(range(0, len(smooth_pos), sample_int)):
            t, f_x = smooth_pos[idx]
            f_num = int(t * fps)
            c_x = int(f_x - crop_width // 2)
            c_x = max(0, min(c_x, width - crop_width))

            next_idx = idx + sample_int
            if next_idx < len(smooth_pos):
                n_t, n_f_x = smooth_pos[next_idx]
                n_f = int(n_t * fps)
                n_c_x = int(n_f_x - crop_width // 2)
                n_c_x = max(0, min(n_c_x, width - crop_width))
                if n_f > f_num:
                    expr = f"{c_x}+(n-{f_num})*({n_c_x}-{c_x})/{n_f - f_num}"
                    segments.append((f_num, n_f, expr))
            else:
                segments.append((f_num, float('inf'), str(c_x)))
                
        if not segments:
            return "0"

        # Recursively construct balanced tree
        def build_tree(segs):
            if len(segs) == 1: return segs[0][2]
            mid = len(segs) // 2
            return f"if(lt(n,{segs[mid][0]}),{build_tree(segs[:mid])},{build_tree(segs[mid:])})"
            
        first_frame = segments[0][0]
        first_val = segments[0][2].split('+')[0] if '+' in segments[0][2] else segments[0][2]
        
        tree = build_tree(segments)
        if first_frame > 0:
            return f"if(lt(n,{first_frame}),{first_val},{tree})"
        return tree

    def _build_expr(self, smooth_pos, fps, width, crop_width):
        return self._build_balanced_ffmpeg_expr(smooth_pos, fps, width, crop_width)

    # ──────────────────────────────────────────────────────────────────────────
    # 9:8 CROPPING  — face-tracked crop to 9:8 (half of 9:16)
    # ──────────────────────────────────────────────────────────────────────────

    def crop_to_9x8(self, video_path: str, output_path: str = None) -> Dict:
        """
        Crop video to 9:8 aspect ratio with smooth face tracking.
        Used as the building block for the stacked photo/video reel formats.

        Input:
            video_path: Source video (any aspect ratio)
            output_path: Destination for the 9:8 crop (default: <stem>_9x8.mp4)

        Output:
            dict with 'success' and 'output_path'
            The output video is scaled to 1080x960 (one half of a 9:16 reel).
        """
        v_path = Path(video_path)
        o_path = Path(output_path) if output_path else v_path.parent / f"{v_path.stem}_9x8.mp4"

        try:
            # Get video properties
            cap = cv2.VideoCapture(str(v_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            cap.release()

            # Target box: 1080x960 (9:8 half of a 9:16 reel)
            box_width = 1080
            box_height = 960

            # Source crop dimensions in 9:8 ratio
            crop_height = height
            crop_width = int(crop_height * 9 / 8)

            if crop_width > width:
                print(f"[DEBUG] crop_to_9x8: Input is narrower than 9:8. Falling back to center crop.")
                crop_width = width
                crop_height = int(crop_width * 8 / 9)
                crop_x = 0
                crop_y = (height - crop_height) // 2
                
                vf = f"crop=w={crop_width}:h={crop_height}:x={crop_x}:y={crop_y},scale={box_width}:{box_height}"
                cmd = [
                    'ffmpeg', '-i', str(v_path),
                    '-vf', vf,
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-preset', 'medium', '-crf', '23', '-y',
                    str(o_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"[DEBUG] crop_to_9x8 complete (fallback portrait): {box_width}x{box_height} → {o_path}")
                return {'success': True, 'output_path': str(o_path)}

            # Detect multi-face timeline
            multi_data = self._get_multi_face_timeline(str(v_path), FACE_CHECK_INTERVAL_FRAMES)
            timeline = multi_data['timeline']
            
            # Smooth face counts over time
            raw_counts = [len(fx) for t, fx in timeline]
            smoothed_counts = []
            
            # Rolling window to smooth out momentary flicker
            for i in range(len(raw_counts)):
                start = max(0, i - 5)
                end = min(len(raw_counts), i + 6)
                sub = raw_counts[start:end]
                
                # Get mode (most frequent value)
                mode = max(set(sub), key=sub.count) if sub else 1
                if mode == 0: mode = 1
                smoothed_counts.append(mode)
                
            smoothed_counts = [max(1, min(3, c)) for c in smoothed_counts]
            max_overall = max(smoothed_counts) if smoothed_counts else 1
            print(f"[DEBUG] crop_to_9x8: Dynamically switching up to {max_overall} layouts.")

            # Helper to generate FFmpeg enable expression for dynamic overlay switching
            def get_enable_expr(target):
                segments = []
                start_t = None
                for i, c in enumerate(smoothed_counts):
                    t = timeline[i][0]
                    if c == target and start_t is None: 
                        start_t = t
                    elif c != target and start_t is not None:
                        segments.append((start_t, t))
                        start_t = None
                if start_t is not None:
                    segments.append((start_t, duration))
                if not segments: return "0"
                return "+".join([f"between(t,{s:.3f},{e:.3f})" for s, e in segments])

            # Helper to generate smooth continuous tracks for a target layout
            def get_tracks(n_faces):
                trks = [[] for _ in range(n_faces)]
                l_k = [width/(n_faces+1) * (i+1) for i in range(n_faces)]
                if not timeline:
                    for i in range(n_faces): trks[i] = [(0.0, l_k[i]), (duration, l_k[i])]
                    return [self._bezier_interpolate(tr, total_frames, SMOOTHING_STRENGTH) for tr in trks]
                
                for i_t, (t, fx) in enumerate(timeline):
                    if smoothed_counts[i_t] != n_faces:
                        for i in range(n_faces): trks[i].append((t, l_k[i]))
                        continue
                    unassigned = list(fx)
                    for i in range(n_faces):
                        if not unassigned: trks[i].append((t, l_k[i]))
                        else:
                            bf = min(unassigned, key=lambda f: abs(f - l_k[i]))
                            trks[i].append((t, bf))
                            l_k[i] = bf
                            unassigned.remove(bf)
                
                if trks[0][0][0] > 0:
                    for i in range(n_faces): trks[i].insert(0, (0.0, trks[i][0][1]))
                if trks[0][-1][0] < duration:
                    for i in range(n_faces): trks[i].append((duration, trks[i][-1][1]))
                return [self._bezier_interpolate(tr, total_frames, SMOOTHING_STRENGTH) for tr in trks]

            vf_parts = []
            
            # --- BUILD FFMPEG GRAPH ---
            if max_overall == 1:
                # Video only ever contains 1 person
                t1 = get_tracks(1)
                e1 = self._build_expr(t1[0], fps, width, crop_width)
                vf = f"crop=w={crop_width}:h={crop_height}:x='{e1}':y=0,scale={box_width}:{box_height}"
                cmd = [
                    'ffmpeg', '-i', str(v_path),
                    '-vf', vf,
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-preset', 'medium', '-crf', '23', '-y',
                    str(o_path)
                ]
            else:
                # Video switches dynamically between 1-3 people
                out_splits = "".join([f"[v{i}]" for i in range(max_overall)])
                vf_parts.append(f"[0:v]split={max_overall}{out_splits};")
                
                # Base Mode 1 (Always running in background)
                t1 = get_tracks(1)
                e1 = self._build_expr(t1[0], fps, width, crop_width)
                vf_parts.append(f"[v0]crop=w={crop_width}:h={crop_height}:x='{e1}':y=0,scale={box_width}:{box_height}[out1];")
                
                # Optional Mode 2
                if max_overall >= 2:
                    t2 = get_tracks(2)
                    s2 = crop_width // 2
                    e2_0, e2_1 = self._build_expr(t2[0], fps, width, s2), self._build_expr(t2[1], fps, width, s2)
                    vf_parts.append(f"[v1]split=2[v1a][v1b];")
                    vf_parts.append(f"[v1a]crop=w={s2}:h={crop_height}:x='{e2_0}':y=0[p2_0];")
                    vf_parts.append(f"[v1b]crop=w={s2}:h={crop_height}:x='{e2_1}':y=0[p2_1];")
                    vf_parts.append(f"[p2_0][p2_1]hstack=inputs=2,scale={box_width}:{box_height}[out2];")
                
                # Optional Mode 3
                if max_overall == 3:
                    t3 = get_tracks(3)
                    s3 = crop_width // 3
                    e3_0, e3_1, e3_2 = self._build_expr(t3[0], fps, width, s3), self._build_expr(t3[1], fps, width, s3), self._build_expr(t3[2], fps, width, s3)
                    vf_parts.append(f"[v2]split=3[v2a][v2b][v2c];")
                    vf_parts.append(f"[v2a]crop=w={s3}:h={crop_height}:x='{e3_0}':y=0[p3_0];")
                    vf_parts.append(f"[v2b]crop=w={s3}:h={crop_height}:x='{e3_1}':y=0[p3_1];")
                    vf_parts.append(f"[v2c]crop=w={s3}:h={crop_height}:x='{e3_2}':y=0[p3_2];")
                    vf_parts.append(f"[p3_0][p3_1][p3_2]hstack=inputs=3,scale={box_width}:{box_height}[out3];")
                
                # Seamless Overlays based on temporal expression
                if max_overall == 2:
                    en2 = get_enable_expr(2)
                    vf_parts.append(f"[out1][out2]overlay=enable='{en2}'[final]")
                elif max_overall == 3:
                    en2 = get_enable_expr(2)
                    en3 = get_enable_expr(3)
                    vf_parts.append(f"[out1][out2]overlay=enable='{en2}'[temp];")
                    vf_parts.append(f"[temp][out3]overlay=enable='{en3}'[final]")
                
                vf = "".join(vf_parts)
                cmd = [
                    'ffmpeg', '-i', str(v_path),
                    '-filter_complex', vf,
                    '-map', '[final]', '-map', '0:a?',
                    '-c:v', 'libx264', '-c:a', 'aac',
                    '-preset', 'medium', '-crf', '23', '-y',
                    str(o_path)
                ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] crop_to_9x8 complete: {box_width}x{box_height} → {o_path}")
            return {'success': True, 'output_path': str(o_path)}

        except subprocess.CalledProcessError as e:
            err = e.stderr.decode() if e.stderr else str(e)
            return {'success': False, 'error': f"crop_to_9x8 failed: {err}"}
        except Exception as e:
            return {'success': False, 'error': f"crop_to_9x8 failed: {str(e)}"}

    # ──────────────────────────────────────────────────────────────────────────
    # STACKING — combine two 9:8 clips into a single 9:16 reel
    # ──────────────────────────────────────────────────────────────────────────

    def stack_videos(self, top_path: str, bottom_path: str, output_path: str) -> Dict:
        """
        Stack two 9:8 videos/images vertically to produce a 9:16 (1080x1920) output.

        Input:
            top_path:    Path to top 9:8 clip (1080x960) — e.g. AI photo/video
            bottom_path: Path to bottom 9:8 clip (1080x960) — e.g. face-tracked highlight
            output_path: Destination for the stacked 9:16 video

        Output:
            dict with 'success' and 'output_path'
            Both inputs are re-scaled to 1080x960 before stacking, so mismatched
            sizes are handled gracefully.
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', str(top_path),
                '-i', str(bottom_path),
                '-filter_complex',
                '[0:v]scale=1080:960[top];[1:v]scale=1080:960[bot];[top][bot]vstack[out]',
                '-map', '[out]',
                '-map', '1:a?',          # audio from bottom clip (optional)
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] stack_videos complete: 1080x1920 → {output_path}")
            return {'success': True, 'output_path': str(output_path)}

        except subprocess.CalledProcessError as e:
            err = e.stderr.decode() if e.stderr else str(e)
            return {'success': False, 'error': f"stack_videos failed: {err}"}
        except Exception as e:
            return {'success': False, 'error': f"stack_videos failed: {str(e)}"}
