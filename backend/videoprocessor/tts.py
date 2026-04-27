import os
import argparse
import numpy as np
import soundfile as sf
from backend.videoprocessor.kokoro_manager import ensure_kokoro_assets_exist, MODEL_PATH, VOICES_PATH

class KokoroTTS:
    _instance = None

    def __init__(self):
        self.kokoro_instance = None
        self._load_kokoro_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_kokoro_model(self):
        ensure_kokoro_assets_exist()
        try:
            from kokoro_onnx import Kokoro
            self.kokoro_instance = Kokoro(
                model_path=str(MODEL_PATH), 
                voices_path=str(VOICES_PATH)
            )
            print("Kokoro model initialized.")
        except Exception as e:
            print(f"ERROR: Could not load kokoro-onnx: {e}")
            raise

    def generate_audio(self, text: str, speaker_name: str = "am_echo", speed: float = 1.0, lang: str = "en-us") -> tuple:
        if self.kokoro_instance is None:
            self._load_kokoro_model()

        try:
            speaker_data = self.kokoro_instance.get_voice_style(speaker_name)
            audio_array, sample_rate = self.kokoro_instance.create(text, voice=speaker_data, speed=speed, lang=lang)
            if audio_array is None:
                raise ValueError("Kokoro returned no audio.")
            return audio_array, sample_rate
        except Exception as e:
            print(f"Error during audio generation: {e}")
            raise

def generate_tts_file(text: str, output_path: str, speaker: str = "am_echo", speed: float = 1.0):
    tts = KokoroTTS.get_instance()
    audio, sr = tts.generate_audio(text, speaker_name=speaker, speed=speed)
    sf.write(output_path, audio, sr)
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS using Kokoro")
    parser.add_argument("--text", type=str, required=True, help="Text to synthesize")
    parser.add_argument("--output", type=str, default="output.wav", help="Output file path")
    parser.add_argument("--speaker", type=str, default="am_echo", help="Speaker voice id")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed")
    args = parser.parse_args()

    ensure_kokoro_assets_exist()
    print(f"Generating audio for '{args.text}' using {args.speaker} at {args.speed}x...")
    generate_tts_file(args.text, args.output, args.speaker, args.speed)
    print(f"Saved to {args.output}")
