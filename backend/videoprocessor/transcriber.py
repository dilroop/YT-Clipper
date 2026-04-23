"""
Audio Transcription Module
Uses OpenAI Whisper for speech-to-text with word-level timestamps

Input: Video file path (mp4, mkv, etc.)
Output: Dictionary containing 'segments' with word-level 'start', 'end', and 'text'
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

    def get_video_duration(self, video_path: str) -> float:
        """Helper to get video duration via ffprobe"""
        probe_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

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

        # Check if the video actually contains an audio stream
        probe_cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'a',
            '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if not probe_result.stdout.strip():
            print(f"No audio streams found in {video_path}")
            return None

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
        Transcribe video audio with word-level timestamps, with caching.

        Args:
            video_path: Path to video file
            progress_callback: Optional callback for progress updates

        Returns:
            dict with segments and word-level timestamps
        """
        try:
            video_path_obj = Path(video_path)
            video_id = video_path_obj.stem
            
            # Setup specific directory for transcript caches
            # Use same directory as where we placed the target file, normally Downloads
            cache_dir = video_path_obj.parent
            cache_file = cache_dir / f"{video_id}_transcript.json"

            # 1. Check if we already have a cached transcript!
            if cache_file.exists():
                print(f"Found cached transcript for {video_id}, loading from disk...")
                if progress_callback:
                    progress_callback({
                        'stage': 'transcribing',
                        'percent': 100,
                        'message': 'Using cached transcript...'
                    })
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    
                    # Ensure cached transcripts don't return an audio_path 
                    # that server.py might try to incorrectly delete
                    cached_data['audio_path'] = None
                    return cached_data

            # 2. Extract audio
            if progress_callback:
                progress_callback({
                    'stage': 'transcribing',
                    'percent': 0,
                    'message': 'Extracting audio...'
                })

            audio_path = self.extract_audio(video_path)
            segments = []
            full_text = ""
            language = "unknown"

            if audio_path is None:
                # Video has no audio track
                if progress_callback:
                    progress_callback({
                        'stage': 'transcribing',
                        'percent': 100,
                        'message': 'No audio track detected. Generating visual transcript...'
                    })
            else:
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
                
                language = result.get('language', 'unknown')
                full_text = result.get('text', '')

                if progress_callback:
                    progress_callback({
                        'stage': 'transcribing',
                        'percent': 100,
                        'message': 'Transcription complete!'
                    })

                # Process segments with word-level timestamps
                for segment in result.get('segments', []):
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

            # If no speech was detected (or no audio track), generate a fake visual transcript based on duration
            if not segments:
                duration = self.get_video_duration(video_path)
                import math
                if duration > 0:
                    words = []
                    for i in range(int(math.ceil(duration))):
                        m, s = divmod(i, 60)
                        h, m = divmod(m, 60)
                        if h > 0:
                            word_text = f"[{h:02d}:{m:02d}:{s:02d}]"
                        else:
                            word_text = f"[{m:02d}:{s:02d}]"
                            
                        words.append({
                            'word': word_text,
                            'start': float(i),
                            'end': min(float(i + 1), duration)
                        })
                    
                    # Group words into 10-second segments so it's not one giant block
                    for i in range(0, len(words), 10):
                        chunk = words[i:i+10]
                        if not chunk: break
                        segments.append({
                            'id': i // 10,
                            'start': chunk[0]['start'],
                            'end': chunk[-1]['end'],
                            'text': ' '.join(w['word'] for w in chunk),
                            'words': chunk
                        })
                    
                    full_text = ' '.join(s['text'] for s in segments)
                    language = 'visual'

            result_dict = {
                'success': True,
                'language': language,
                'segments': segments,
                'full_text': full_text,
                'audio_path': audio_path  # Return audio path for cleanup by caller
            }
            
            # Save the result to cache for future requests
            # (Set audio_path to None so if loaded later, caller doesn't try to delete phantom files)
            cache_clone = result_dict.copy()
            cache_clone['audio_path'] = None
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_clone, f, ensure_ascii=False)
                print(f"Transcript cached successfully to {cache_file}")
            except Exception as cache_err:
                print(f"Warning: Failed to cache transcript: {cache_err}")

            return result_dict

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


if __name__ == "__main__":
    import sys
    import datetime
    import cv2
    from pathlib import Path

    # Ensure local import works when run directly
    try:
        from subtitle_burner import SubtitleBurner
    except ImportError:
        sys.path.append(str(Path(__file__).parent.parent))
        from videoprocessor.subtitle_burner import SubtitleBurner

    print("\n" + "="*50)
    print("YT-Clipper Standalone Subtitle Generator (CLI)")
    print("="*50 + "\n")

    video_input = input("Enter the path to the original video: ").strip()
    if not video_input:
        print("[!] No video path provided. Exiting.")
        sys.exit(1)

    video_path_obj = Path(video_input)
    if not video_path_obj.exists():
        print(f"[!] File not found: {video_input}")
        sys.exit(1)

    font_family = input("\nEnter font family [e.g. Arial, Impact] (Default: Arial): ").strip() or "Arial"
    
    font_size_str = input("Enter font size (Default: 80): ").strip()
    font_size = int(font_size_str) if font_size_str.isdigit() else 80
    
    text_color = input("Enter text hex color (Default: #22DD66): ").strip() or "#22DD66"
    
    words_count_str = input("Enter number of words per caption [1-5] (Default: 3): ").strip()
    words_count = int(words_count_str) if words_count_str.isdigit() else 3
    
    y_pos_str = input("Enter Y position percentage from top [e.g. 50=middle, 80=bottom] (Default: 80): ").strip()
    y_pos = int(y_pos_str) if y_pos_str.isdigit() else 80

    print("\n[+] Configuration complete. Initializing...\n")
    
    transcriber = AudioTranscriber()
    
    def log_progress(data):
        print(f"[{data.get('stage', 'Info').upper()}] {data.get('percent', 0)}% - {data.get('message', '')}")
        
    print(f"\n---> STEP 1: Transcribing {video_path_obj.name}...")
    transcript_result = transcriber.transcribe(str(video_path_obj), progress_callback=log_progress)
    
    if not transcript_result.get('success', False):
        print(f"[!] Transcription failed: {transcript_result.get('error')}")
        sys.exit(1)
        
    words = []
    for segment in transcript_result.get('segments', []):
        for word in segment.get('words', []):
            words.append(word)
            
    if not words:
        print("[!] No speech detected in the audio track.")
        sys.exit(1)
        
    print(f"[+] Detected {len(words)} total words.")
    
    print("\n---> STEP 2: Rendering Subtitles...")
    
    # Grab native dimensions
    cap = cv2.VideoCapture(str(video_path_obj))
    if cap.isOpened():
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[+] Detected resolution: {width}x{height}")
        cap.release()
    else:
        width, height = 1920, 1080
        print("[!] Could not fetch dimensions. Defaulting to 1920x1080")

    timestamp_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = video_path_obj.parent / f"{video_path_obj.stem}_transcribed_{timestamp_suffix}.mp4"
    
    config = {
        'words_per_caption': words_count,
        'font_family': font_family,
        'font_size': font_size,
        'vertical_position': y_pos,
        'text_color': text_color
    }
    
    burner = SubtitleBurner(config=config)
    temp_ass_path = video_path_obj.parent / f"temp_ass_{timestamp_suffix}.ass"
    
    try:
        ass_file = burner.create_ass_subtitles(
            words=words,
            output_path=str(temp_ass_path),
            clip_start_time=0,
            video_width=width,
            video_height=height
        )
        print(f"[+] Built ASS Subtitles at {ass_file}")
        print("[+] FFMPEG rendering video (this might take a while)...")
        
        result = burner.burn_captions(
            video_path=str(video_path_obj),
            subtitle_path=str(temp_ass_path),
            output_path=str(output_path)
        )
        
        if result.get('success'):
            print("\n" + "="*50)
            print(f"SUCCESS! Output saved directly next to the original:\n{output_path}")
            print("="*50 + "\n")
        else:
            print(f"\n[!] Subtitle rendering failed: {result.get('error', 'Unknown Error')}")
            
    except Exception as e:
        print(f"[!] Fatal error during rendering pipeline: {e}")
    finally:
        # Cleanup
        if temp_ass_path.exists():
            temp_ass_path.unlink()
