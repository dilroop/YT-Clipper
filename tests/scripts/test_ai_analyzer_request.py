"""
Test script to show OpenAI API request format and prompt
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Example transcript segments (simplified)
example_segments = [
    {
        'start': 10.5,
        'end': 15.2,
        'text': 'So the interesting thing about artificial intelligence is that',
        'words': [
            {'word': 'So', 'start': 10.5, 'end': 10.8},
            {'word': 'the', 'start': 10.8, 'end': 11.0},
            {'word': 'interesting', 'start': 11.0, 'end': 11.6},
            {'word': 'thing', 'start': 11.6, 'end': 11.9},
        ]
    },
    {
        'start': 15.2,
        'end': 20.8,
        'text': 'it can actually understand context in ways we never imagined before',
        'words': []
    },
    {
        'start': 20.8,
        'end': 25.5,
        'text': 'and this is going to completely change how we work',
        'words': []
    }
]

video_info = {
    'title': 'The Future of AI Technology',
    'description': 'A discussion about artificial intelligence and its impact on society'
}

print("=" * 80)
print("OPENAI API REQUEST EXAMPLE")
print("=" * 80)

# Show the system prompt
print("\n1. SYSTEM PROMPT GENERATED:")
print("-" * 80)

system_prompt = f"""You are a professional video editor for short-form content (TikTok/Reels/Shorts). From the following video transcript with timestamps, select 5 segments that would make the most engaging clips.

VIDEO INFO:
- Title: {video_info['title']}
- Description: {video_info['description'][:500]}

Selection criteria for good clips:
- Punchlines or funny moments
- Interesting insights or information
- Emotional or dramatic moments
- Memorable quotes
- Complete topics (with beginning, middle, end)
- Hooks or intriguing questions
- Surprising revelations or plot twists

⚠️ DURATION RULES - VERY IMPORTANT:
- Each clip MUST be between 15 and 60 seconds
- TARGET duration: 37 seconds

Return response in JSON format:
[
  {{
    "start_time": "00:01:23.000",
    "end_time": "00:01:45.000",
    "title": "Short descriptive title",
    "reason": "Why this is interesting",
    "keywords": ["keyword1", "keyword2"]
  }}
]

Return ONLY the JSON array, no other text."""

print(system_prompt)

# Show the transcript format
print("\n2. TRANSCRIPT FORMAT SENT TO GPT:")
print("-" * 80)

transcript_lines = []
for segment in example_segments:
    # Format timestamps
    start_h = int(segment['start'] // 3600)
    start_m = int((segment['start'] % 3600) // 60)
    start_s = int(segment['start'] % 60)
    start_ms = int((segment['start'] % 1) * 1000)
    start_time = f"{start_h:02d}:{start_m:02d}:{start_s:02d}.{start_ms:03d}"

    end_h = int(segment['end'] // 3600)
    end_m = int((segment['end'] % 3600) // 60)
    end_s = int(segment['end'] % 60)
    end_ms = int((segment['end'] % 1) * 1000)
    end_time = f"{end_h:02d}:{end_m:02d}:{end_s:02d}.{end_ms:03d}"

    transcript_lines.append(f"[{start_time} - {end_time}] {segment['text']}")

transcript = "\n".join(transcript_lines)
print(transcript)

# Show the full prompt
print("\n3. FULL PROMPT SENT TO OPENAI API:")
print("-" * 80)
full_prompt = f"{system_prompt}\n\nTranscript:\n{transcript}"
print(full_prompt)

# Show the API call structure
print("\n4. OPENAI API CALL STRUCTURE:")
print("-" * 80)
print("""
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4o-mini",              # or "gpt-4"
    messages=[
        {
            "role": "user",
            "content": full_prompt    # The prompt shown above
        }
    ],
    temperature=1.0,                  # Creativity level (0.0-2.0)
)

# Extract the response
result = response.choices[0].message.content
""")

# Show example GPT response
print("\n5. EXAMPLE GPT RESPONSE:")
print("-" * 80)
print("""
[
  {
    "start_time": "00:00:10.500",
    "end_time": "00:00:25.500",
    "title": "AI Understanding Context",
    "reason": "Explains a key insight about AI capabilities with complete thought",
    "keywords": ["artificial intelligence", "context", "understanding"]
  }
]
""")

# Actually call the API if key is available
api_key = os.getenv('OPENAI_API_KEY')
if api_key and api_key.startswith('sk-'):
    print("\n6. ACTUAL API CALL (LIVE):")
    print("-" * 80)
    print("Making real API call to OpenAI...\n")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0')),
        )

        result = response.choices[0].message.content
        print("✅ API Response:")
        print(result)

        print(f"\n📊 Token Usage:")
        print(f"   Input tokens:  {response.usage.prompt_tokens}")
        print(f"   Output tokens: {response.usage.completion_tokens}")
        print(f"   Total tokens:  {response.usage.total_tokens}")

        # Calculate cost (for gpt-4o-mini)
        input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.15
        output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
        total_cost = input_cost + output_cost
        print(f"\n💰 Estimated Cost:")
        print(f"   Input:  ${input_cost:.6f}")
        print(f"   Output: ${output_cost:.6f}")
        print(f"   Total:  ${total_cost:.6f}")

    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("\n❌ No API key found - skipping live call")
    print("Set OPENAI_API_KEY in .env file to see live API response")

print("\n" + "=" * 80)
print("For a real video, the transcript would be much longer (100-500 lines)")
print("and GPT would analyze the entire context to find the best moments!")
print("=" * 80)
