# Clip Detection Methods

YTClipper now supports two methods for detecting interesting clips from videos:

## 1. Simple Keyword-Based Detection (analyzer.py)

**How it works:**
- Uses predefined keywords to score segments
- Looks for excitement words: "amazing", "incredible", "wow", "insane", etc.
- Detects questions and emphasis
- Counts exclamation marks and capital letters
- Fast and works offline

**Pros:**
- ✅ Free (no API costs)
- ✅ Fast processing
- ✅ Works offline
- ✅ No API key needed

**Cons:**
- ❌ Less accurate
- ❌ Misses context and nuance
- ❌ Can't understand semantic meaning
- ❌ Limited to English keyword matching

**Best for:**
- Quick testing
- Processing many videos on a budget
- Videos with obvious excitement markers

---

## 2. AI-Based Detection (ai_analyzer.py)

**How it works:**
- Sends transcript with timestamps to GPT (OpenAI)
- AI analyzes content semantically
- Looks for: punchlines, insights, drama, quotes, story arcs
- Understands context and quality
- Based on the approach used by successful short-form content creators

**Pros:**
- ✅ Much more accurate
- ✅ Understands context and nuance
- ✅ Can identify hooks, plot twists, and emotional moments
- ✅ Works with any language (multilingual)
- ✅ Finds complete story segments

**Cons:**
- ❌ Costs money (OpenAI API fees)
- ❌ Requires internet connection
- ❌ Slower than keyword-based
- ❌ Needs API key configuration

**Best for:**
- High-quality content creation
- Professional use cases
- Maximum clip quality
- Complex or narrative content

---

## Setup Guide

### For Simple Keyword-Based Detection

No setup needed! Just use the existing `SectionAnalyzer` class:

```python
from backend.analyzer import SectionAnalyzer

analyzer = SectionAnalyzer(
    min_clip_duration=15,
    max_clip_duration=60
)

clips = analyzer.find_interesting_clips(segments, num_clips=5)
```

### For AI-Based Detection

1. **Get an OpenAI API key:**
   - Go to https://platform.openai.com/api-keys
   - Create a new API key
   - Copy the key (starts with `sk-`)

2. **Set up environment variable:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

   Or create a `.env` file:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

3. **Use the AI analyzer:**
   ```python
   from backend.ai_analyzer import AIAnalyzer
   import os

   api_key = os.getenv('OPENAI_API_KEY')

   analyzer = AIAnalyzer(
       api_key=api_key,
       model="gpt-4o-mini",  # or "gpt-4" for higher quality
       temperature=1.0,
       min_clip_duration=15,
       max_clip_duration=60
   )

   # Optional: pass video info for better context
   video_info = {
       'title': 'Video Title',
       'description': 'Video description...'
   }

   clips = analyzer.find_interesting_clips(
       segments,
       num_clips=5,
       video_info=video_info
   )
   ```

---

## Cost Comparison

### Keyword-Based
- **Cost per video:** $0 (free)
- **Processing time:** ~1-2 seconds

### AI-Based (GPT-4o-mini)
- **Cost per video:** ~$0.01-0.10 (depending on video length)
- **Processing time:** ~5-15 seconds
- **API costs:**
  - Input: $0.15 per 1M tokens
  - Output: $0.60 per 1M tokens
- **Typical usage:** 10-30K tokens per video

### AI-Based (GPT-4)
- **Cost per video:** ~$0.30-1.00 (depending on video length)
- **Higher quality results**
- **API costs:**
  - Input: $5.00 per 1M tokens
  - Output: $15.00 per 1M tokens

---

## Recommendations

**Use Keyword-Based if:**
- You're processing many videos
- Budget is a concern
- Videos have obvious excitement moments
- Testing or development

**Use AI-Based if:**
- Quality is more important than cost
- Processing professional content
- Videos have subtle interesting moments
- Complex narratives or storytelling
- Podcast or interview content

**Hybrid Approach:**
1. Use keyword-based to filter obvious highlights
2. Use AI-based on top candidates for final selection
3. Saves money while maintaining quality

---

## Model Recommendations

### GPT-4o-mini (Recommended for most users)
- Best cost/performance ratio
- Fast and affordable
- Good quality results
- **Use for:** General content, high volume

### GPT-4
- Highest quality
- Better understanding of subtle nuance
- More expensive
- **Use for:** Premium content, critical projects

### GPT-3.5-turbo
- Cheapest option
- Lower quality than GPT-4o-mini
- **Use for:** Budget projects, testing

---

## Configuration Options

Both analyzers support these parameters:

```python
analyzer = AIAnalyzer(
    api_key="...",
    model="gpt-4o-mini",        # Model choice
    temperature=1.0,             # AI creativity (0.0-2.0)
    min_clip_duration=15,        # Minimum clip length (seconds)
    max_clip_duration=60         # Maximum clip length (seconds)
)
```

**Temperature guide:**
- 0.0-0.5: Conservative, predictable selections
- 0.5-1.0: Balanced (recommended)
- 1.0-2.0: Creative, varied selections

---

## Example Comparison

**Sample Video:** 15-minute podcast interview

### Keyword-Based Results:
```
Clip 1: "That's absolutely incredible! The way that..."
Clip 2: "What? Really? Are you serious about that?"
Clip 3: "This is amazing! I never thought..."
```
→ Found clips with excitement words, but may lack complete context

### AI-Based Results:
```
Clip 1: Complete story about overcoming a challenge
Clip 2: Unexpected revelation with emotional buildup
Clip 3: Funny anecdote with punchline
```
→ Found clips with narrative completeness and emotional impact

---

## Next Steps

To integrate AI-based detection into the server:

1. Add environment variable support
2. Update `/api/process` endpoint to accept `analysis_method` parameter
3. Update frontend to let users choose detection method
4. Add API key configuration in settings

See the reference implementation at: https://github.com/jipraks/yt-short-clipper
