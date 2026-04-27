import os
import requests
import io
import torch
import numpy as np
from tqdm import tqdm
from backend.core.constants import BASE_DIR

MODELS_DIR = BASE_DIR / "backend" / "assets" / "kokoro_models"
MODEL_PATH = MODELS_DIR / "kokoro.onnx"
VOICES_PATH = MODELS_DIR / "voices.bin"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"

SUPPORTED_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole", "af_nova", "af_river", "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
]

def download_file():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    if os.path.exists(MODEL_PATH):
        print(f"'{MODEL_PATH}' already exists.")
        return

    print(f"Downloading {MODEL_PATH} from {MODEL_URL}...")
    with requests.get(MODEL_URL, stream=True, allow_redirects=True) as response:
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        block_size = 4096
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=str(MODEL_PATH))
        with open(MODEL_PATH, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()

def download_voices_data():
    if os.path.exists(VOICES_PATH):
        print(f"'{VOICES_PATH}' already exists.")
        return

    pattern = "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices/{name}.pt"
    voices = {}

    for name in tqdm(SUPPORTED_VOICES, desc="Downloading voices"):
        url = pattern.format(name=name)
        try:
            r = requests.get(url)
            r.raise_for_status()
            content = io.BytesIO(r.content)
            data: np.ndarray = torch.load(content, map_location='cpu', weights_only=True).numpy()
            voices.update({name: data})
        except Exception as e:
            print(f"Failed to download voice '{name}': {e}")
            continue

    if not voices:
        raise RuntimeError("No voices downloaded.")

    with open(VOICES_PATH, "wb") as f:
        np.savez(f, **voices)
    print(f"Created {VOICES_PATH}")

def ensure_kokoro_assets_exist():
    download_file()
    download_voices_data()

if __name__ == "__main__":
    ensure_kokoro_assets_exist()
