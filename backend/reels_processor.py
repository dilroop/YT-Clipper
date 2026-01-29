"""
Reels Processor Module
Converts videos to reels format (9:16) with speaker auto-focus
Uses MediaPipe FaceDetector for intelligent cropping (faster, more accurate than Haar Cascade)
"""

import cv2
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np


# ==================== FACE TRACKING SETTINGS ====================
# These control how frequently the face position is checked and crop is updated

# How often to check for faces (in frames)
# Lower values = more accurate tracking but slower preprocessing
# 4 frames @ 30fps = ~0.13s between checks
# Try: 4 (0.13s), 8 (0.27s), 15 (0.5s)
FACE_CHECK_INTERVAL_FRAMES = 4

# Smooth motion interpolation (uses Bezier curves)
# When enabled, creates smooth crop motion between detected positions
# No segments = no audio clicks, smooth camera movement
USE_SMOOTH_INTERPOLATION = True

# Smoothing strength for Bezier curves (0.0-1.0)
# Lower = follows face closely, Higher = smoother but slower response
# 0.3 = responsive, 0.5 = balanced, 0.7 = very smooth
SMOOTHING_STRENGTH = 0.5

# Zero-face panning settings (when no faces detected)
# Instead of static crop, pan smoothly left-to-right and back
ENABLE_ZERO_FACE_PANNING = True

# Panning boundaries (percentage of video width)
# 0.15 = start at 15% from left edge, 0.85 = stop at 85%
# This hides the left 0-15% and right 85-100% edges
PAN_LEFT_BOUNDARY = 0.15   # Start panning from this % of width
PAN_RIGHT_BOUNDARY = 0.85  # Pan up to this % of width

# Panning speed (seconds for one complete left-to-right pan)
# Lower = faster panning, Higher = slower, more cinematic
# 8.0 = completes one pan in 8 seconds (good for podcasts)
# 12.0 = slower, more dramatic
PAN_CYCLE_DURATION = 8.0

# ================================================================

# ==================== OUTPUT FORMAT OPTIONS ====================
# Format 1: Standard 9:16 vertical with all tracking modes
FORMAT_VERTICAL_9_16 = "vertical_9x16"

# Format 2: Stacked 9:8 boxes (TOP: AI-animated photo, BOTTOM: tracked highlight)
FORMAT_STACKED_PHOTO = "stacked_photo"

# Format 3: Stacked 9:8 boxes (TOP: AI-generated video, BOTTOM: tracked highlight)
FORMAT_STACKED_VIDEO = "stacked_video"
# ================================================================


class ReelsProcessor:
    def __init__(self):
        """Initialize reels processor with MediaPipe face detection"""
        # MediaPipe detectors are created on-demand in each method
        # to avoid timestamp conflicts between sequential and non-sequential processing
        pass

    def _get_face_detection_model(self):
        """Download and cache MediaPipe face detection model"""
        import urllib.request
        import os

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
        """
        Interpolate between points using Catmull-Rom to Bezier conversion for smooth curves

        Args:
            points: List of (time, value) tuples
            num_samples: Number of interpolated points to generate
            smoothness: 0.0-1.0, controls curve smoothness

        Returns:
            List of interpolated (time, value) tuples
        """
        if len(points) < 2:
            return points

        # Extract times and values
        times = np.array([p[0] for p in points])
        values = np.array([p[1] for p in points])

        # Create interpolation times
        t_min, t_max = times[0], times[-1]
        interp_times = np.linspace(t_min, t_max, num_samples)

        # Use cubic interpolation with smoothing
        from scipy import interpolate

        # Catmull-Rom spline (smooth curve through points)
        # Adjust tension based on smoothness (0 = tight, 1 = loose)
        tension = smoothness

        # Create cubic spline
        cs = interpolate.CubicSpline(times, values, bc_type='natural')
        interp_values = cs(interp_times)

        # Apply smoothing filter for extra smoothness
        if smoothness > 0.3:
            from scipy.ndimage import gaussian_filter1d
            sigma = smoothness * 2
            interp_values = gaussian_filter1d(interp_values, sigma=sigma)

        return list(zip(interp_times, interp_values))

    def _generate_panning_positions(self, duration: float, fps: float, width: int, crop_width: int) -> List[Tuple[float, float]]:
        """
        Generate smooth panning positions for zero-face segments
        Pans left-to-right and back using sine wave for smooth motion

        Args:
            duration: Segment duration in seconds
            fps: Frames per second
            width: Video width in pixels
            crop_width: Width of crop window

        Returns:
            List of (time, x_position) tuples
        """
        import math

        # Calculate boundary positions in pixels
        left_boundary_px = int(width * PAN_LEFT_BOUNDARY)
        right_boundary_px = int(width * PAN_RIGHT_BOUNDARY) - crop_width

        # Ensure boundaries are valid
        right_boundary_px = max(left_boundary_px, min(right_boundary_px, width - crop_width))

        # Center position
        center_x = (left_boundary_px + right_boundary_px) / 2
        amplitude = (right_boundary_px - left_boundary_px) / 2

        # Generate positions using sine wave for smooth panning
        num_frames = int(duration * fps)
        positions = []

        for frame in range(num_frames):
            time = frame / fps

            # Sine wave oscillation: -1 to 1 over PAN_CYCLE_DURATION seconds
            # Frequency: 1 / PAN_CYCLE_DURATION (completes one full cycle in PAN_CYCLE_DURATION seconds)
            angle = (2 * math.pi * time) / PAN_CYCLE_DURATION

            # Map sine wave to panning range
            # sin(-π/2) = -1 (left), sin(π/2) = 1 (right)
            x_position = center_x + amplitude * math.sin(angle - math.pi / 2)

            # Clamp to boundaries
            x_position = max(left_boundary_px, min(x_position, right_boundary_px))

            positions.append((time, x_position))

        print(f"[DEBUG] Generated panning motion: {left_boundary_px}px to {right_boundary_px}px over {PAN_CYCLE_DURATION}s cycles")

        return positions

    def _get_face_positions_timeline(self, video_path: str, check_every_n_frames: int = 8) -> Dict:
        """
        Get face positions throughout video as a timeline (for smooth interpolation)

        Args:
            video_path: Path to video
            check_every_n_frames: Check faces every N frames

        Returns:
            Dict with timeline data: {
                'positions': [(time, x_center), ...],
                'fps': float,
                'width': int,
                'height': int
            }
        """
        # Create fresh VIDEO-mode detector
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
        print(f"[DEBUG] Detecting face positions every {check_every_n_frames} frames...")

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

            # Get single best face position
            best_face_x = None
            if detection_result.detections:
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    x_min = int(bbox.origin_x)
                    w = int(bbox.width)
                    h = int(bbox.height)

                    # Apply filters
                    if w < min_face_size or h < min_face_size:
                        continue
                    face_center_x = x_min + w // 2
                    if face_center_x < edge_margin or face_center_x > width - edge_margin:
                        continue

                    # Filter by confidence score
                    confidence = detection.categories[0].score if detection.categories else 0.0
                    if confidence < 0.6:
                        continue

                    # Filter by aspect ratio (faces are roughly square)
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio < 0.6 or aspect_ratio > 1.4:
                        continue

                    # Take first valid face
                    best_face_x = face_center_x
                    break

            if best_face_x is not None:
                positions.append((timestamp, best_face_x))

            frame_idx += check_every_n_frames

        cap.release()

        print(f"[DEBUG] Detected {len(positions)} face positions")

        # If no faces detected, use center
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
        """
        Detect faces throughout video and create segments with different face counts

        Args:
            video_path: Path to video
            check_every_n_frames: Check faces every N frames (default: 8)

        Returns:
            List of segments with face count and timestamps
        """
        # Create fresh VIDEO-mode detector for sequential frame processing
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

        # Get video properties
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

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Detect faces with MediaPipe FaceDetector
            timestamp_ms = int((frame_idx / fps) * 1000)  # Convert to milliseconds
            detection_result = video_detector.detect_for_video(mp_image, timestamp_ms)

            timestamp = frame_idx / fps

            # Extract face positions from detections
            face_positions = []
            min_face_size = int(height * 0.08)  # Face must be at least 8% of frame height
            edge_margin = int(width * 0.05)  # 5% margin from edges

            if detection_result.detections:
                for detection in detection_result.detections:
                    # Get bounding box
                    bbox = detection.bounding_box
                    x_min = int(bbox.origin_x)
                    y_min = int(bbox.origin_y)
                    w = int(bbox.width)
                    h = int(bbox.height)
                    x_max = x_min + w
                    y_max = y_min + h

                    # Filter out very small detections (likely logos, text, or noise)
                    if w < min_face_size or h < min_face_size:
                        continue

                    # Filter out detections too close to edges (likely background objects)
                    face_center_x = x_min + w // 2
                    if face_center_x < edge_margin or face_center_x > width - edge_margin:
                        continue

                    # Filter by confidence score (reduce false positives)
                    confidence = detection.categories[0].score if detection.categories else 0.0
                    if confidence < 0.6:  # Require at least 60% confidence
                        continue

                    # Filter by aspect ratio (real faces are roughly square, not wide rectangles)
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio < 0.6 or aspect_ratio > 1.4:  # Face should be 0.6-1.4 ratio
                        continue

                    # MediaPipe FaceDetector with enhanced filtering
                    # Filters: size, edge, confidence, aspect ratio

                    face_positions.append({
                        'topLeft': {'x': x_min, 'y': y_min},
                        'rightBottom': {'x': x_max, 'y': y_max},
                        'width': w,
                        'height': h,
                        'confidence': detection.categories[0].score if detection.categories else 0.0
                    })

            # Validate face count - if 2 faces, check if sizes are similar
            # This filters out false detections (microphone, hands, etc.)
            face_count = len(face_positions)
            if face_count == 2:
                face1_width = face_positions[0]['width']
                face2_width = face_positions[1]['width']
                size_ratio = min(face1_width, face2_width) / max(face1_width, face2_width)

                # If sizes are too different (< 50% ratio), treat as single face
                if size_ratio < 0.5:
                    face_count = 1

            # Start new segment or continue current one
            if current_segment is None or current_segment['face_count'] != face_count:
                # Save previous segment
                if current_segment is not None:
                    current_segment['end_time'] = timestamp
                    current_segment['end_frame'] = frame_idx
                    segments.append(current_segment)

                # Start new segment
                current_segment = {
                    'face_count': face_count,
                    'start_time': timestamp,
                    'start_frame': frame_idx,
                    'faces': [face_positions] if face_positions else []
                }
            else:
                # Add face positions to current segment
                if face_positions:
                    current_segment['faces'].append(face_positions)

            frame_idx += check_every_n_frames

        # Close last segment
        if current_segment is not None:
            current_segment['end_time'] = total_frames / fps
            current_segment['end_frame'] = total_frames
            segments.append(current_segment)

        cap.release()

        print(f"[DEBUG] Detected {len(segments)} segments:")
        for i, seg in enumerate(segments):
            duration = seg['end_time'] - seg['start_time']
            print(f"  Segment {i+1}: {seg['face_count']} faces, {seg['start_time']:.1f}s - {seg['end_time']:.1f}s ({duration:.1f}s)")

        return segments

    def detect_speaker_position(self, video_path: str, sample_frames: int = 10) -> Dict:
        """
        Detect speaker position in video by sampling frames
        Supports dual-face split-screen for 2-person conversations

        Args:
            video_path: Path to video
            sample_frames: Number of frames to sample for detection

        Returns:
            dict with crop parameters (x, y, width, height) or dual_faces list
        """
        # Create IMAGE-mode detector for non-sequential frame sampling
        base_options = python.BaseOptions(model_asset_buffer=self._get_face_detection_model())
        image_options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,  # Use IMAGE mode for sampling
            min_detection_confidence=0.5,
            min_suppression_threshold=0.3
        )
        image_detector = vision.FaceDetector.create_from_options(image_options)

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise Exception(f"Cannot open video: {video_path}")

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Sample frames evenly throughout video
        frame_indices = [int(total_frames * i / sample_frames) for i in range(sample_frames)]

        face_positions = []
        frames_with_two_faces = 0

        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if not ret:
                continue

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Detect faces with MediaPipe FaceDetector (IMAGE mode)
            detection_result = image_detector.detect(mp_image)

            # Store face positions using corner points
            frame_faces = []
            min_face_size = int(height * 0.08)
            edge_margin = int(width * 0.05)

            if detection_result.detections:
                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    x_min = int(bbox.origin_x)
                    y_min = int(bbox.origin_y)
                    w = int(bbox.width)
                    h = int(bbox.height)
                    x_max = x_min + w
                    y_max = y_min + h

                    # Apply same filters as other detection methods
                    if w < min_face_size or h < min_face_size:
                        continue

                    face_center_x = x_min + w // 2
                    if face_center_x < edge_margin or face_center_x > width - edge_margin:
                        continue

                    # Filter by confidence score
                    confidence = detection.categories[0].score if detection.categories else 0.0
                    if confidence < 0.6:
                        continue

                    # Filter by aspect ratio (faces are roughly square)
                    aspect_ratio = w / h if h > 0 else 0
                    if aspect_ratio < 0.6 or aspect_ratio > 1.4:
                        continue

                    frame_faces.append({
                        'topLeft': {'x': x_min, 'y': y_min},
                        'rightBottom': {'x': x_max, 'y': y_max},
                        'width': w,
                        'height': h
                    })

            # Track when we detect exactly 2 valid faces (similar sizes)
            if len(frame_faces) == 2:
                face1_width = frame_faces[0]['width']
                face2_width = frame_faces[1]['width']
                size_ratio = min(face1_width, face2_width) / max(face1_width, face2_width)

                # Both faces should be within reasonable size of each other (at least 50% ratio)
                if size_ratio >= 0.5:
                    frames_with_two_faces += 1

            if frame_faces:
                face_positions.append(frame_faces)

        cap.release()

        # Check if we consistently detect 2 faces throughout the video
        # Use a high threshold (90%) to avoid dual mode when video transitions from 2 to 1 person
        # This ensures dual mode is only used when BOTH people are present for nearly the entire clip
        dual_face_threshold = sample_frames * 0.9
        if frames_with_two_faces >= dual_face_threshold:
            # Process for dual-face split screen
            print(f"[DEBUG] Dual-face mode: {frames_with_two_faces}/{sample_frames} frames have 2 faces")
            return self._process_dual_face_crop(face_positions, width, height)
        else:
            print(f"[DEBUG] Single-face mode: Only {frames_with_two_faces}/{sample_frames} frames have 2 faces (need {int(dual_face_threshold)}+ for dual mode)")

        # Single face or no consistent dual-face detection
        # Use median face position for better centering (more robust than average)
        all_faces = [face for frame_faces in face_positions for face in frame_faces]

        if all_faces:
            # Calculate median face center for horizontal positioning
            face_centers = sorted([(f['topLeft']['x'] + f['rightBottom']['x']) / 2 for f in all_faces])

            # Use median center position
            if len(face_centers) % 2 == 0:
                median_center_x = (face_centers[len(face_centers)//2 - 1] + face_centers[len(face_centers)//2]) / 2
            else:
                median_center_x = face_centers[len(face_centers)//2]

            # Calculate crop parameters for 9:16 aspect ratio
            target_aspect = 9 / 16  # width / height for reels
            crop_height = height
            crop_width = int(crop_height * target_aspect)

            # Center crop horizontally around detected face
            crop_x = int(median_center_x - crop_width // 2)

            # Ensure crop stays within video bounds
            crop_x = max(0, min(crop_x, width - crop_width))

            return {
                'x': crop_x,
                'y': 0,
                'width': crop_width,
                'height': crop_height,
                'face_detected': True,
                'mode': 'single'
            }
        else:
            # No face detected - use Joe Rogan style default positions
            return self._get_default_crop_position(width, height)

    def _process_dual_face_crop(self, face_positions: List[List[Dict]], width: int, height: int) -> Dict:
        """
        Process dual-face detection for split-screen effect
        Creates two 9:8 crops stacked vertically to make 9:16
        Face should occupy 40% of the 9:8 box and be centered

        Args:
            face_positions: List of frames, each containing list of face dicts
            width: Video width
            height: Video height

        Returns:
            Crop parameters for dual-face mode
        """
        # Filter to frames with exactly 2 faces
        dual_face_frames = [frame for frame in face_positions if len(frame) == 2]

        if not dual_face_frames:
            # Fallback to single face if we don't have dual-face data
            return self._get_default_crop_position(width, height)

        # Filter out false detections - both faces should be similar in size
        # If one face is less than 50% the width of the other, it's likely a false detection
        valid_dual_face_frames = []
        for frame in dual_face_frames:
            face1_width = frame[0]['width']
            face2_width = frame[1]['width']
            size_ratio = min(face1_width, face2_width) / max(face1_width, face2_width)

            # Both faces should be within reasonable size of each other (at least 50% ratio)
            if size_ratio >= 0.5:
                valid_dual_face_frames.append(frame)

        # If we don't have enough valid dual-face frames after filtering, use single-face mode
        if len(valid_dual_face_frames) < len(dual_face_frames) * 0.5:
            print(f"[DEBUG] Filtered out {len(dual_face_frames) - len(valid_dual_face_frames)} frames with mismatched face sizes")
            print(f"[DEBUG] Only {len(valid_dual_face_frames)}/{len(dual_face_frames)} frames have valid dual faces - using single-face mode")
            return self._get_default_crop_position(width, height)

        dual_face_frames = valid_dual_face_frames

        # Helper function to calculate average face and apply padding
        def calculate_face_crop(faces):
            # Average the corners
            tl_x = sum(f['topLeft']['x'] for f in faces) / len(faces)
            tl_y = sum(f['topLeft']['y'] for f in faces) / len(faces)
            rb_x = sum(f['rightBottom']['x'] for f in faces) / len(faces)
            rb_y = sum(f['rightBottom']['y'] for f in faces) / len(faces)
            width = sum(f['width'] for f in faces) / len(faces)
            height = sum(f['height'] for f in faces) / len(faces)

            # Apply padding: Box.LT = Face.LT - (width, height/2)
            #                Box.RB = Face.RB + (width, height*0.75)
            box_lt_x = int(tl_x - width)
            box_lt_y = int(tl_y - (height / 2))
            box_rb_x = int(rb_x + width)
            box_rb_y = int(rb_y + (height * 0.75))

            return {
                'box_lt_x': box_lt_x,
                'box_lt_y': box_lt_y,
                'box_width': box_rb_x - box_lt_x,
                'box_height': box_rb_y - box_lt_y,
                'center_x': (tl_x + rb_x) / 2,
                'avg_width': width,
                'avg_height': height
            }

        # Separate left and right faces
        left_faces = []
        right_faces = []
        for frame in dual_face_frames:
            sorted_faces = sorted(frame, key=lambda f: f['topLeft']['x'])
            left_faces.append(sorted_faces[0])
            right_faces.append(sorted_faces[1])

        # Calculate crop boxes for both faces
        left = calculate_face_crop(left_faces)
        right = calculate_face_crop(right_faces)

        # Use average box width, conform to 9:8 ratio
        avg_box_width = (left['box_width'] + right['box_width']) // 2
        final_crop_width = avg_box_width
        final_crop_height = int(final_crop_width * 8 / 9)

        # Adjust if height exceeds width (maintain proper aspect)
        if final_crop_height > final_crop_width:
            final_crop_width = int(final_crop_height * 9 / 8)

        # Ensure crop doesn't exceed video dimensions
        if final_crop_width > width:
            final_crop_width = width
            final_crop_height = int(final_crop_width * 8 / 9)
        if final_crop_height > height:
            final_crop_height = height
            final_crop_width = int(final_crop_height * 9 / 8)

        # Calculate final crop positions (centered horizontally, top anchored)
        left_crop_x = int(left['center_x'] - final_crop_width // 2)
        left_crop_y = left['box_lt_y']

        right_crop_x = int(right['center_x'] - final_crop_width // 2)
        right_crop_y = right['box_lt_y']

        # Clamp to video boundaries for FFmpeg processing
        left_crop_x = max(0, min(left_crop_x, width - final_crop_width))
        left_crop_y = max(0, min(left_crop_y, height - final_crop_height))

        right_crop_x = max(0, min(right_crop_x, width - final_crop_width))
        right_crop_y = max(0, min(right_crop_y, height - final_crop_height))

        # Scaling to target output (1080x1920)
        target_output_width = 1080
        target_output_height = int(target_output_width * 8 / 9)
        scale_factor = target_output_width / final_crop_width

        print(f"[DEBUG] Dual-face crop: {final_crop_width}x{final_crop_height} (ratio={final_crop_width/final_crop_height:.3f})")
        print(f"[DEBUG] Scale: {final_crop_width}x{final_crop_height} -> {target_output_width}x{target_output_height} ({scale_factor:.2f}x)")
        print(f"[DEBUG] Left face: {left['avg_width']:.0f}px = {(left['avg_width']/final_crop_width)*100:.1f}% of crop")
        print(f"[DEBUG] Right face: {right['avg_width']:.0f}px = {(right['avg_width']/final_crop_width)*100:.1f}% of crop")

        return {
            'mode': 'dual',
            'face_detected': True,
            'left_face': {
                'x': left_crop_x,
                'y': left_crop_y,
                'width': final_crop_width,
                'height': final_crop_height
            },
            'right_face': {
                'x': right_crop_x,
                'y': right_crop_y,
                'width': final_crop_width,
                'height': final_crop_height
            },
            'scale_width': target_output_width,
            'scale_height': target_output_height,
            'output_width': target_output_width,
            'output_height': target_output_height * 2
        }

    def _get_default_crop_position(self, width: int, height: int, position: str = "left") -> Dict:
        """
        Get default crop position (Joe Rogan style - fixed positions)

        Args:
            width: Video width
            height: Video height
            position: "left", "center", or "right"

        Returns:
            Crop parameters
        """
        # Calculate 9:16 crop dimensions
        crop_height = height
        crop_width = int(crop_height * 9 / 16)

        if position == "left":
            # Focus on left speaker (common in podcasts)
            crop_x = width // 4 - crop_width // 2
        elif position == "right":
            # Focus on right speaker
            crop_x = (width * 3 // 4) - crop_width // 2
        else:  # center
            crop_x = (width - crop_width) // 2

        # Ensure within bounds
        crop_x = max(0, min(crop_x, width - crop_width))

        return {
            'x': crop_x,
            'y': 0,
            'width': crop_width,
            'height': crop_height,
            'face_detected': False,
            'position': position,
            'mode': 'single'
        }

    def convert_to_reels(
        self,
        video_path: str,
        output_path: str = None,
        auto_detect: bool = True,
        dynamic_mode: bool = True,
        output_format: str = None,
        ai_content_path: str = None,
        caption_text: str = None
    ) -> Dict:
        """
        Convert video to reels format with smart cropping
        Supports single-face and dual-face split-screen modes
        Can dynamically switch between modes based on face detection

        Args:
            video_path: Path to input video
            output_path: Optional output path
            auto_detect: Use face detection for cropping
            dynamic_mode: Enable dynamic mode switching (check faces every 8 frames)
            output_format: Format type (FORMAT_VERTICAL_9_16, FORMAT_STACKED_PHOTO, FORMAT_STACKED_VIDEO)
            ai_content_path: Path to AI-generated content (photo/video) for stacked formats
            caption_text: Optional caption text to overlay at the end

        Returns:
            dict with result
        """
        video_path = Path(video_path)

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_reels.mp4"
        else:
            output_path = Path(output_path)

        # Default to vertical 9:16 format
        if output_format is None:
            output_format = FORMAT_VERTICAL_9_16

        # Route to appropriate conversion method based on format
        if output_format == FORMAT_STACKED_PHOTO:
            return self._convert_to_stacked_format(
                video_path, output_path,
                ai_content_type="photo",
                ai_content_path=ai_content_path,
                caption_text=caption_text
            )
        elif output_format == FORMAT_STACKED_VIDEO:
            return self._convert_to_stacked_format(
                video_path, output_path,
                ai_content_type="video",
                ai_content_path=ai_content_path,
                caption_text=caption_text
            )

        # FORMAT_VERTICAL_9_16 - existing logic
        # If dynamic mode is enabled, check for dual-face segments
        if dynamic_mode and auto_detect:
            # Quick check: detect segments to see if we have dual-face segments
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            segments = self.detect_face_segments(str(video_path), check_every_n_frames=FACE_CHECK_INTERVAL_FRAMES)
            has_dual_face_segments = any(seg['face_count'] == 2 for seg in segments)

            if has_dual_face_segments:
                # Hybrid mode: Use dynamic conversion with smooth interpolation for single-face segments
                print("[DEBUG] Detected dual-face segments - using hybrid mode (dual-face static + single-face smooth)")
                return self._convert_to_reels_dynamic(video_path, output_path)
            elif USE_SMOOTH_INTERPOLATION:
                # Pure smooth mode: No dual-face segments, use full smooth interpolation
                print("[DEBUG] No dual-face segments - using pure smooth interpolation mode")
                return self._convert_to_reels_smooth(video_path, output_path)
            else:
                # Legacy segment-based without smooth interpolation
                return self._convert_to_reels_dynamic(video_path, output_path)

        # Otherwise use the original static mode detection
        # Detect speaker position(s)
        if auto_detect:
            crop_params = self.detect_speaker_position(str(video_path))
        else:
            # Get video dimensions for default crop
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            crop_params = self._get_default_crop_position(width, height, "center")

        # Check if dual-face mode
        if crop_params.get('mode') == 'dual':
            return self._convert_dual_face_reels(video_path, output_path, crop_params)
        else:
            return self._convert_single_face_reels(video_path, output_path, crop_params)

    def _convert_single_face_reels(self, video_path: Path, output_path: Path, crop_params: Dict) -> Dict:
        """Convert to reels with single face crop (original behavior)"""
        # Build ffmpeg crop filter
        crop_filter = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}"

        # Scale to standard reels resolution
        scale_filter = "scale=1080:1920"

        # Combine filters
        vf_filter = f"{crop_filter},{scale_filter}"

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', vf_filter,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': str(output_path),
                'crop_params': crop_params,
                'mode': 'single'
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error converting to reels: {e.stderr.decode()}"
            }

    def _convert_dual_face_reels(self, video_path: Path, output_path: Path, crop_params: Dict) -> Dict:
        """Convert to reels with dual-face split-screen"""
        left = crop_params['left_face']
        right = crop_params['right_face']
        scale_w = crop_params.get('scale_width')
        scale_h = crop_params.get('scale_height')

        # Create complex filter for dual split-screen:
        # 1. Split input into 2 streams
        # 2. Crop left face from first stream
        # 3. Scale left crop to target dimensions
        # 4. Crop right face from second stream
        # 5. Scale right crop to target dimensions
        # 6. Stack them vertically (should now be 1080x1920)

        if scale_w and scale_h:
            # Scale each crop to target dimensions before stacking
            vf_filter = (
                f"[0:v]split=2[left][right];"
                f"[left]crop={left['width']}:{left['height']}:{left['x']}:{left['y']}[left_crop];"
                f"[left_crop]scale={scale_w}:{scale_h}[left_scaled];"
                f"[right]crop={right['width']}:{right['height']}:{right['x']}:{right['y']}[right_crop];"
                f"[right_crop]scale={scale_w}:{scale_h}[right_scaled];"
                f"[left_scaled][right_scaled]vstack"
            )
        else:
            # No scaling needed, just crop and stack, then scale final
            vf_filter = (
                f"[0:v]split=2[left][right];"
                f"[left]crop={left['width']}:{left['height']}:{left['x']}:{left['y']}[left_crop];"
                f"[right]crop={right['width']}:{right['height']}:{right['x']}:{right['y']}[right_crop];"
                f"[left_crop][right_crop]vstack[stacked];"
                f"[stacked]scale=1080:1920"
            )

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-filter_complex', vf_filter,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': str(output_path),
                'crop_params': crop_params,
                'mode': 'dual'
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error converting to dual-face reels: {e.stderr.decode()}"
            }

    def _convert_to_reels_smooth(self, video_path: Path, output_path: Path) -> Dict:
        """
        Convert to reels with smooth Bezier curve-based face tracking
        No segments = no audio clicks, smooth camera movement

        Args:
            video_path: Path to input video
            output_path: Path for output

        Returns:
            dict with result
        """
        try:
            print(f"[DEBUG] Using smooth interpolation mode (Bezier curves)")

            # Get face position timeline
            timeline = self._get_face_positions_timeline(str(video_path), FACE_CHECK_INTERVAL_FRAMES)
            positions = timeline['positions']
            fps = timeline['fps']
            width = timeline['width']
            height = timeline['height']
            total_frames = timeline['total_frames']

            # Calculate crop dimensions (9:16 aspect ratio)
            crop_height = height
            crop_width = int(crop_height * 9 / 16)

            # Check if faces were actually detected or if we're using fallback center positions
            # Fallback positions are exactly 2 points at start/end with center x-coordinate
            is_zero_face = (len(positions) == 2 and
                           positions[0][1] == width // 2 and
                           positions[1][1] == width // 2)

            if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                # No faces detected - use smooth panning instead
                print(f"[DEBUG] No faces detected - using smooth panning (left-right motion)")
                video_duration = total_frames / fps
                smooth_positions = self._generate_panning_positions(video_duration, fps, width, crop_width)
                print(f"[DEBUG] Generated {len(smooth_positions)} panning positions")
            else:
                # Interpolate face positions using Bezier curves
                num_samples = total_frames  # One position per frame for ultra-smooth motion
                print(f"[DEBUG] Interpolating {len(positions)} keyframes to {num_samples} frames using Bezier curves")
                smooth_positions = self._bezier_interpolate(positions, num_samples, SMOOTHING_STRENGTH)

            # Generate crop positions for each frame
            crop_x_values = []
            for _, x_pos in smooth_positions:
                if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                    # Panning mode - x_pos is already the crop position
                    crop_x = int(x_pos)
                else:
                    # Face tracking mode - x_pos is face center, need to center crop on it
                    crop_x = int(x_pos - crop_width // 2)

                # Clamp to video bounds
                crop_x = max(0, min(crop_x, width - crop_width))
                crop_x_values.append(crop_x)

            # Use zoompan filter for smooth motion
            # Create expression that interpolates between positions
            print(f"[DEBUG] Generating smooth crop filter...")

            # For smooth motion, we'll use crop with a custom expression
            # Generate a file with crop coordinates per frame
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())

            # Create a simple approach: generate segments with linear interpolation
            # FFmpeg zoompan doesn't support per-frame coordinates easily
            # So we'll use crop with expressions based on frame number

            # Alternative: Use crop with setpts and expressions
            # Build expression from interpolated data

            # Simplest approach: Use overlay with moving crop
            # But for now, let's use crop with frame-based expression

            # Generate crop command with smooth transitions
            # We'll create a zoompan-like effect using crop + scale

            # Actually, let's write a file with timestamps and use sendcmd
            cmd_file = temp_dir / "crop_commands.txt"
            with open(cmd_file, 'w') as f:
                # Generate commands for key positions only (not all frames)
                step = max(1, len(smooth_positions) // 100)  # Max 100 commands
                for i in range(0, len(smooth_positions), step):
                    time, face_x = smooth_positions[i]
                    crop_x = int(face_x - crop_width // 2)
                    crop_x = max(0, min(crop_x, width - crop_width))
                    # sendcmd format: time filter command
                    f.write(f"{time} crop x {crop_x}\n")

            # Actually, sendcmd is complex. Let's use a simpler approach:
            # Pre-crop with padding, then use zoompan to follow interpolated positions

            # Simplest working solution: Use crop with changing x based on frame number
            # We'll create a piecewise linear expression

            # Generate FFmpeg expression for crop x-coordinate
            # Format: if(gte(n,frame1),x1,if(gte(n,frame2),x2,...))

            # For simplicity, let's sample positions and create smooth transitions
            sample_interval = fps  # One sample per second
            sampled_indices = range(0, len(smooth_positions), int(sample_interval))

            # Build expression for smooth crop x position
            expr_parts = []
            for i, idx in enumerate(sampled_indices):
                if idx >= len(smooth_positions):
                    break
                time, face_x = smooth_positions[idx]
                frame_num = int(time * fps)
                crop_x = int(face_x - crop_width // 2)
                crop_x = max(0, min(crop_x, width - crop_width))

                if i == 0:
                    expr_parts.append(f"if(lt(n,{frame_num}),{crop_x}")
                else:
                    # Linear interpolation between current and next
                    if i < len(list(sampled_indices)) - 1:
                        next_idx = list(sampled_indices)[i + 1]
                        if next_idx < len(smooth_positions):
                            next_time, next_face_x = smooth_positions[min(next_idx, len(smooth_positions)-1)]
                            next_frame = int(next_time * fps)
                            next_crop_x = int(next_face_x - crop_width // 2)
                            next_crop_x = max(0, min(next_crop_x, width - crop_width))

                            # Linear interpolation formula
                            expr_parts.append(f",if(lt(n,{next_frame}),{crop_x}+(n-{frame_num})*({next_crop_x}-{crop_x})/{next_frame-frame_num}")
                    else:
                        expr_parts.append(f",{crop_x}")

            # Close all if statements
            expr_parts.append(")" * (len(expr_parts) - 1))
            crop_x_expr = "".join(expr_parts)

            # Build ffmpeg command with smooth crop
            vf_filter = f"crop=w={crop_width}:h={crop_height}:x='{crop_x_expr}':y=0,scale=1080:1920"

            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', vf_filter,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(output_path)
            ]

            print(f"[DEBUG] Running single-pass conversion with smooth motion...")
            subprocess.run(cmd, check=True, capture_output=True)

            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"[DEBUG] Smooth conversion complete: {output_path}")

            return {
                'success': True,
                'output_path': str(output_path),
                'mode': 'smooth',
                'keyframes': len(positions)
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error in smooth conversion: {e.stderr.decode()}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error in smooth conversion: {str(e)}"
            }

    def _convert_to_reels_dynamic(self, video_path: Path, output_path: Path) -> Dict:
        """
        Convert to reels with dynamic mode switching based on face detection
        Checks faces every 8 frames and switches between dual/single mode as needed

        Args:
            video_path: Path to input video
            output_path: Path for output

        Returns:
            dict with result
        """
        try:
            import tempfile
            import shutil

            # Get video dimensions and fps
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            # Detect face segments using configured interval
            print(f"[DEBUG] Detecting face segments (checking every {FACE_CHECK_INTERVAL_FRAMES} frames)...")
            segments = self.detect_face_segments(str(video_path), check_every_n_frames=FACE_CHECK_INTERVAL_FRAMES)

            if not segments:
                # No segments detected, fall back to simple single mode
                print("[DEBUG] No segments detected, using default single-face mode")
                crop_params = self._get_default_crop_position(width, height, "center")
                return self._convert_single_face_reels(video_path, output_path, crop_params)

            # Merge consecutive segments with same face count to reduce jitter
            merged_segments = self._merge_segments(segments)
            print(f"[DEBUG] Merged into {len(merged_segments)} segments")

            # Skip segment splitting when smooth interpolation is enabled
            # Smooth interpolation handles motion within segments, so no need to split
            if not USE_SMOOTH_INTERPOLATION:
                # Split long single-face segments for better face tracking (legacy mode)
                max_duration = 2.0  # 2 seconds per segment
                merged_segments = self._split_long_single_face_segments(merged_segments, max_duration=max_duration)
                print(f"[DEBUG] After splitting: {len(merged_segments)} segments")

            # If only one segment, use simple conversion
            if len(merged_segments) == 1:
                seg = merged_segments[0]
                if seg['face_count'] == 2:
                    print("[DEBUG] Single segment with 2 faces, using dual mode")
                    crop_params = self._process_dual_face_crop(seg['faces'], width, height)
                    return self._convert_dual_face_reels(video_path, output_path, crop_params)
                else:
                    print("[DEBUG] Single segment with single/no face, using single mode")
                    crop_params = self._get_default_crop_position(width, height, "center")
                    return self._convert_single_face_reels(video_path, output_path, crop_params)

            # Multiple segments - need to process each and concatenate
            print(f"[DEBUG] Processing {len(merged_segments)} segments with mode switching")
            temp_dir = Path(tempfile.mkdtemp())
            segment_files = []

            try:
                # Extract original audio ONCE (keep it untouched to avoid clicks)
                print(f"[DEBUG] Extracting original audio...")
                audio_path = temp_dir / "original_audio.aac"
                audio_cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-vn',  # No video
                    '-acodec', 'copy',  # Copy audio without re-encoding
                    '-y',
                    str(audio_path)
                ]
                subprocess.run(audio_cmd, check=True, capture_output=True)

                # Process each segment (VIDEO ONLY, no audio)
                for i, seg in enumerate(merged_segments):
                    print(f"[DEBUG] Processing segment {i+1}/{len(merged_segments)}: "
                          f"{seg['face_count']} faces, {seg['start_time']:.1f}s-{seg['end_time']:.1f}s")

                    # Extract segment from original video (VIDEO ONLY)
                    segment_path = temp_dir / f"segment_{i:03d}_raw.mp4"
                    extract_cmd = [
                        'ffmpeg',
                        '-i', str(video_path),
                        '-ss', str(seg['start_time']),
                        '-to', str(seg['end_time']),
                        '-c:v', 'libx264',
                        '-an',  # No audio
                        '-preset', 'ultrafast',
                        '-y',
                        str(segment_path)
                    ]
                    subprocess.run(extract_cmd, check=True, capture_output=True)

                    # Determine crop parameters for this segment
                    if seg['face_count'] == 2 and len(seg['faces']) > 0:
                        # Dual-face mode
                        crop_params = self._process_dual_face_crop(seg['faces'], width, height)
                        processed_path = temp_dir / f"segment_{i:03d}_processed.mp4"

                        # Apply dual-face crop with scaling
                        left = crop_params['left_face']
                        right = crop_params['right_face']
                        scale_w = crop_params.get('scale_width')
                        scale_h = crop_params.get('scale_height')

                        if scale_w and scale_h:
                            # Scale each crop to target dimensions before stacking
                            vf_filter = (
                                f"[0:v]split=2[left][right];"
                                f"[left]crop={left['width']}:{left['height']}:{left['x']}:{left['y']}[left_crop];"
                                f"[left_crop]scale={scale_w}:{scale_h}[left_scaled];"
                                f"[right]crop={right['width']}:{right['height']}:{right['x']}:{right['y']}[right_crop];"
                                f"[right_crop]scale={scale_w}:{scale_h}[right_scaled];"
                                f"[left_scaled][right_scaled]vstack"
                            )
                        else:
                            # No scaling, just crop and stack then scale final
                            vf_filter = (
                                f"[0:v]split=2[left][right];"
                                f"[left]crop={left['width']}:{left['height']}:{left['x']}:{left['y']}[left_crop];"
                                f"[right]crop={right['width']}:{right['height']}:{right['x']}:{right['y']}[right_crop];"
                                f"[left_crop][right_crop]vstack[stacked];"
                                f"[stacked]scale=1080:1920"
                            )

                        process_cmd = [
                            'ffmpeg',
                            '-i', str(segment_path),
                            '-filter_complex', vf_filter,
                            '-c:v', 'libx264',
                            '-an',  # No audio (will add back later)
                            '-preset', 'medium',
                            '-crf', '23',
                            '-y',
                            str(processed_path)
                        ]
                    else:
                        # Single-face or no-face mode - use SMOOTH INTERPOLATION
                        processed_path = temp_dir / f"segment_{i:03d}_processed.mp4"

                        if seg['face_count'] == 1 and len(seg['faces']) > 0 and USE_SMOOTH_INTERPOLATION:
                            # Apply smooth Bezier interpolation within this segment
                            print(f"[DEBUG]   Applying smooth interpolation to single-face segment...")

                            # Extract face positions with timestamps (relative to segment start)
                            positions = []
                            frames_in_segment = len(seg['faces'])
                            segment_duration = seg['end_time'] - seg['start_time']

                            for frame_idx, frame_faces in enumerate(seg['faces']):
                                if frame_faces:
                                    # Get first face center
                                    face = frame_faces[0]
                                    face_center_x = (face['topLeft']['x'] + face['rightBottom']['x']) / 2
                                    timestamp = (frame_idx / frames_in_segment) * segment_duration
                                    positions.append((timestamp, face_center_x))

                            if len(positions) >= 2:
                                # Get segment frame count
                                segment_frame_count = int((seg['end_time'] - seg['start_time']) * fps)

                                # Interpolate using Bezier curves
                                smooth_positions = self._bezier_interpolate(positions, segment_frame_count, SMOOTHING_STRENGTH)

                                # Calculate crop dimensions
                                target_aspect = 9 / 16
                                crop_height = height
                                crop_width = int(crop_height * target_aspect)

                                # Generate FFmpeg expression for smooth crop
                                # Limit to max 30 keyframes to avoid overly complex expressions
                                max_keyframes = 30
                                sample_interval = max(1, len(smooth_positions) // max_keyframes)

                                sampled_positions = smooth_positions[::sample_interval]
                                if len(sampled_positions) > max_keyframes:
                                    sampled_positions = sampled_positions[:max_keyframes]

                                # Build simpler expression with linear interpolation
                                # Format: lerp(a, b, (n-start)/(end-start))
                                expr_parts = []
                                for i in range(len(sampled_positions)):
                                    time, face_x = sampled_positions[i]
                                    # Frame number relative to segment (starts at 0)
                                    frame_num = int((i / len(sampled_positions)) * segment_frame_count)
                                    crop_x = int(face_x - crop_width // 2)
                                    crop_x = max(0, min(crop_x, width - crop_width))

                                    if i == 0:
                                        expr_parts.append(f"if(lt(n,{frame_num}),{crop_x}")
                                    elif i < len(sampled_positions) - 1:
                                        next_time, next_face_x = sampled_positions[i + 1]
                                        next_frame = int(((i + 1) / len(sampled_positions)) * segment_frame_count)
                                        next_crop_x = int(next_face_x - crop_width // 2)
                                        next_crop_x = max(0, min(next_crop_x, width - crop_width))

                                        # Linear interpolation: a + (n-start)*(b-a)/(end-start)
                                        if next_frame > frame_num:
                                            expr_parts.append(f",if(lt(n,{next_frame}),{crop_x}+(n-{frame_num})*({next_crop_x}-{crop_x})/{next_frame-frame_num}")
                                        else:
                                            expr_parts.append(f",{crop_x}")
                                    else:
                                        # Last frame
                                        expr_parts.append(f",{crop_x}")

                                # Close all if statements (one less than parts count)
                                expr_parts.append(")" * (len(sampled_positions) - 1))
                                crop_x_expr = "".join(expr_parts)

                                print(f"[DEBUG]   Generated expression with {len(sampled_positions)} keyframes")
                                vf_filter = f"crop=w={crop_width}:h={crop_height}:x='{crop_x_expr}':y=0,scale=1080:1920"
                            else:
                                # Not enough positions, fall back to static crop
                                all_faces = [face for frame_faces in seg['faces'] for face in frame_faces]
                                face_centers = sorted([(f['topLeft']['x'] + f['rightBottom']['x']) / 2 for f in all_faces])
                                median_center_x = face_centers[len(face_centers)//2] if face_centers else width // 2

                                target_aspect = 9 / 16
                                crop_height = height
                                crop_width = int(crop_height * target_aspect)
                                crop_x = int(median_center_x - crop_width // 2)
                                crop_x = max(0, min(crop_x, width - crop_width))

                                crop_filter = f"crop={crop_width}:{crop_height}:{crop_x}:0"
                                vf_filter = f"{crop_filter},scale=1080:1920"
                        else:
                            # Zero-face segment or smooth interpolation disabled
                            # Check if this is actually a zero-face segment
                            if seg['face_count'] == 0 and ENABLE_ZERO_FACE_PANNING and USE_SMOOTH_INTERPOLATION:
                                # Apply smooth panning for zero-face segments
                                print(f"[DEBUG]   Applying smooth panning to zero-face segment...")

                                segment_duration = seg['end_time'] - seg['start_time']
                                segment_frame_count = int(segment_duration * fps)

                                # Calculate crop dimensions
                                target_aspect = 9 / 16
                                crop_height = height
                                crop_width = int(crop_height * target_aspect)

                                # Generate panning positions
                                panning_positions = self._generate_panning_positions(
                                    segment_duration, fps, width, crop_width
                                )

                                # Use similar expression generation as smooth interpolation
                                max_keyframes = 30
                                sample_interval = max(1, len(panning_positions) // max_keyframes)
                                sampled_positions = panning_positions[::sample_interval]
                                if len(sampled_positions) > max_keyframes:
                                    sampled_positions = sampled_positions[:max_keyframes]

                                # Build FFmpeg expression with linear interpolation
                                expr_parts = []
                                for i in range(len(sampled_positions)):
                                    time, pan_x = sampled_positions[i]
                                    frame_num = int((i / len(sampled_positions)) * segment_frame_count)
                                    crop_x = int(pan_x)
                                    crop_x = max(0, min(crop_x, width - crop_width))

                                    if i == 0:
                                        expr_parts.append(f"if(lt(n,{frame_num}),{crop_x}")
                                    elif i < len(sampled_positions) - 1:
                                        next_time, next_pan_x = sampled_positions[i + 1]
                                        next_frame = int(((i + 1) / len(sampled_positions)) * segment_frame_count)
                                        next_crop_x = int(next_pan_x)
                                        next_crop_x = max(0, min(next_crop_x, width - crop_width))

                                        if next_frame > frame_num:
                                            expr_parts.append(f",if(lt(n,{next_frame}),{crop_x}+(n-{frame_num})*({next_crop_x}-{crop_x})/{next_frame-frame_num}")
                                        else:
                                            expr_parts.append(f",{crop_x}")
                                    else:
                                        expr_parts.append(f",{crop_x}")

                                expr_parts.append(")" * (len(sampled_positions) - 1))
                                crop_x_expr = "".join(expr_parts)

                                print(f"[DEBUG]   Generated panning expression with {len(sampled_positions)} keyframes")
                                vf_filter = f"crop=w={crop_width}:h={crop_height}:x='{crop_x_expr}':y=0,scale=1080:1920"
                            else:
                                # Smooth interpolation disabled or other case - use default center crop
                                crop_params = self._get_default_crop_position(width, height, "center")
                                crop_filter = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}"
                                vf_filter = f"{crop_filter},scale=1080:1920"

                        process_cmd = [
                            'ffmpeg',
                            '-i', str(segment_path),
                            '-vf', vf_filter,
                            '-c:v', 'libx264',
                            '-an',  # No audio (will add back later)
                            '-preset', 'medium',
                            '-crf', '23',
                            '-y',
                            str(processed_path)
                        ]

                    subprocess.run(process_cmd, check=True, capture_output=True)
                    segment_files.append(processed_path)

                # Concatenate all video segments (no audio)
                print(f"[DEBUG] Concatenating {len(segment_files)} processed video segments")
                concat_list_path = temp_dir / "concat_list.txt"
                with open(concat_list_path, 'w') as f:
                    for seg_file in segment_files:
                        f.write(f"file '{seg_file}'\n")

                video_only_path = temp_dir / "video_only.mp4"
                concat_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_list_path),
                    '-c', 'copy',
                    '-y',
                    str(video_only_path)
                ]
                subprocess.run(concat_cmd, check=True, capture_output=True)

                # Add original audio back to concatenated video
                print(f"[DEBUG] Adding original audio to final video")
                merge_cmd = [
                    'ffmpeg',
                    '-i', str(video_only_path),
                    '-i', str(audio_path),
                    '-c:v', 'copy',  # Copy video (no re-encode)
                    '-c:a', 'aac',   # Encode audio to aac
                    '-shortest',     # Match shortest stream (video)
                    '-y',
                    str(output_path)
                ]
                subprocess.run(merge_cmd, check=True, capture_output=True)

                print(f"[DEBUG] Dynamic conversion complete: {output_path}")

                return {
                    'success': True,
                    'output_path': str(output_path),
                    'mode': 'dynamic',
                    'segments': len(merged_segments)
                }

            finally:
                # Cleanup temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error in dynamic conversion: {e.stderr.decode()}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error in dynamic conversion: {str(e)}"
            }

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge consecutive segments with same face count
        Also filters out very short segments (< 1 second) that are likely detection errors

        Args:
            segments: List of segments from detect_face_segments()

        Returns:
            Merged list of segments
        """
        if not segments:
            return []

        # First pass: filter out very short segments (< 1 second)
        # These are usually false detections
        min_segment_duration = 1.0
        filtered = []

        for i, seg in enumerate(segments):
            duration = seg['end_time'] - seg['start_time']

            # Keep segment if it's long enough OR if it's the last segment
            if duration >= min_segment_duration or i == len(segments) - 1:
                filtered.append(seg)
            else:
                # Very short segment - merge it with previous if possible
                if filtered:
                    # Extend the previous segment to cover this short one
                    filtered[-1]['end_time'] = seg['end_time']
                    filtered[-1]['end_frame'] = seg['end_frame']
                    if 'faces' in seg and 'faces' in filtered[-1]:
                        filtered[-1]['faces'].extend(seg['faces'])
                    print(f"[DEBUG] Filtered out short segment ({duration:.1f}s) with {seg['face_count']} faces at {seg['start_time']:.1f}s")
                else:
                    # First segment is short, keep it anyway
                    filtered.append(seg)

        # Second pass: merge consecutive segments with same face count
        merged = []
        current = filtered[0].copy()

        for seg in filtered[1:]:
            if seg['face_count'] == current['face_count']:
                # Merge with current segment
                current['end_time'] = seg['end_time']
                current['end_frame'] = seg['end_frame']
                if 'faces' in seg and 'faces' in current:
                    current['faces'].extend(seg['faces'])
            else:
                # Save current and start new segment
                merged.append(current)
                current = seg.copy()

        # Add the last segment
        merged.append(current)

        return merged

    def _split_long_single_face_segments(self, segments: List[Dict], max_duration: float = 2.0) -> List[Dict]:
        """
        Split long single-face segments into smaller chunks for better face tracking.
        Only splits single-face (count=1) segments that exceed max_duration.

        Duration is controlled by CROP_UPDATE_INTERVAL_FRAMES setting.
        Lower = smoother tracking but more segments (audio clicks)
        Higher = fewer segments but less responsive tracking

        Args:
            segments: List of merged segments
            max_duration: Maximum duration for single-face segments (seconds, default 2.0 = 60 frames at 30fps)

        Returns:
            List of segments with long single-face segments split
        """
        result = []

        for seg in segments:
            duration = seg['end_time'] - seg['start_time']

            # Only split single-face segments that are too long
            if seg['face_count'] == 1 and duration > max_duration and 'faces' in seg and len(seg['faces']) > 0:
                # Calculate how many chunks we need
                num_chunks = int(duration / max_duration) + 1
                chunk_duration = duration / num_chunks

                # Calculate faces per chunk
                total_face_frames = len(seg['faces'])
                faces_per_chunk = max(1, total_face_frames // num_chunks)

                print(f"[DEBUG] Splitting long single-face segment ({duration:.1f}s) into {num_chunks} chunks of ~{chunk_duration:.1f}s")

                # Create chunks
                for i in range(num_chunks):
                    chunk_start = seg['start_time'] + (i * chunk_duration)
                    chunk_end = seg['start_time'] + ((i + 1) * chunk_duration) if i < num_chunks - 1 else seg['end_time']

                    # Distribute faces to chunks
                    face_start_idx = i * faces_per_chunk
                    face_end_idx = (i + 1) * faces_per_chunk if i < num_chunks - 1 else total_face_frames
                    chunk_faces = seg['faces'][face_start_idx:face_end_idx]

                    chunk = {
                        'start_time': chunk_start,
                        'end_time': chunk_end,
                        'face_count': seg['face_count'],
                        'faces': chunk_faces
                    }
                    result.append(chunk)
            else:
                # Keep segment as-is (dual-face, short single-face, or no-face)
                result.append(seg)

        return result

    def _convert_to_stacked_format(
        self,
        video_path: Path,
        output_path: Path,
        ai_content_type: str,
        ai_content_path: str = None,
        caption_text: str = None
    ) -> Dict:
        """
        Convert to stacked 9:8 format with AI content on top and tracked highlight on bottom

        Args:
            video_path: Path to input video
            output_path: Path for output
            ai_content_type: "photo" or "video"
            ai_content_path: Path to AI-generated content (if None, uses placeholder)
            caption_text: Optional caption text to overlay

        Returns:
            dict with result
        """
        try:
            import tempfile
            import shutil

            print(f"[DEBUG] Converting to stacked {ai_content_type} format")

            temp_dir = Path(tempfile.mkdtemp())

            # Get video properties
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return {'success': False, 'error': f"Cannot open video: {video_path}"}

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            cap.release()

            # Calculate 9:8 dimensions
            # Final output is 1080x1920 (9:16)
            # Each 9:8 box is 1080x960
            box_width = 1080
            box_height = 960

            # Step 1: Create bottom box (tracked highlight)
            print(f"[DEBUG] Creating bottom 9:8 box with face tracking...")
            bottom_box_path = temp_dir / "bottom_box.mp4"

            # Use smooth interpolation for single-face tracking
            timeline = self._get_face_positions_timeline(str(video_path), FACE_CHECK_INTERVAL_FRAMES)
            positions = timeline['positions']

            # Calculate crop dimensions for 9:8 aspect ratio
            crop_height = height
            crop_width = int(crop_height * 9 / 8)

            # Check if faces were detected or using fallback
            is_zero_face = (len(positions) == 2 and
                           positions[0][1] == width // 2 and
                           positions[1][1] == width // 2)

            if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                # Use panning for zero-face
                print(f"[DEBUG] No faces detected - using smooth panning")
                smooth_positions = self._generate_panning_positions(duration, fps, width, crop_width)
            else:
                # Interpolate face positions
                print(f"[DEBUG] Interpolating {len(positions)} face positions")
                smooth_positions = self._bezier_interpolate(positions, total_frames, SMOOTHING_STRENGTH)

            # Generate crop expression
            crop_x_values = []
            for _, x_pos in smooth_positions:
                if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                    crop_x = int(x_pos)
                else:
                    crop_x = int(x_pos - crop_width // 2)
                crop_x = max(0, min(crop_x, width - crop_width))
                crop_x_values.append(crop_x)

            # Sample positions for FFmpeg expression
            sample_interval = fps
            sampled_indices = range(0, len(smooth_positions), int(sample_interval))

            expr_parts = []
            for i, idx in enumerate(sampled_indices):
                if idx >= len(smooth_positions):
                    break
                time, face_x = smooth_positions[idx]
                frame_num = int(time * fps)

                if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                    crop_x = int(face_x)
                else:
                    crop_x = int(face_x - crop_width // 2)
                crop_x = max(0, min(crop_x, width - crop_width))

                if i == 0:
                    expr_parts.append(f"if(lt(n,{frame_num}),{crop_x}")
                else:
                    if i < len(list(sampled_indices)) - 1:
                        next_idx = list(sampled_indices)[i + 1]
                        if next_idx < len(smooth_positions):
                            next_time, next_face_x = smooth_positions[min(next_idx, len(smooth_positions)-1)]
                            next_frame = int(next_time * fps)

                            if is_zero_face and ENABLE_ZERO_FACE_PANNING:
                                next_crop_x = int(next_face_x)
                            else:
                                next_crop_x = int(next_face_x - crop_width // 2)
                            next_crop_x = max(0, min(next_crop_x, width - crop_width))

                            expr_parts.append(f",if(lt(n,{next_frame}),{crop_x}+(n-{frame_num})*({next_crop_x}-{crop_x})/{next_frame-frame_num}")
                    else:
                        expr_parts.append(f",{crop_x}")

            expr_parts.append(")" * (len(expr_parts) - 1))
            crop_x_expr = "".join(expr_parts)

            # Create bottom box with tracking
            vf_filter = f"crop=w={crop_width}:h={crop_height}:x='{crop_x_expr}':y=0,scale={box_width}:{box_height}"

            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', vf_filter,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(bottom_box_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] Bottom box created: {box_width}x{box_height}")

            # Step 2: Create or load top box (AI content)
            print(f"[DEBUG] Creating top 9:8 box with {ai_content_type}...")
            top_box_path = temp_dir / f"top_box_{ai_content_type}.mp4"

            if ai_content_path and Path(ai_content_path).exists():
                # Use provided AI content
                print(f"[DEBUG] Using AI content from: {ai_content_path}")
                # Resize and trim to match duration
                cmd = [
                    'ffmpeg',
                    '-i', str(ai_content_path),
                    '-vf', f'scale={box_width}:{box_height}:force_original_aspect_ratio=decrease,pad={box_width}:{box_height}:(ow-iw)/2:(oh-ih)/2',
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-an',  # No audio for top box
                    '-preset', 'medium',
                    '-crf', '23',
                    '-y',
                    str(top_box_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                # Generate placeholder
                if ai_content_type == "photo":
                    self._generate_ai_photo_placeholder(box_width, box_height, duration, fps, top_box_path)
                else:  # video
                    self._generate_ai_video_placeholder(box_width, box_height, duration, fps, top_box_path)

            print(f"[DEBUG] Top box created: {box_width}x{box_height}")

            # Step 3: Stack boxes vertically
            print(f"[DEBUG] Stacking boxes vertically...")
            stacked_path = temp_dir / "stacked.mp4"

            # Use filter_complex to stack with audio from bottom
            vf_filter = "[0:v][1:v]vstack"

            cmd = [
                'ffmpeg',
                '-i', str(top_box_path),
                '-i', str(bottom_box_path),
                '-filter_complex', vf_filter,
                '-map', '[out]',  # This will be auto-named by vstack
                '-map', '1:a',  # Audio from bottom box (second input)
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(stacked_path)
            ]

            # Actually, vstack doesn't auto-name, let's fix the command
            cmd = [
                'ffmpeg',
                '-i', str(top_box_path),
                '-i', str(bottom_box_path),
                '-filter_complex', '[0:v][1:v]vstack[stacked]',
                '-map', '[stacked]',
                '-map', '1:a',  # Audio from bottom box
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(stacked_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[DEBUG] Stacked video created: 1080x1920")

            # Step 4: Add captions if provided
            if caption_text:
                print(f"[DEBUG] Adding captions...")
                self._add_captions_overlay(stacked_path, output_path, caption_text)
            else:
                # Just copy stacked to output
                shutil.copy(stacked_path, output_path)

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"[DEBUG] Stacked {ai_content_type} format complete: {output_path}")

            return {
                'success': True,
                'output_path': str(output_path),
                'mode': f'stacked_{ai_content_type}',
                'format': f'{box_width}x{box_height * 2} (two {box_width}x{box_height} boxes stacked)'
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error in stacked conversion: {e.stderr.decode() if e.stderr else str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error in stacked conversion: {str(e)}"
            }

    def _generate_ai_photo_placeholder(self, width: int, height: int, duration: float, fps: float, output_path: Path):
        """
        Generate placeholder for AI-animated photo (solid color with text)

        Args:
            width: Box width
            height: Box height
            duration: Video duration in seconds
            fps: Frames per second
            output_path: Output path for placeholder
        """
        print(f"[DEBUG] Generating AI photo placeholder...")

        # Create solid color with text overlay
        # Using lavfi to generate test pattern
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'color=c=0x2E3440:s={width}x{height}:d={duration}:r={fps}',
            '-vf', f"drawtext=text='AI Photo Placeholder':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _generate_ai_video_placeholder(self, width: int, height: int, duration: float, fps: float, output_path: Path):
        """
        Generate placeholder for AI-generated video (animated gradient)

        Args:
            width: Box width
            height: Box height
            duration: Video duration in seconds
            fps: Frames per second
            output_path: Output path for placeholder
        """
        print(f"[DEBUG] Generating AI video placeholder...")

        # Create animated gradient using testsrc2
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'testsrc2=size={width}x{height}:rate={fps}:duration={duration}',
            '-vf', f"drawtext=text='AI Video Placeholder':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _add_captions_overlay(self, video_path: Path, output_path: Path, caption_text: str):
        """
        Add caption text overlay to video

        Args:
            video_path: Input video path
            output_path: Output video path
            caption_text: Caption text to overlay
        """
        print(f"[DEBUG] Adding caption overlay: {caption_text[:50]}...")

        # Add caption at bottom using drawtext filter
        # Position captions in bottom 20% of frame with padding
        vf_filter = f"drawtext=text='{caption_text}':fontcolor=white:fontsize=36:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=h-th-100"

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', vf_filter,
            '-c:v', 'libx264',
            '-c:a', 'copy',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
