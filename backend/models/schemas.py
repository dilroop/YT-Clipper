from pydantic import BaseModel
from typing import Optional, List

class VideoURLRequest(BaseModel):
    url: str

class AnalyzeVideoRequest(BaseModel):
    url: str
    ai_strategy: Optional[str] = "viral-moments"
    extra_context: Optional[str] = None
    client_id: Optional[str] = None

class ProcessVideoRequest(BaseModel):
    url: str
    format: str
    burn_captions: bool = True
    selected_clips: Optional[List] = None
    preanalyzed_clips: Optional[List] = None
    full_transcript_words: Optional[List] = None  # Full video words for re-deriving subtitles
    ai_strategy: Optional[str] = "viral-moments"
    extra_context: Optional[str] = None
    client_id: Optional[str] = None

class ConfigUpdate(BaseModel):
    downloader_backend: Optional[str] = None
    caption_settings: Optional[dict] = None
    watermark_settings: Optional[dict] = None
    ai_validation: Optional[dict] = None
