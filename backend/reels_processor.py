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

    def detect_face_segments(self, video_path: str, check_every_n_frames: int = 8) -> List[Dict]:
        """
        Detect faces throughout video and create segments with different face counts

        Args:
            video_path: Path to video
            check_every_n_frames: Check faces every N frames (default: 8)

        Returns:
            List of segments with face count and timestamps
        """
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

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            face_count = len(faces)
            timestamp = frame_idx / fps

            # Store face positions
            face_positions = []
            for (x, y, w, h) in faces:
                face_positions.append({
                    'x': x + w // 2,
                    'y': y + h // 2,
                    'w': w,
                    'h': h
                })

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

        # Average face sizes
        left_w_avg = sum(f['w'] for f in left_faces) / len(left_faces)
        left_h_avg = sum(f['h'] for f in left_faces) / len(left_faces)
        right_w_avg = sum(f['w'] for f in right_faces) / len(right_faces)
        right_h_avg = sum(f['h'] for f in right_faces) / len(right_faces)

        # Target: Face should be 40% of the crop width for nice padding
        # If face_width = 0.4 * crop_width, then crop_width = face_width / 0.4 = face_width * 2.5
        avg_face_width = (left_w_avg + right_w_avg) / 2
        desired_crop_width = int(avg_face_width * 2.5)

        # For 9:8 aspect ratio: height = width * 8/9
        desired_crop_height = int(desired_crop_width * 8 / 9)

        # CONSTRAINT: Crop height can't exceed half video height (since we stack two)
        # This is a hard constraint for maintaining proper stacking
        max_crop_height = height // 2
        max_crop_width = int(max_crop_height * 9 / 8)

        # If desired dimensions exceed video bounds, use maximum allowed dimensions
        if desired_crop_height > max_crop_height or desired_crop_width > max_crop_width:
            # Use maximum dimensions that fit while maintaining 9:8 ratio
            final_crop_height = max_crop_height
            final_crop_width = max_crop_width

            # In this case, faces will occupy more than 40% of the box
            # This happens when faces are very large relative to video size
            print(f"[DEBUG] Faces are large relative to video - using max crop dimensions")
            print(f"[DEBUG] Desired: {desired_crop_width}x{desired_crop_height}, Using: {final_crop_width}x{final_crop_height}")
        else:
            # We can achieve 40% face occupancy
            final_crop_width = desired_crop_width
            final_crop_height = desired_crop_height

        # Calculate crop positions centered around each face
        # Horizontal position (centered on face x)
        left_crop_x = int(left_x - final_crop_width // 2)
        right_crop_x = int(right_x - final_crop_width // 2)

        # Vertical position (centered on face y)
        left_crop_y = int(left_y - final_crop_height // 2)
        right_crop_y = int(right_y - final_crop_height // 2)

        # Ensure crops stay within bounds horizontally
        left_crop_x = max(0, min(left_crop_x, width - final_crop_width))
        right_crop_x = max(0, min(right_crop_x, width - final_crop_width))

        # Ensure crops stay within bounds vertically
        left_crop_y = max(0, min(left_crop_y, height - final_crop_height))
        right_crop_y = max(0, min(right_crop_y, height - final_crop_height))

        print(f"[DEBUG] Dual-face crop: width={final_crop_width}, height={final_crop_height} (ratio={final_crop_width/final_crop_height:.3f}, should be 1.125 for 9:8)")
        print(f"[DEBUG] Left face: avg_width={left_w_avg:.0f}, occupies {(left_w_avg/final_crop_width)*100:.1f}% of box width")
        print(f"[DEBUG] Right face: avg_width={right_w_avg:.0f}, occupies {(right_w_avg/final_crop_width)*100:.1f}% of box width")
        print(f"[DEBUG] Stacked output will be {final_crop_width}x{final_crop_height*2} (ratio={final_crop_width/(final_crop_height*2):.3f}, should be 0.5625 for 9:16)")

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
            'output_width': final_crop_width,
            'output_height': final_crop_height * 2
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
        dynamic_mode: bool = True
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

        Returns:
            dict with result
        """
        video_path = Path(video_path)

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_reels.mp4"
        else:
            output_path = Path(output_path)

        # If dynamic mode is enabled, use segment-based conversion
        if dynamic_mode and auto_detect:
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

            # Get video dimensions
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            # Detect face segments (check every 8 frames)
            print("[DEBUG] Detecting face segments for dynamic conversion...")
            segments = self.detect_face_segments(str(video_path), check_every_n_frames=8)

            if not segments:
                # No segments detected, fall back to simple single mode
                print("[DEBUG] No segments detected, using default single-face mode")
                crop_params = self._get_default_crop_position(width, height, "center")
                return self._convert_single_face_reels(video_path, output_path, crop_params)

            # Merge consecutive segments with same face count to reduce jitter
            merged_segments = self._merge_segments(segments)
            print(f"[DEBUG] Merged into {len(merged_segments)} segments")

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
                # Process each segment
                for i, seg in enumerate(merged_segments):
                    print(f"[DEBUG] Processing segment {i+1}/{len(merged_segments)}: "
                          f"{seg['face_count']} faces, {seg['start_time']:.1f}s-{seg['end_time']:.1f}s")

                    # Extract segment from original video
                    # Use re-encoding instead of copy to handle short segments properly
                    segment_path = temp_dir / f"segment_{i:03d}_raw.mp4"
                    extract_cmd = [
                        'ffmpeg',
                        '-i', str(video_path),
                        '-ss', str(seg['start_time']),
                        '-to', str(seg['end_time']),
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-preset', 'ultrafast',  # Fast encoding for temp segments
                        '-y',
                        str(segment_path)
                    ]
                    subprocess.run(extract_cmd, check=True, capture_output=True)

                    # Determine crop parameters for this segment
                    if seg['face_count'] == 2 and len(seg['faces']) > 0:
                        # Dual-face mode
                        crop_params = self._process_dual_face_crop(seg['faces'], width, height)
                        processed_path = temp_dir / f"segment_{i:03d}_processed.mp4"

                        # Apply dual-face crop
                        left = crop_params['left_face']
                        right = crop_params['right_face']

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
                            '-c:a', 'aac',
                            '-preset', 'medium',
                            '-crf', '23',
                            '-y',
                            str(processed_path)
                        ]
                    else:
                        # Single-face or no-face mode
                        # Get crop params for single face (or default if no faces)
                        if seg['face_count'] == 1 and len(seg['faces']) > 0:
                            # Calculate average face position for single face
                            all_faces = [face for frame_faces in seg['faces'] for face in frame_faces]
                            avg_x = sum(f['x'] for f in all_faces) / len(all_faces)

                            target_aspect = 9 / 16
                            crop_height = height
                            crop_width = int(crop_height * target_aspect)
                            crop_x = int(avg_x - crop_width // 2)
                            crop_x = max(0, min(crop_x, width - crop_width))

                            crop_params = {
                                'x': crop_x,
                                'y': 0,
                                'width': crop_width,
                                'height': crop_height
                            }
                        else:
                            # No face or multiple faces - use default center crop
                            crop_params = self._get_default_crop_position(width, height, "center")

                        processed_path = temp_dir / f"segment_{i:03d}_processed.mp4"

                        crop_filter = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}"
                        vf_filter = f"{crop_filter},scale=1080:1920"

                        process_cmd = [
                            'ffmpeg',
                            '-i', str(segment_path),
                            '-vf', vf_filter,
                            '-c:v', 'libx264',
                            '-c:a', 'aac',
                            '-preset', 'medium',
                            '-crf', '23',
                            '-y',
                            str(processed_path)
                        ]

                    subprocess.run(process_cmd, check=True, capture_output=True)
                    segment_files.append(processed_path)

                # Concatenate all segments
                print(f"[DEBUG] Concatenating {len(segment_files)} processed segments")
                concat_list_path = temp_dir / "concat_list.txt"
                with open(concat_list_path, 'w') as f:
                    for seg_file in segment_files:
                        f.write(f"file '{seg_file}'\n")

                concat_cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_list_path),
                    '-c', 'copy',
                    '-y',
                    str(output_path)
                ]
                subprocess.run(concat_cmd, check=True, capture_output=True)

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
        This reduces jitter from temporary detection changes

        Args:
            segments: List of segments from detect_face_segments()

        Returns:
            Merged list of segments
        """
        if not segments:
            return []

        merged = []
        current = segments[0].copy()

        for seg in segments[1:]:
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
