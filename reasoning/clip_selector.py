import json
from google import genai
from dotenv import load_dotenv
import os
import re

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

client = genai.Client(api_key=GEMINI_API_KEY)


# ------------ SYSTEM PROMPT (REVISED) ---------------
SYSTEM_PROMPT = """
You are an expert AI video clip selector for short-form content (TikTok, Instagram Reels, YouTube Shorts).
Your job is to analyze a long transcript and select the BEST 30–60 second clip that will go VIRAL.

CRITICAL RULES:
1. **HOOK FIRST** - The clip MUST have a STRONG HOOK within the first 2-3 seconds
2. **COMPLETE ARGUMENT** - Clip must be standalone. Problem -> Analysis -> Conclusion.
3. **NO FILLER** - Remove "um", "uh", boring intros.
4. **VIRAL POTENTIAL** - Choose segments with high emotional or informational value.

OUTPUT FORMAT (JSON):
{
  "start": 12.5,
  "end": 45.8,
  "duration": 33.3,
  "title": "Judul Viral",
  "description": "Deskripsi singkat",
  "hook": "Kalimat pertama",
  "reason": "Kenapa ini viral",
  "viral_score": 8.5,
  "tags": ["tag1", "tag2"],
  "key_insight": "Insight utama"
}
"""

SYSTEM_PROMPT_MULTI = """
You are an expert AI video clip selector. Analyze the transcript and select the BEST 5-10 viral clips.

CRITICAL DURATION RULES:
1. **PREFERRED DURATION**: 45 to 90 seconds (Best for retention & monetization).
2. **MINIMUM DURATION**: 30 seconds (Absolute minimum).
3. **CONTEXT IS KING**: Do not cut a sentence in half just to fit the time. Extend the clip slightly if needed to complete the thought.

NEW RULE FOR MONETIZATION:
4. **ADD VALUE** - For each clip, generate a single, bold, analytical or humorous annotation text that adds unique context or highlights a key moment.

OUTPUT FORMAT (LIST OF JSON):
[
  {
    "start": 10.0,
    "end": 65.0,
    "duration": 55.0,
    "title": "...",
    "description": "...",
    "hook": "...",
    "reason": "...",
    "viral_score": 9.0,
    "tags": [],
    "key_insight": "...",
    "annotation_text": "FAKTA BARU: Sesuatu yang gila terjadi di detik ini.", # <-- FIELD BARU
    "annotation_start_offset": 5.0 # <-- FIELD BARU: Waktu kemunculan (detik), relatif dari start klip.
  },
  ...
]
"""


def select_clip_gemini(transcript_path: str, min_duration=30, max_duration=60):
    """Single clip selection"""
    print("🧠 GEMINI AI REASONING - Selecting best clip...")
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    transcript_text = format_transcript_for_gemini(transcript_data)

    user_input = f"""
TRANSCRIPT DATA:
{transcript_text[:30000]}

REQUIREMENTS:
- Find the single BEST viral clip.
- Duration target: {min_duration}s - {max_duration}s.
- Return ONLY valid JSON.
"""

    chat = client.chats.create(model="gemini-flash-lite-latest")

    try:
        response = chat.send_message(
            SYSTEM_PROMPT + "\n\n" + user_input
        )
        result = parse_gemini_response(response.text)
        # Pass hard_min=15 to prevent crashing on slightly short clips
        validate_clip_selection(result, hard_min_duration=15)
        return result

    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        raise


def select_multi_clips_gemini(transcript_path: str, min_duration=30, max_duration=180, n=10):
    """
    Select multiple viral clips.
    """
    print(f"🧠 GEMINI AI REASONING - Selecting {n} clips...")
    print(f"   Target Duration: {min_duration}s - {max_duration}s")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    transcript_text = format_transcript_for_gemini(transcript_data)

    user_input = f"""
TRANSCRIPT DATA:
{transcript_text[:45000]}

TASK:
- Select {n} distinct viral clips.
- PREFERRED Duration: {min_duration}s to {max_duration}s.
- If a clip is extremely good but slightly shorter ({min_duration-10}s), INCLUDE IT.
- For each clip, generate a **single, bold, analytical or humorous annotation text** that adds context or highlights a key moment.
- Provide the **annotation_start_offset** (time in seconds from the clip start) where this annotation should appear and be displayed for 5 seconds.
- Output strictly a JSON List.
"""

    chat = client.chats.create(model="gemini-flash-lite-latest")
    try:
        response = chat.send_message(
            SYSTEM_PROMPT_MULTI + "\n\n" + user_input
        )
        
        # Parse Response
        response_text = response.text.strip()
        # Clean markdown
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)

        try:
            result = json.loads(response_text)
        except:
            # Fallback regex extraction if JSON is messy
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                raise ValueError("Could not parse JSON list from Gemini response")

        valid_clips = []
        for clip in result:
            if not isinstance(clip, dict): continue
            try:
                # Disini kuncinya: Kita gunakan Hard Limit 15 detik.
                # Biarkan clip 30s-50s lolos meskipun setting di agent_loop 60s.
                validate_clip_selection(clip, hard_min_duration=15)
                valid_clips.append(clip)
            except Exception as e:
                print(f"⚠️  Skipping truly invalid clip: {e}")
        
        print(f"✅ Gemini selected {len(valid_clips)} valid clips.")
        return valid_clips

    except Exception as e:
        print(f"❌ Gemini API error (multi-clip): {e}")
        raise


def format_transcript_for_gemini(transcript_data):
    formatted = []
    for segment in transcript_data.get("segments", []):
        start = segment.get("start", 0.0)
        end = segment.get("end", 0.0)
        text = segment.get("text", "").strip()
        if text:
            formatted.append(f"[{start:.2f}-{end:.2f}] {text}")
    return "\n".join(formatted)


def parse_gemini_response(response_text):
    response_text = response_text.strip()
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'^```\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    
    try:
        return json.loads(response_text)
    except:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Invalid JSON format")


def validate_clip_selection(result, hard_min_duration=15):
    """
    Validasi clip.
    Menggunakan HARD MINIMUM (15s) untuk mencegah crash.
    Parameter min_duration dari function call diabaikan untuk validasi error,
    hanya digunakan sebagai guideline di prompt.
    """
    required_fields = ["start", "end", "title"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing field: {field}")

    if "duration" not in result:
        result["duration"] = result["end"] - result["start"]

    # --- RELAXED VALIDATION LOGIC ---
    duration = result["duration"]
    
    # Kalau di bawah 15 detik, anggap sampah/error
    if duration < hard_min_duration:
        raise ValueError(f"Duration {duration:.2f}s is below hard limit ({hard_min_duration}s)")
    
    # Kalau di bawah 60 detik (tapi di atas 15), cuma kasih warning, JANGAN CRASH
    if duration < 60:
        print(f"   ⚠️ Info: Short clip detected ({duration:.2f}s). Accepted for virality.")

    if result["start"] < 0 or result["end"] <= result["start"]:
        raise ValueError("Invalid timestamps")

    # Defaults
    if "description" not in result: result["description"] = result["title"]
    if "hook" not in result: result["hook"] = result["title"]
    if "viral_score" not in result: result["viral_score"] = 7.0
    if "tags" not in result: result["tags"] = []
    if "key_insight" not in result: result["key_insight"] = result["description"]
    if "annotation_text" not in result: result["annotation_text"] = ""
    if "annotation_start_offset" not in result: result["annotation_start_offset"] = 0.0

    return result
