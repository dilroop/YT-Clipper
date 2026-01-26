# YTClipper Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure OpenAI API Key (Optional but Recommended)

For better clip detection using AI:

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Get your OpenAI API key:**
   - Go to https://platform.openai.com/api-keys
   - Sign up or log in
   - Click "Create new secret key"
   - Copy the key (starts with `sk-`)

3. **Edit the `.env` file:**
   ```bash
   nano .env  # or use your preferred editor
   ```

4. **Add your API key:**
   ```env
   OPENAI_API_KEY=sk-your-actual-key-here
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_TEMPERATURE=1.0
   ```

5. **Load environment variables:**
   ```bash
   # Option 1: Load manually
   source .env

   # Option 2: Use python-dotenv (recommended)
   pip3 install python-dotenv
   ```

   If using python-dotenv, add to the top of `backend/server.py`:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### 3. Start the Server

```bash
python3 backend/server.py
```

The server will automatically detect if you have an API key:
- ✅ **With API key:** Uses AI-based clip detection (better results)
- 📝 **Without API key:** Uses simple keyword-based detection (free, but less accurate)

---

## Testing Clip Detection

To test which analyzer is being used:

```bash
# Terminal 1: Start server
python3 backend/server.py

# You should see one of these messages:
# "Using AI-based clip analyzer (GPT)" ← API key found
# "Using simple keyword-based analyzer (no API key found)" ← No key
```

---

## API Key Cost Estimates

Using AI-based detection with `gpt-4o-mini`:
- **Short video (5 min):** ~$0.01-0.02
- **Medium video (15 min):** ~$0.03-0.05
- **Long video (60 min):** ~$0.10-0.20

For 100 videos per month: ~$5-10

---

## Alternative: Use Simple Analyzer (Free)

If you don't want to use OpenAI:
1. **Don't create a `.env` file** or leave `OPENAI_API_KEY` empty
2. The system will automatically use the free keyword-based analyzer
3. Results will be less accurate but still functional

---

## Verify Setup

Test that everything is working:

```python
# test_ai_analyzer.py
import os
from backend.ai_analyzer import AIAnalyzer

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ No API key found in environment")
    print("Set OPENAI_API_KEY environment variable")
    exit(1)

print("✅ API key found!")
print(f"Using model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")

# Test the analyzer
analyzer = AIAnalyzer(
    api_key=api_key,
    model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
)

print("✅ AI Analyzer initialized successfully!")
```

Run it:
```bash
export OPENAI_API_KEY=sk-your-key
python3 test_ai_analyzer.py
```

---

## Troubleshooting

### "No API key found" message
- Make sure you created the `.env` file
- Check that the API key starts with `sk-`
- Verify you loaded the environment variables: `source .env`

### "OpenAI API error"
- Check that your API key is valid
- Verify you have credits in your OpenAI account
- Check your OpenAI usage limits

### "Module not found: openai"
```bash
pip3 install openai
```

---

## Next Steps

- Read `CLIP_DETECTION_GUIDE.md` for detailed comparison of detection methods
- Open http://localhost:5000 in your browser to use the web interface
- Process your first video and compare results with/without AI

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (none) | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | GPT model to use |
| `OPENAI_TEMPERATURE` | `1.0` | AI creativity (0.0-2.0) |

---

## Recommended Configuration

For best results:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini     # Best cost/quality ratio
OPENAI_TEMPERATURE=1.0        # Balanced creativity
```
