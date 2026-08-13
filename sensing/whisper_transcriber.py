import subprocess
import json
import os
import re
from pathlib import Path
import srt

# === PATH CONFIGURATION (M4 OPTIMIZED) ===
CURRENT_FILE = Path(__file__).resolve()
SENSING_DIR = CURRENT_FILE.parent
PROJECT_ROOT = SENSING_DIR.parent 

# Folder whisper.cpp ada di root project
WHISPER_CPP_DIR = PROJECT_ROOT / "whisper.cpp"

# Binary Location
BIN_PATH = WHISPER_CPP_DIR / "build" / "bin"
WHISPER_EXEC = BIN_PATH / "whisper-cli"

# Model Location (Large V3 Turbo)
MODEL_PATH = WHISPER_CPP_DIR / "models" / "ggml-large-v3-turbo.bin"

# === DEBUG PATH ===
print(f"-------- M4 WHISPER CONFIG --------")
print(f"Project Root    : {PROJECT_ROOT}")
print(f"Whisper Binary  : {WHISPER_EXEC}")
print(f"Model Path      : {MODEL_PATH}")
print(f"Binary Ready?   : {WHISPER_EXEC.exists()}")
print(f"-----------------------------------")

def extract_audio(video_path, audio_path):
    """
    FFmpeg Safe Mode.
    Mengubah video ke WAV format 'Canonical' (16kHz, Mono, 16-bit).
    """
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite
        "-i", video_path,   # Input
        "-vn",              # No Video
        "-ac", "1",         # Mono (Wajib)
        "-ar", "16000",     # 16kHz (Wajib)
        "-c:a", "pcm_s16le",# 16-bit Integer
        "-f", "wav",        # Container WAV
        str(audio_path)
    ]
    
    print(f"🎤 [M4-Job] Extracting Audio: {audio_path}")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error: {e.stderr.decode()}")
        raise Exception("Gagal ekstraksi audio via FFmpeg.")

    if not Path(audio_path).exists() or os.path.getsize(audio_path) < 100:
        raise Exception(f"File audio kosong/korup: {audio_path}")
        
    print(f"✅ Audio Ready.")

def parse_whisper_timestamp(ts_str):
    """Mengubah format '00:00:01,000' menjadi float seconds."""
    try:
        h, m, s = ts_str.split(':')
        s, ms = s.split(',')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    except:
        return 0.0

def _get_all_words_flat(segments, time_offset=0.0):
    """
    Mengambil semua kata dari SRT segments ke dalam satu list datar dengan estimasi timing.
    """
    all_words = []
    
    for seg in segments:
        seg_text = seg.content.replace('\n', ' ').strip()
        start_sec = seg.start.total_seconds()
        end_sec = seg.end.total_seconds()
        
        words = seg_text.split()
        if not words:
            continue
            
        # Estimasi timing yang lebih ketat (membagi durasi segmen ke setiap kata)
        avg_duration_per_word = (end_sec - start_sec) / len(words)
        current_time = start_sec
        
        for word_text in words:
            word_end_time = current_time + avg_duration_per_word
            
            all_words.append({
                "text": word_text,
                "start": round(current_time + time_offset, 2),
                "end": round(word_end_time + time_offset, 2),
                "confidence": 0.99 
            })
            current_time = word_end_time
            
    return all_words


def _rechunk_srt_to_data(srt_path, pause_threshold=0.35):
    """
    Membaca SRT, mengekstrak kata-kata, dan ME-RECHUNK menjadi segmen
    berdasarkan jeda bicara (pause_threshold) dan tanda baca akhir kalimat.
    """
    final_data = {
        "text": "",
        "segments": [],
        "language": "id"
    }

    try:
        segments_srt = srt.parse(Path(srt_path).read_text(encoding="utf-8"))
    except:
        print("⚠️ SRT parsing failed. Check file encoding.")
        return final_data

    # 1. First Pass: Kumpulkan semua kata ke list datar dengan estimasi timing
    all_words = _get_all_words_flat(segments_srt) 
    
    if not all_words:
        return final_data
    
    # 2. Second Pass: Re-chunking cerdas
    current_segment_words = []
    
    for i, word in enumerate(all_words):
        current_segment_words.append(word)

        should_break = False
        
        # Cek Jeda (Pause Threshold)
        if i < len(all_words) - 1:
            next_word_start = all_words[i+1]['start']
            current_word_end = word['end']
            pause_duration = next_word_start - current_word_end
            
            # Aturan 1: Jika jeda signifikan (misalnya 0.35 detik)
            if pause_duration >= pause_threshold:
                should_break = True
                
        # Aturan 2: Break pada tanda baca akhir kalimat (selalu membuat break, terlepas dari jeda)
        # Kita gunakan .strip() untuk memastikan tanda baca ada di akhir kata (hasil Whisper)
        if word["text"].strip().endswith((".", "?", "!", ":", ";")):
            should_break = True

        # Eksekusi Break
        if should_break and current_segment_words:
            final_data["segments"].append(_create_final_segment(current_segment_words))
            current_segment_words = [] 

    # Proses segmen terakhir
    if current_segment_words:
        final_data["segments"].append(_create_final_segment(current_segment_words))
        
    # Re-construct full text dan simpan
    final_data["text"] = _get_segment_text(all_words)
    
    return final_data # HANYA me-return data


def _create_final_segment(words):
    """Membuat segmen JSON dari list kata."""
    text = _get_segment_text(words)
    return {
        "start": words[0]["start"],
        "end": words[-1]["end"],
        "text": text,
        "words": words
    }

def _get_segment_text(words):
    """Menggabungkan teks dari list kata menjadi satu string."""
    return " ".join([w["text"] for w in words]).strip()

def fmt_time_ass(seconds):
    """Format waktu detik ke ASS (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def create_ass_file(json_data, ass_path, title="Video"):
    """
    Generate file subtitle .ass yang persis seperti sample test-030.ass.
    Menggunakan format event Dialogue standar.
    """
    header = f"""[Script Info]
Title: {title}
ScriptType: v4.00+

[V4+ Styles]
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,10

[Events]
"""
    try:
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            segments = json_data.get("segments", [])
            for seg in segments:
                start = fmt_time_ass(seg.get("start", 0))
                end = fmt_time_ass(seg.get("end", 0))
                text = seg.get("text", "").strip()
                if text:
                    f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,, {text}\n")
        print(f"📝 ASS Subtitle saved: {ass_path}")
    except Exception as e:
        print(f"⚠️ Gagal membuat ASS: {e}")

def whisper_transcribe(audio_path, out_json, fast_mode=True):
    # Validasi File
    if not WHISPER_EXEC.exists():
        raise FileNotFoundError(f"❌ Binary Whisper tidak ditemukan di: {WHISPER_EXEC}\nSilakan jalankan langkah build ulang.")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"❌ Model tidak ditemukan di: {MODEL_PATH}")

    audio_path = Path(audio_path)
    output_stem_path = audio_path.parent / audio_path.stem
    srt_path = output_stem_path.with_suffix(".srt")

    # COMMAND OPTIMAL UNTUK M4 CHIP
    # Note: Kita gunakan -owts (output word timestamps) untuk mendapatkan 'tokens' di JSON
    cmd = [
        str(WHISPER_EXEC),
        "-m", str(MODEL_PATH),
        "-f", str(audio_path),
        "-l", "id",       
        "-t", "8",        
        "-osrt",            # PENTING: Output SRT
        "-sow",             # PENTING: Split on word (Membuat baris SRT sangat pendek)
        "-ml", "1",         # Max token length 1 (untuk timing token/kata)
        "-of", str(output_stem_path),
        "-np",            
        "--prompt", "Gunakan bahasa Indonesia formal dan gaul."
    ]

    print(f"🚀 [M4-Job] Transcribing (SRT Word-Level Mode)...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Cek Error
    if result.returncode != 0:
        if result.returncode == 10:
            print("❌ Error 10: Format WAV invalid. Pastikan extract_audio berjalan benar.")
        else:
            print(f"❌ Whisper Error Code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
        raise Exception("Transkripsi Whisper gagal.")

    # 1. Parsing SRT
    if not srt_path.exists():
        raise FileNotFoundError("Whisper selesai tapi SRT output tidak muncul.")

    print(f"📝 Parsing SRT output...")
    
    # 2. KONVERSI STRUKTUR ke JSON standar Anda (memanggil fungsi baru)
    # PENTING: Panggil _rechunk_srt_to_data (tanpa argumen out_json)
    final_data = _rechunk_srt_to_data(srt_path)

    # 3. Simpan JSON Final 
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON (Standardized from SRT) saved: {out_json}")
    
    # 4. Generate ASS
    ass_path = Path(out_json).with_suffix(".ass")
    create_ass_file(final_data, ass_path, title=audio_path.stem)

    return final_data

if __name__ == "__main__":
    pass