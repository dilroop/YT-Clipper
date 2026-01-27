"""
Audio Transcription Module
Uses OpenAI Whisper for speech-to-text with word-level timestamps
"""

import whisper
import subprocess
from pathlib import Path
import json


class AudioTranscriber:
    def __init__(self, model_name: str = "base"):
        """
        Initialize Whisper model

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
                       base is good balance of speed/accuracy
        """
        print(f"Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name)
        print("Whisper model loaded successfully")

    def extract_audio(self, video_path: str, output_path: str = None) -> str:
        """
        Extract audio from video using ffmpeg

        Args:
            video_path: Path to video file
            output_path: Optional output path for audio file

        Returns:
            Path to extracted audio file
        """
        video_path = Path(video_path)

        if output_path is None:
            # Use dedicated temp folder for audio extraction
            temp_dir = Path(__file__).parent.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            output_path = temp_dir / f"{video_path.stem}_audio.wav"
        else:
            output_path = Path(output_path)

        # Extract audio with ffmpeg
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (Whisper's native)
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return str(output_path)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error extracting audio: {e.stderr.decode()}")

    def transcribe(self, video_path: str, progress_callback=None) -> dict:
        """
        Transcribe video audio with word-level timestamps

        Args:
            video_path: Path to video file
            progress_callback: Optional callback for progress updates

        Returns:
            dict with segments and word-level timestamps
        """
        try:
            # Extract audio
            if progress_callback:
                progress_callback({
                    'stage': 'transcribing',
                    'percent': 0,
                    'message': 'Extracting audio...'
                })

            audio_path = self.extract_audio(video_path)

            # Transcribe with Whisper
            if progress_callback:
                progress_callback({
                    'stage': 'transcribing',
                    'percent': 20,
                    'message': 'Transcribing audio...'
                })

            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )

            if progress_callback:
                progress_callback({
                    'stage': 'transcribing',
                    'percent': 100,
                    'message': 'Transcription complete!'
                })

            # Don't clean up audio file immediately - let caller handle cleanup
            # This allows reusing the audio file if needed and ensures cleanup only on success

            # Process segments with word-level timestamps
            segments = []
            for segment in result['segments']:
                segment_data = {
                    'id': segment['id'],
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip(),
                    'words': []
                }

                # Extract word-level timestamps if available
                if 'words' in segment:
                    for word_info in segment['words']:
                        segment_data['words'].append({
                            'word': word_info['word'].strip(),
                            'start': word_info['start'],
                            'end': word_info['end']
                        })

                segments.append(segment_data)

            return {
                'success': True,
                'language': result.get('language', 'unknown'),
                'segments': segments,
                'full_text': result['text'],
                'audio_path': audio_path  # Return audio path for cleanup by caller
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_text_at_timestamp(self, segments: list, start_time: float, end_time: float) -> str:
        """
        Get text spoken between two timestamps

        Args:
            segments: List of transcript segments
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Text spoken in that time range
        """
        words = []

        for segment in segments:
            for word_info in segment.get('words', []):
                word_start = word_info['start']
                word_end = word_info['end']

                # Check if word overlaps with time range
                if word_start <= end_time and word_end >= start_time:
                    words.append(word_info['word'])

        return ' '.join(words).strip()
