import json
import traceback
from fastapi import APIRouter, HTTPException
from backend.core.constants import BASE_DIR
from backend.core.config import get_config_with_defaults

router = APIRouter()


def _build_prompt(info_data: dict, filename: str) -> str:
    """Build a prompt for the AI from the clip's info JSON."""
    video_title = info_data.get("title", "")
    video_desc = info_data.get("description", "")
    transcript = info_data.get("transcript", "")
    channel = info_data.get("channel", "")

    # Trim transcript to avoid token overload
    if len(transcript) > 3000:
        transcript = transcript[:3000] + "..."

    return f"""You are a social media content expert. Your job is to generate compelling metadata for a short video clip.

VIDEO CONTEXT:
- Source: "{video_title}" by {channel}
- Video description: {video_desc[:500] if video_desc else "N/A"}
- Clip transcript: {transcript}
- Clip filename: {filename}

TASK: Based on the transcript and video context above, generate metadata for this specific clip segment.

Return a valid JSON object with EXACTLY these keys (no extra keys, no markdown):
{{
  "title": "A concise, engaging clip title (max 80 chars)",
  "description": "A compelling 2-3 sentence description of what happens in this clip. Include context about who is speaking and what the key insight or moment is.",
  "keywords": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
}}

Rules:
- Title should grab attention and be searchable
- Description should be suitable for a YouTube or Instagram post caption
- Include 6-10 relevant keywords/tags as an array of lowercase strings
- Do NOT include hashtag symbols in keywords
- Output ONLY the raw JSON, no markdown code blocks"""


@router.post("/api/clips/{project}/{format}/{filename}/generate-metadata")
async def generate_metadata(project: str, format: str, filename: str):
    """
    Use AI to generate a title, description, and keywords for a clip
    that lacks proper metadata (e.g. workflow-generated clips).
    Reads the existing _info.json, generates content via AI, and saves back.
    """
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        stem = video_path.stem

        # Find existing info file (prefer JSON)
        info_json_path = video_path.parent / f"{stem}_info.json"
        info_txt_path = video_path.parent / f"{stem}_info.txt"

        info_data = {}
        if info_json_path.exists():
            with open(info_json_path, "r", encoding="utf-8") as f:
                info_data = json.load(f)
        elif info_txt_path.exists():
            with open(info_txt_path, "r", encoding="utf-8") as f:
                info_data["transcript"] = f.read()

        # Load AI config
        config = get_config_with_defaults()
        ai_settings = config.get("ai_settings", {})

        # Try OpenAI first, then DeepSeek
        generated = None
        error_detail = None

        openai_cfg = ai_settings.get("openai", {})
        openai_key = openai_cfg.get("api_key", "")
        deepseek_cfg = ai_settings.get("deepseek", {})
        deepseek_key = deepseek_cfg.get("api_key", "")

        prompt = _build_prompt(info_data, filename)

        if openai_key and openai_key.startswith("sk-"):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                model = openai_cfg.get("model") or "gpt-4o-mini"
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=600,
                )
                raw = response.choices[0].message.content.strip()
                generated = json.loads(raw)
            except Exception as e:
                error_detail = f"OpenAI failed: {e}"
                traceback.print_exc()

        if generated is None and deepseek_key:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=deepseek_key,
                    base_url="https://api.deepseek.com/v1",
                )
                model = deepseek_cfg.get("model") or "deepseek-chat"
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=600,
                )
                raw = response.choices[0].message.content.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                generated = json.loads(raw.strip())
            except Exception as e:
                error_detail = f"DeepSeek failed: {e}"
                traceback.print_exc()

        if generated is None:
            raise HTTPException(
                status_code=503,
                detail=f"AI generation failed. Configure an API key in Settings. ({error_detail})"
            )

        # Validate the response shape
        title = str(generated.get("title", "")).strip() or filename
        description = str(generated.get("description", "")).strip()
        keywords = generated.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip().lower() for k in keywords if k]

        # Merge into existing info_data under the "clip" key
        if "clip" not in info_data:
            info_data["clip"] = {}
        info_data["clip"]["title"] = title
        info_data["clip"]["description"] = description
        info_data["clip"]["keywords"] = keywords

        # Always write back as JSON
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "clip": {
                "title": title,
                "description": description,
                "keywords": keywords,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating metadata: {str(e)}")
