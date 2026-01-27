"""
Reels Processor Module
Converts videos to reels format (9:16) with speaker auto-focus
Uses face detection for intelligent cropping
"""

import cv2
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class ReelsProcessor:
    def __init__(self):
        """Initialize reels processor with face detection"""
        # Load OpenCV's pre-trained face detector
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

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

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            # Track when we detect exactly 2 faces
            if len(faces) == 2:
                frames_with_two_faces += 1

            # Store face positions with frame info
            frame_faces = []
            for (x, y, w, h) in faces:
                frame_faces.append({
                    'x': x + w // 2,  # Face center x
                    'y': y + h // 2,  # Face center y
                    'w': w,
                    'h': h
                })

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
        # Calculate average face position from all detected faces
        all_faces = [face for frame_faces in face_positions for face in frame_faces]

        if all_faces:
            avg_x = sum(f['x'] for f in all_faces) / len(all_faces)
            avg_y = sum(f['y'] for f in all_faces) / len(all_faces)
            avg_w = sum(f['w'] for f in all_faces) / len(all_faces)
            avg_h = sum(f['h'] for f in all_faces) / len(all_faces)

            # Calculate crop parameters for 9:16 aspect ratio
            target_aspect = 9 / 16  # width / height for reels
            crop_height = height
            crop_width = int(crop_height * target_aspect)

            # Center crop around detected face
            crop_x = int(avg_x - crop_width // 2)

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
        Ensures faces are centered in their respective boxes

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

        # Calculate average positions for left and right faces
        left_faces = []
        right_faces = []

        for frame in dual_face_frames:
            # Sort by x position to identify left/right
            sorted_faces = sorted(frame, key=lambda f: f['x'])
            left_faces.append(sorted_faces[0])
            right_faces.append(sorted_faces[1])

        # Average positions (center of face)
        left_x = sum(f['x'] for f in left_faces) / len(left_faces)
        left_y = sum(f['y'] for f in left_faces) / len(left_faces)
        right_x = sum(f['x'] for f in right_faces) / len(right_faces)
        right_y = sum(f['y'] for f in right_faces) / len(right_faces)

        # Average face sizes for padding calculation
        left_w_avg = sum(f['w'] for f in left_faces) / len(left_faces)
        right_w_avg = sum(f['w'] for f in right_faces) / len(right_faces)

        # Calculate 9:8 crop dimensions (half of 9:16 vertically)
        # Each box is 9:8, stacked = 9:16
        # Add 2x padding around faces for better framing
        half_height = height // 2
        crop_width = int(half_height * 9 / 8)

        # Increase crop area by 2x to add padding around faces
        # This gives more context and makes the framing less claustrophobic
        padding_multiplier = 2.0

        # Calculate padded crop dimensions based on face size
        left_padded_width = int(left_w_avg * padding_multiplier)
        right_padded_width = int(right_w_avg * padding_multiplier)

        # Use the larger of: crop_width or padded_width (to ensure we don't crop too tight)
        left_crop_width = max(crop_width, left_padded_width)
        right_crop_width = max(crop_width, right_padded_width)

        # Calculate crop positions centered around each face
        # Horizontal position (centered on face x)
        left_crop_x = int(left_x - left_crop_width // 2)
        right_crop_x = int(right_x - right_crop_width // 2)

        # Vertical position (centered on face y with extra vertical padding)
        left_crop_y = int(left_y - half_height // 2)
        right_crop_y = int(right_y - half_height // 2)

        # Ensure crops stay within bounds horizontally
        left_crop_x = max(0, min(left_crop_x, width - left_crop_width))
        right_crop_x = max(0, min(right_crop_x, width - right_crop_width))

        # Ensure crops stay within bounds vertically
        left_crop_y = max(0, min(left_crop_y, height - half_height))
        right_crop_y = max(0, min(right_crop_y, height - half_height))

        # Use consistent crop width for final output (use the larger one)
        final_crop_width = max(left_crop_width, right_crop_width)

        return {
            'mode': 'dual',
            'face_detected': True,
            'left_face': {
                'x': left_crop_x,
                'y': left_crop_y,
                'width': final_crop_width,
                'height': half_height
            },
            'right_face': {
                'x': right_crop_x,
                'y': right_crop_y,
                'width': final_crop_width,
                'height': half_height
            },
            'output_width': final_crop_width,
            'output_height': height
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
        auto_detect: bool = True
    ) -> Dict:
        """
        Convert video to reels format with smart cropping
        Supports single-face and dual-face split-screen modes

        Args:
            video_path: Path to input video
            output_path: Optional output path
            auto_detect: Use face detection for cropping

        Returns:
            dict with result
        """
        video_path = Path(video_path)

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_reels.mp4"
        else:
            output_path = Path(output_path)

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

        # Create complex filter for dual split-screen:
        # 1. Split input into 2 streams
        # 2. Crop left face from first stream
        # 3. Crop right face from second stream
        # 4. Stack them vertically
        # 5. Scale to 1080x1920
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
