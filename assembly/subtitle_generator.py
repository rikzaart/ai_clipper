"""
ASS Karaoke Subtitle Generator

Generate ASS subtitle dengan karaoke effect menggunakan word-level timestamps
dari whisper-timestamped.
"""

import json
import copy
from pathlib import Path


def generate_ass_subtitle(transcript_json_path, ass_path):
    """
    Generate ASS karaoke subtitle dari transcript JSON

    Args:
        transcript_json_path: Path ke transcript JSON dengan word-level timestamps
        ass_path: Path ke output ASS file

    Returns:
        ass_path jika berhasil
    """

    print(f"💬 Generating ASS karaoke subtitle...")
    print(f"   Input: {transcript_json_path}")
    print(f"   Output: {ass_path}")

    # Load transcript
    try:
        transcript_json_path = str(Path(transcript_json_path).resolve())
        with open(transcript_json_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading transcript: {e}")
        print(f"   Creating empty subtitle file")
        # Create empty subtitle
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(_get_ass_header())
        return ass_path

    # Check if word-level timestamps exist
    segments = transcript.get("segments", [])
    has_word_timestamps = False

    if segments and len(segments) > 0:
        first_segment = segments[0]
        if "words" in first_segment and len(first_segment.get("words", [])) > 0:
            has_word_timestamps = True

    print(f"   Segments: {len(segments)}")
    print(f"   Word-level timestamps: {'Yes' if has_word_timestamps else 'No'}")

    # Generate ASS content
    ass_content = _get_ass_header()

    if has_word_timestamps:
        # Generate karaoke subtitle with word-level timing
        ass_content += _generate_karaoke_events(segments)
        print(f"   Generated karaoke subtitle with word-level timing")
    else:
        # Fallback to segment-level subtitle
        ass_content += _generate_simple_events(segments)
        print(f"   Generated simple subtitle (no word-level timing)")
        # Fix 4: Join all text if words empty, create one long simple subtitle
        if not has_word_timestamps and len(segments) > 0:
            full_text = " ".join([s.get("text", "").strip() for s in segments if s.get("text")])
            if full_text:
                ass_content += _generate_simple_events([{"start": 0, "end": 60, "text": full_text}])

    # Write to file
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    print(f"✅ Subtitle generated: {ass_path}")

    return ass_path


def _offset_word_timing(words, start_time):
    """Menggeser timestamp kata-kata (word-level) ke belakang."""
    offset_words = []
    for word in words:
        new_word = copy.deepcopy(word)
        # Pastikan tidak ada waktu negatif
        new_word["start"] = max(0.0, word.get("start", 0.0) - start_time)
        new_word["end"] = max(new_word["start"], word.get("end", 0.0) - start_time) 
        offset_words.append(new_word)
    return offset_words


def slice_and_offset_transcript(transcript_json_path, ass_path, clip_start, clip_end):
    """
    Memotong transkrip JSON sesuai durasi klip dan mereset (offset) timestamp-nya.

    Args:
        transcript_json_path: Path ke transcript JSON
        ass_path: Path ke output ASS file
        clip_start: Waktu mulai klip (dalam detik)
        clip_end: Waktu akhir klip (dalam detik)

    Returns:
        ass_path jika berhasil
    """
    print(f"💬 Slicing & Offseting transcript for clip...")
    print(f"   Input: {transcript_json_path}")
    print(f"   Output: {ass_path}")
    print(f"   Clip Range: {clip_start:.2f}s - {clip_end:.2f}s")

    try:
        transcript_json_path = str(Path(transcript_json_path).resolve())
        with open(transcript_json_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading transcript: {e}")
        print(f"   Creating empty subtitle file")
        # Create empty subtitle
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(_get_ass_header())
        return ass_path

    # 1. SLICING: Filter segments yang masuk dalam clip
    segments = full_data.get("segments", [])
    clipped_segments = []
    
    for segment in segments:
        seg_start = segment.get("start", 0.0)
        seg_end = segment.get("end", 0.0)

        # Hanya ambil segment yang bersinggungan/masuk dalam clip
        if seg_end > clip_start and seg_start < clip_end:
            new_segment = copy.deepcopy(segment)

            # 2. OFFSET: Geser waktu
            new_segment["start"] = max(0.0, seg_start - clip_start)
            new_segment["end"] = min(clip_end - clip_start, seg_end - clip_start)
            
            # Geser waktu di level word-level juga (penting untuk karaoke)
            if "words" in new_segment:
                valid_words = []
                for word in new_segment["words"]:
                    w_start = word.get("start", 0.0)
                    w_end = word.get("end", 0.0)
                    if w_end > clip_start and w_start < clip_end:
                        word["start"] = max(0.0, w_start - clip_start)
                        word["end"] = max(word["start"], w_end - clip_start)
                        valid_words.append(word)
                new_segment["words"] = valid_words

            clipped_segments.append(new_segment)

    # Check if word-level timestamps exist
    has_word_timestamps = False
    if clipped_segments and len(clipped_segments) > 0:
        first_segment = clipped_segments[0]
        if "words" in first_segment and len(first_segment.get("words", [])) > 0:
            has_word_timestamps = True

    print(f"   Segments after clipping: {len(clipped_segments)}")
    print(f"   Word-level timestamps: {'Yes' if has_word_timestamps else 'No'}")

    # 3. GENERATE ASS dari data yang sudah dipotong
    ass_content = _get_ass_header()
    
    if has_word_timestamps:
        ass_content += _generate_karaoke_events(clipped_segments)
        print(f"   Generated karaoke subtitle with word-level timing")
    else:
        ass_content += _generate_simple_events(clipped_segments)
        print(f"   Generated simple subtitle (no word-level timing)")
         
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
        
    print(f"✅ Subtitle saved & synced: {ass_path}")
    return ass_path


def _get_ass_header():
    """Generate ASS file header dengan dua style font (Normal & Emphasis), tanpa outline, dan posisi subtitle center bawah"""
    return """[Script Info]
Title: AI Agent Short Video
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Normal,Alte Haas Grotesk,100,&H00E0FAFE,&H00CAFD,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,0,0,2,60,60,300,1
Style: Emphasis,Apple Garamond,110,&H00CDEDFA,&H00CAFD,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,0,0,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _generate_karaoke_events(segments, max_words_per_line=7, max_duration=2.5, time_offset=0.12):
    """
    Generate karaoke events dengan word-level timing, chunking, dua style font, dan posisi center bawah
    """
    events = []
    # Center bawah: x=540 (tengah), y=1500 (agak bawah, bisa disesuaikan)
    pos_x = 540
    pos_y = 1500
    pos_tag = f"{{\\pos({pos_x},{pos_y})}}"
    for segment in segments:
        words = segment.get("words", [])
        if not words or len(words) == 0:
            continue
        chunks = _chunk_words(words, max_words_per_line, max_duration)
        for chunk in chunks:
            if not chunk:
                continue
            chunk_start = chunk[0].get("start", 0.0) + time_offset
            chunk_end = chunk[-1].get("end", 0.0) + time_offset
            karaoke_text = pos_tag
            for word in chunk:
                word_text = word.get("text", "").strip()
                word_start = word.get("start", 0.0)
                word_end = word.get("end", 0.0)
                duration_cs = int((word_end - word_start) * 100)
                if duration_cs < 10:
                    duration_cs = 10
                if word_text.isupper() and len(word_text) > 1:
                    karaoke_text += f"{{\\rEmphasis}}{{\\k{duration_cs}}}{word_text}{{\\rNormal}} "
                else:
                    karaoke_text += f"{{\\k{duration_cs}}}{word_text} "
            start_formatted = _format_timestamp(chunk_start)
            end_formatted = _format_timestamp(chunk_end)
            dialogue = f"Dialogue: 0,{start_formatted},{end_formatted},Normal,,0,0,0,,{karaoke_text.strip()}\n"
            events.append(dialogue)
    return "".join(events)


def _chunk_words(words, max_words, max_duration):
    """
    Chunk words into smaller groups berdasarkan:
    - Max words per line
    - Max duration per line
    - Natural pauses (punctuation)

    Returns:
        List of word chunks
    """
    chunks = []
    current_chunk = []

    for i, word in enumerate(words):
        current_chunk.append(word)

        # Check if we should break
        should_break = False

        # Break if max words reached
        if len(current_chunk) >= max_words:
            should_break = True

        # Break if max duration reached
        if current_chunk:
            chunk_duration = current_chunk[-1].get("end", 0.0) - current_chunk[0].get("start", 0.0)
            if chunk_duration >= max_duration:
                should_break = True

        # Break at punctuation
        word_text = word.get("text", "").strip()
        if word_text.endswith((",", ".", "!", "?", "ya", "gitu", "nih")):
            should_break = True

        # Break if this is the last word
        if i == len(words) - 1:
            should_break = True

        if should_break and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []

    return chunks


def _generate_simple_events(segments):
    """
    Generate simple subtitle events (fallback tanpa word-level timing)
    """
    events = []

    for segment in segments:
        text = segment.get("text", "").strip()
        start_time = segment.get("start", 0.0)
        end_time = segment.get("end", 0.0)

        if not text:
            continue

        # Format timestamps
        start_formatted = _format_timestamp(start_time)
        end_formatted = _format_timestamp(end_time)

        # Create dialogue line
        dialogue = f"Dialogue: 0,{start_formatted},{end_formatted},Default,,0,0,0,,{text}\n"
        events.append(dialogue)

    return "".join(events)


def _format_timestamp(seconds):
    """
    Format timestamp untuk ASS format: H:MM:SS.CS

    Args:
        seconds: Time dalam detik (float)

    Returns:
        Formatted string (e.g., "0:01:23.45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)

    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"