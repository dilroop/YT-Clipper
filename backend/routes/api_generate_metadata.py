import json
import traceback
from fastapi import APIRouter, HTTPException
from backend.core.constants import BASE_DIR
from backend.core.config import get_config_with_defaults

router = APIRouter()


def _build_prompt(info_data: dict, filename: str) -> str:
    """Build a prompt for the AI from the clip's info JSON."""
    video_title = info_data.get("video", {}).get("title") or info_data.get("title", "Unknown Video")
    video_desc = info_data.get("video", {}).get("description") or info_data.get("description", "")
    transcript = info_data.get("transcript", "")
    channel = info_data.get("video", {}).get("channel") or info_data.get("channel", "Unknown Channel")

    # Trim transcript to avoid token overload
    if len(transcript) > 3000:
        transcript = transcript[:3000] + "..."

    return f"""You are an expert Social Media Growth Strategist and Viral Copywriter. Your specialty is writing high-retention content for YouTube, Instagram, and TikTok.

VIDEO CONTEXT:
- Source: "{video_title}" by {channel}
- Transcript: {transcript}

TASK: Generate a complete social media metadata package for this clip.

SOCIAL MEDIA PACKAGING RULES:

### 1. YouTube Package (Search & Browse Optimized)
- **Title:** 3 curiosity-gap options (Max 60 chars) separated by new lines. 
  - *Rule:* Strictly avoid pipes (|). Use colons (:) or parentheses () for separation. 
  - *Emoji:* Max 1, placed at the very end of the title.
- **Description:** A 2-paragraph summary. 
  - *SEO Rule:* The first 150 characters must contain your primary keywords for the algorithm preview.
- **Hashtags:** Exactly 3 highly relevant hashtags at the bottom.
- **Emojis:** Use exactly 3 in the description as section/bullet headers.

### 2. Instagram Package (Aesthetic & Authority)
- **Reel Hook (On-screen):** 3 punchy options (3–7 words) separated by new lines. 
  - *Rule:* Use "Problem/Solution" or "Secret" framing. Avoid special symbols like % or &.
- **Caption:** A "Micro-story" style caption (100–150 words). 
  - *Rule:* Use frequent line breaks (1–2 sentences per block). No large text walls.
- **Hashtags:** Exactly 5 hashtags. (Mix: 1 Broad, 3 Niche, 1 Branded).
- **Emojis:** Use 3–5 relevant emojis placed at the end of key sentences as visual "punctuation."

### 3. TikTok Package (Viral Discovery)
- **On-screen Hook:** 3 high-energy options (Fast-paced and direct) separated by new lines.
  - *Rule:* Use "Search-Friendly" text (words people actually type into the TikTok search bar).
- **Caption:** Punchy and short (Under 150 characters). 
  - *Rule:* Avoid formal punctuation; write it like a trending "comment" or a quick text.
- **Hashtags:** 3–4 hashtags focused on specific niche sub-cultures (e.g., #ScienceTok).
- **Emojis:** Use 2–3 emojis, usually grouped at the end of the text.

Return response as a valid JSON object with EXACTLY this structure:
{{
  "youtube": {{
    "title": "Option 1 | Option 2 | Option 3",
    "description": "...",
    "hashtags": "#tag1 #tag2 #tag3"
  }},
  "instagram": {{
    "title": "Hook 1 | Hook 2 | Hook 3",
    "description": "...",
    "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5"
  }},
  "tiktok": {{
    "title": "Hook 1 | Hook 2 | Hook 3",
    "description": "...",
    "hashtags": "#tag1 #tag2 #tag3"
  }},
  "keywords": ["tag1", "tag2", "tag3"]
}}

Rules:
- Output ONLY the raw JSON.
- DO NOT use markdown code blocks.
- Ensure all descriptions are completed fully."""


@router.post("/api/clips/{project}/{format}/{filename}/generate-metadata")
async def generate_metadata(project: str, format: str, filename: str):
    """
    Use AI to generate multi-platform metadata for a clip.
    """
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        stem = video_path.stem
        info_json_path = video_path.parent / f"{stem}_info.json"

        if not info_json_path.exists():
             raise HTTPException(status_code=404, detail="Info JSON not found")

        with open(info_json_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)

        # Extract video source info for attribution
        video_info = info_data.get("video", {})
        channel_name = video_info.get("channel", "Unknown Channel")
        video_url = video_info.get("url", "")
        source_attribution = f"\n\nSource of the Clip: {channel_name}\nLink: {video_url}"

        # Load AI config
        config = get_config_with_defaults()
        ai_settings = config.get("ai_settings", {})

        openai_cfg = ai_settings.get("openai", {})
        openai_key = openai_cfg.get("api_key", "")
        deepseek_cfg = ai_settings.get("deepseek", {})
        deepseek_key = deepseek_cfg.get("api_key", "")

        prompt = _build_prompt(info_data, filename)

        generated = None
        error_detail = None

        # Helper to strip markdown and parse JSON
        def clean_and_parse(raw):
             raw = raw.strip()
             if raw.startswith("```"):
                 lines = raw.splitlines()
                 if lines[0].startswith("```"): lines = lines[1:]
                 if lines[-1].startswith("```"): lines = lines[:-1]
                 raw = "\n".join(lines).strip()
             return json.loads(raw)

        if openai_key and openai_key.startswith("sk-"):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                model = openai_cfg.get("model") or "gpt-4o-mini"
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1000,
                )
                generated = clean_and_parse(response.choices[0].message.content)
            except Exception as e:
                error_detail = f"OpenAI failed: {e}"

        if generated is None and deepseek_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com/v1")
                model = deepseek_cfg.get("model") or "deepseek-chat"
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1000,
                )
                generated = clean_and_parse(response.choices[0].message.content)
            except Exception as e:
                error_detail = f"DeepSeek failed: {e}"

        if generated is None:
            raise HTTPException(status_code=503, detail=f"AI generation failed. ({error_detail})")

        # Inject source attribution into all platform descriptions
        for platform in ["youtube", "instagram", "tiktok"]:
            if platform in generated:
                desc = str(generated[platform].get("description", ""))
                generated[platform]["description"] = desc + source_attribution

        # Build final metadata object
        # Merge the new platform-specific packages into the existing clip metadata
        if "clip" not in info_data:
             info_data["clip"] = {}
        
        # We merge the generated packages (youtube, instagram, tiktok, keywords)
        # while preserving existing fields like 'parts', 'reason', 'score', etc.
        for key, value in generated.items():
            info_data["clip"][key] = value

        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)

        return {"success": True, "clip": generated}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
