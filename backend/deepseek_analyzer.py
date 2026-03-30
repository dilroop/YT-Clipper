"""
DeepSeek Clip Analyzer
Uses DeepSeek's chat API (OpenAI-compatible) to detect interesting clips from video transcripts.
Same normalized output format as AIAnalyzer.
"""

from backend.ai_analyzer import AIAnalyzer


class DeepSeekAnalyzer(AIAnalyzer):
    """
    DeepSeek-backed analyzer. Re-uses all of AIAnalyzer's logic (prompt building,
    clip validation, timestamp parsing, etc.) and simply overrides the OpenAI client
    to point at DeepSeek's API endpoint.
    """

    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

    # Available DeepSeek models (used for frontend dropdown)
    AVAILABLE_MODELS = [
        "deepseek-chat",
        "deepseek-reasoner",
    ]

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        min_clip_duration: int,
        max_clip_duration: int,
    ):
        """
        Initialize DeepSeek analyzer.

        Args:
            api_key: DeepSeek API key
            model: Model name (deepseek-chat, deepseek-reasoner)
            temperature: Sampling temperature (0.0–2.0)
            min_clip_duration: Minimum clip length in seconds
            max_clip_duration: Maximum clip length in seconds
        """
        # Import here to avoid circular imports at module level
        from openai import OpenAI

        # Store attributes
        self.model = model
        self.temperature = temperature
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.provider_name = "DeepSeek"

        # Point the OpenAI SDK at DeepSeek's API
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.DEEPSEEK_BASE_URL,
        )

        print(f"🧠 DeepSeek Analyzer initialized: model={model}, temperature={temperature}")
