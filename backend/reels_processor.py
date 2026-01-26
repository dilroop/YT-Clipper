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

        Args:
            video_path: Path to video
            sample_frames: Number of frames to sample for detection

        Returns:
            dict with crop parameters (x, y, width, height)
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

            # Store face positions
            for (x, y, w, h) in faces:
                face_positions.append({
                    'x': x + w // 2,  # Face center x
                    'y': y + h // 2,  # Face center y
                    'w': w,
                    'h': h
                })

        cap.release()

        # Calculate average face position
        if face_positions:
            avg_x = sum(f['x'] for f in face_positions) / len(face_positions)
            avg_y = sum(f['y'] for f in face_positions) / len(face_positions)
            avg_w = sum(f['w'] for f in face_positions) / len(face_positions)
            avg_h = sum(f['h'] for f in face_positions) / len(face_positions)

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
                'face_detected': True
            }
        else:
            # No face detected - use Joe Rogan style default positions
            return self._get_default_crop_position(width, height)

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
            'position': position
        }

    def convert_to_reels(
        self,
        video_path: str,
        output_path: str = None,
        auto_detect: bool = True
    ) -> Dict:
        """
        Convert video to reels format with smart cropping

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

        # Detect speaker position
        if auto_detect:
            crop_params = self.detect_speaker_position(str(video_path))
        else:
            # Get video dimensions for default crop
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            crop_params = self._get_default_crop_position(width, height, "center")

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
                'crop_params': crop_params
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error converting to reels: {e.stderr.decode()}"
            }
