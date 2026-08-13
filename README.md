# 🤖 AI Agent Short Videos - Auto Editor

Agent otomatis untuk mengubah video YouTube panjang menjadi video short vertical dengan **Gemini AI reasoning** untuk intelligent clip selection.

## 🎯 Fitur Utama

### ✨ NEW: Gemini AI Integration
- 🧠 **Intelligent Clip Selection** - Gemini 1.5 Flash analyzes transcript and selects best 20-60s clip
- 🎯 **Strong Hook Detection** - AI finds clips with powerful hooks in first 2-3 seconds
- 📊 **Viral Score** - AI calculates viral potential (1-10 score)
- 📝 **Auto Title & Description** - AI generates engaging titles in Indonesian informal style
- 🏷️ **Smart Tags** - AI suggests relevant tags for better discoverability

### 🎬 Complete Video Processing Pipeline

#### STEP 1: YouTube Download
- ✅ Download video from YouTube with cookie authentication
- ✅ Support for age-restricted and private videos

#### STEP 2: Audio Transcription (OPTIMIZED - 3-4x faster!)
- ✅ Extract audio with single-pass FFmpeg (3-5x faster)
- ✅ Whisper Medium model (3-5x faster than large-v3-turbo)
- ✅ Word-level timestamps with confidence scores
- ✅ Optimized parameters (beam=3, temp=0.0)
- ✅ Aggressive noise reduction for better accuracy
- ✅ Indonesian informal language support (gue, lu, kayak, banget)

#### STEP 3: 🧠 Gemini AI Reasoning (NEW!)
- ✅ Analyze full transcript for best clip
- ✅ Find strong hooks (questions, shocking statements, bold claims)
- ✅ Ensure complete story (standalone clip)
- ✅ Calculate viral potential (1-10 score)
- ✅ Generate title & description (Indonesian informal)
- ✅ Suggest relevant tags

#### STEP 4: Face Detection
- ✅ YOLOv8 face detection for smart cropping
- ✅ Sample 20 frames for accurate tracking
- ✅ Confidence threshold optimization

#### STEP 5: Dynamic Crop Calculation
- ✅ Smart crop based on face positions
- ✅ EMA motion smoothing for stable tracking
- ✅ Fallback to center crop if no faces detected
- ✅ 9:16 aspect ratio (1080x1920)

#### STEP 6: Karaoke Subtitle Generation
- ✅ ASS format with word-level karaoke effect
- ✅ Sentence chunking (max 7 words, max 2.5s)
- ✅ Time offset (+0.12s) for perfect sync
- ✅ Styling: Arial Black, orange secondary color, outline, shadow

#### STEP 7: Video Rendering
- ✅ FFmpeg rendering with Gemini's selected clip timing
- ✅ Dynamic crop (face-tracking)
- ✅ Karaoke subtitles
- ✅ **Fujifilm Vintage Cinematic color grading** (natural, film-like)
- ✅ 1080x1920 vertical format

#### STEP 8: Google Drive Upload
- ✅ Upload raw video to Drive
- ✅ Upload finished video to Drive
- ✅ Return file IDs for tracking

#### STEP 9: Google Sheets Update
- ✅ Update status to "done"
- ✅ Save raw_file_id and finished_file_id
- ✅ **Save Gemini metadata** (title, description, viral_score)

## 📋 Requirements

```bash
pip install -r requirements.txt
```

### Key Dependencies:
- `openai-whisper` - Audio transcription (Medium model for speed)
- `whisper-timestamped` - Word-level timestamps
- `torchaudio` - Required for VAD (Voice Activity Detection)
- `google-generativeai` - **Gemini AI API** (intelligent clip selection)
- `yt-dlp` - YouTube downloader with cookie support
- `ultralytics` - YOLOv8 face detection
- `opencv-python` - Video processing
- `google-api-python-client` - Google Drive & Sheets API
- `ffmpeg` - Video rendering (install separately)

## 🚀 Setup & Installation

### 1. Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from: https://ffmpeg.org/download.html
```

### 2. Setup Google Cloud Credentials

Buat file `credentials.json` dari Google Cloud Console dengan akses ke:
- Google Drive API
- Google Sheets API

Run authentication:
```bash
python auth.py
```

### 3. Setup Gemini AI API Key

1. Get API key from: https://aistudio.google.com/app/apikey
2. Create `.env` file:

```bash
cp .env.example .env
```

3. Edit `.env` and add your API key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Setup Google Sheets

Format spreadsheet (sheet "Jobs"):

| Column | Field | Description | Source |
|--------|-------|-------------|--------|
| A | job_id | Unique job ID | Manual |
| B | youtube_url | YouTube URL | Manual |
| C | raw_file_id | Raw video Drive ID | Agent |
| D | finished_file_id | Finished video Drive ID | Agent |
| E | status | pending/processing/done/error | Agent |
| **F** | **title** | **Gemini-generated title** | **Gemini AI** ✨ |
| **G** | **description** | **Gemini-generated description** | **Gemini AI** ✨ |
| **H** | **viral_score** | **Viral potential (1-10)** | **Gemini AI** ✨ |
- Column L: updated_at (timestamp)

### 3. Jalankan Agent

```bash
python agent.py
```

Agent akan:
1. Monitor Google Sheets setiap 5 detik
2. Ambil job dengan status "downloading" dan assigned_to "mac_local"
3. Process video secara otomatis
4. Update status ke "done" atau "error"

## 📁 Struktur Folder

```
.
├── agent.py              # Main agent script
├── credentials.json      # Google API credentials
├── token.json           # OAuth token (auto-generated)
├── requirements.txt     # Python dependencies
├── raw/                 # Downloaded videos
├── temp/                # Temporary files & transcripts
└── finished/            # Final edited videos
```

## 🎨 Caption Styling

Caption menggunakan styling yang menarik:
- Font: Arial Bold
- Size: 60px
- Color: White
- Stroke: Black (3px)
- Position: Bottom area (75% dari atas)
- Width: Full width dengan padding 50px kiri-kanan

## 🔧 Customization

### Ubah Scene Detection Threshold
```python
scenes = detect_scenes(raw_path, threshold=27.0)  # Default: 27.0
```

### Ubah Durasi Scene
```python
best_scene = select_best_scene(scenes, min_duration=10, max_duration=60)
```

### Ubah Video Resolution
```python
vertical_clip = reframe_to_vertical(raw_path, target_width=1080, target_height=1920)
```

### Ubah Caption Style
Edit fungsi `create_caption_clip()` di `agent.py`

## 📊 Workflow

```
YouTube URL → Download → Transcribe → Scene Detect → Reframe → Add Captions → Export → Upload → Done
```

## 🐛 Troubleshooting

### Error: "No module named 'scenedetect'"
```bash
pip install scenedetect[opencv]
```

### Error: "MoviePy import error"
Pastikan menggunakan MoviePy 2.x:
```bash
pip install moviepy==2.0.0
```

### Error: "Failed to load audio: No such file or directory"
Ini terjadi karena yt-dlp mendownload file dengan ekstensi berbeda (.webm instead of .mp4).
Agent sudah otomatis mendeteksi file yang sebenarnya, tapi jika masih error:
1. Check folder `raw/` untuk melihat file yang terdownload
2. Pastikan ffmpeg terinstall: `brew install ffmpeg` (macOS)

### Error: "cannot import name 'crop' from 'moviepy.video.fx'"
Update ke MoviePy 2.x yang menggunakan method `cropped()` bukan `crop()`:
```bash
pip install --upgrade moviepy
```

### Video terlalu gelap/terang
Adjust scene detection threshold (nilai lebih tinggi = lebih sensitif)

## 📝 License

MIT License

