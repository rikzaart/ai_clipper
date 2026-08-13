"""
Video Renderer dengan FFmpeg

Render final video dengan:
- Dynamic crop (focus ke wajah)
- Resize ke vertical 9:16 (1080x1920)
- Karaoke subtitle overlay
- Color grading (cinematic look)
- Optimal encoding settings
"""

import os
import subprocess


class FFmpegRenderError(Exception):
    pass


# Color Grading Presets - Fujifilm Vintage Cinematic Style
COLOR_GRADING_PRESETS = {
    "none": None,

    "fujifilm": {
        "name": "Fujifilm Classic (Vintage Cinematic)",
        "filters": [
            # Step 1: Lift blacks (faded shadows) - signature Fujifilm look
            "curves=r='0/0.05 0.5/0.5 1/1':g='0/0.05 0.5/0.5 1/1':b='0/0.08 0.5/0.5 1/1'",

            # Step 2: Subtle contrast & muted saturation (natural, not oversaturated)
            "eq=contrast=1.08:brightness=0.01:saturation=0.92",

            # Step 3: Warm color shift (Fujifilm warm tones)
            "colorbalance=rs=0.08:gs=0.02:bs=-0.06:rm=0.04:gm=-0.01:bm=-0.03:rh=0.02:gh=-0.01:bh=-0.02",

            # Step 4: Soft highlights (prevent blown out whites)
            "curves=master='0/0 0.7/0.75 1/0.98'",

            # Step 5: Film grain (subtle texture)
            "noise=alls=3:allf=t+u",
        ]
    },

    "fujifilm_pro400h": {
        "name": "Fujifilm Pro 400H (Pastel & Soft)",
        "filters": [
            # Lifted blacks (very faded)
            "curves=r='0/0.08 0.5/0.52 1/1':g='0/0.08 0.5/0.5 1/1':b='0/0.1 0.5/0.5 1/1'",

            # Low contrast, desaturated (pastel look)
            "eq=contrast=1.05:brightness=0.03:saturation=0.88",

            # Slight green/yellow shift (Pro 400H signature)
            "colorbalance=rs=0.05:gs=0.04:bs=-0.08:rm=0.02:gm=0.02:bm=-0.04:rh=0:gh=0.01:bh=-0.02",

            # Soft highlights
            "curves=master='0/0 0.8/0.85 1/0.98'",

            # Fine grain
            "noise=alls=2:allf=t+u",
        ]
    },

    "fujifilm_velvia": {
        "name": "Fujifilm Velvia (Rich & Vibrant)",
        "filters": [
            # Slight lifted blacks (not too much)
            "curves=r='0/0.03 0.5/0.5 1/1':g='0/0.03 0.5/0.5 1/1':b='0/0.04 0.5/0.5 1/1'",

            # Higher saturation but natural (Velvia signature)
            "eq=contrast=1.12:brightness=0.02:saturation=1.08",

            # Rich warm tones (reds & oranges pop)
            "colorbalance=rs=0.1:gs=0:bs=-0.08:rm=0.06:gm=-0.02:bm=-0.05:rh=0.03:gh=-0.02:bh=-0.03",

            # Punchy contrast curve
            "curves=master='0/0 0.3/0.25 0.7/0.78 1/1'",

            # Minimal grain
            "noise=alls=1:allf=t+u",
        ]
    },

    "fujifilm_superia": {
        "name": "Fujifilm Superia (Everyday Natural)",
        "filters": [
            # Moderate lifted blacks
            "curves=r='0/0.04 0.5/0.5 1/1':g='0/0.04 0.5/0.5 1/1':b='0/0.06 0.5/0.5 1/1'",

            # Balanced, natural look
            "eq=contrast=1.06:brightness=0.02:saturation=0.95",

            # Slight warm shift (natural skin tones)
            "colorbalance=rs=0.06:gs=0.01:bs=-0.05:rm=0.03:gm=0:bm=-0.03:rh=0.01:gh=0:bh=-0.01",

            # Gentle contrast
            "curves=master='0/0 0.5/0.52 1/0.99'",

            # Medium grain
            "noise=alls=2.5:allf=t+u",
        ]
    },

    "kodak_portra": {
        "name": "Kodak Portra (Natural Skin Tones)",
        "filters": [
            # Lifted blacks (faded film look)
            "curves=r='0/0.06 0.5/0.5 1/1':g='0/0.06 0.5/0.5 1/1':b='0/0.08 0.5/0.5 1/1'",

            # Low contrast, muted saturation (Portra signature)
            "eq=contrast=1.04:brightness=0.02:saturation=0.9",

            # Warm, flattering skin tones
            "colorbalance=rs=0.07:gs=0.03:bs=-0.07:rm=0.04:gm=0.01:bm=-0.04:rh=0.02:gh=0:bh=-0.02",

            # Soft, gentle curve
            "curves=master='0/0 0.6/0.65 1/0.98'",

            # Fine grain
            "noise=alls=2:allf=t+u",
        ]
    },

    "cinestill_800t": {
        "name": "CineStill 800T (Cinematic Night)",
        "filters": [
            # Lifted blacks (halation effect)
            "curves=r='0/0.07 0.5/0.5 1/1':g='0/0.07 0.5/0.5 1/1':b='0/0.09 0.5/0.5 1/1'",

            # Moderate contrast, slightly desaturated
            "eq=contrast=1.1:brightness=0.01:saturation=0.93",

            # Cool tones with warm highlights (tungsten balanced)
            "colorbalance=rs=-0.03:gs=-0.02:bs=0.08:rm=-0.02:gm=-0.01:bm=0.05:rh=0.05:gh=0.02:bh=-0.03",

            # Cinematic curve
            "curves=master='0/0 0.4/0.38 0.7/0.75 1/0.99'",

            # Visible grain (800 ISO)
            "noise=alls=4:allf=t+u",
        ]
    },

    "natural": {
        "name": "Natural (Minimal Grading)",
        "filters": [
            # Very subtle lifted blacks
            "curves=r='0/0.02 0.5/0.5 1/1':g='0/0.02 0.5/0.5 1/1':b='0/0.03 0.5/0.5 1/1'",

            # Minimal adjustments (natural look)
            "eq=contrast=1.03:brightness=0.01:saturation=0.98",

            # Barely noticeable warm shift
            "colorbalance=rs=0.02:gs=0:bs=-0.02:rm=0.01:gm=0:bm=-0.01:rh=0:gh=0:bh=0",

            # No grain
        ]
    },

    "the_batman_2022": {
    "name": "The Batman 2022 – Gotham Nights (Moody Neo-Noir)",
    "filters": [
        # 1. S-curve contrast + slight blacks lift (deep shadows tapi legible)
        "curves=r='0/0.02 0.15/0.08 0.5/0.50 1/1':g='0/0.02 0.15/0.09 0.5/0.50 1/1':b='0/0.03 0.15/0.12 0.5/0.50 1/1'",

        # 2. Balanced contrast + lift (kurangi gelap, dusty desat)
        "eq=contrast=1.25:brightness=0.02:saturation=0.84",

        # 3. Teal shadows + orange highlights (subtle, preserve warmth)
        "colorbalance=rs=-0.02:gs=0.03:bs=0.12:rm=-0.01:gm=0.02:bm=0.06:rh=0.12:gh=0.03:bh=-0.04",

        # 4. Mids teal push (balance blue, red mix untuk skin)
        "colorchannelmixer=bb=1.12:br=1.08",

        # 5. Highlights roll-off (prevent blown, preserve details)
        "curves=master='0/0 0.25/0.20 0.75/0.85 1/0.98'",

        # 6. 35mm grain + halation (halus, tidak noisy)
        "noise=alls=4:allf=t+u+p",
        "unsharp=5:5:-0.5",

        # 7. Vignette (fix: uppercase PI, lebih strong untuk Gotham edges)
        "vignette=angle=PI/4"
    ]
},
}


def render_final_video(
    input_path,
    start_time,
    end_time,
    output_path,
    crop_params=None,
    subtitle_path=None,
    target_width=1080,
    target_height=1920,
    color_grading="kodak_portra",
    annotation_text=None,
    annotation_start_offset=5.0,
    audio_path=None  # Tambahkan parameter audio_path
):
    """
    Render final video dengan FFmpeg

    Args:
        input_path: Path ke input video
        start_time: Start time dalam detik
        end_time: End time dalam detik
        output_path: Path ke output video
        crop_params: Dict dengan crop parameters {x, y, width, height}
        subtitle_path: Path ke subtitle file (.ass)
        target_width: Target width (default: 1080)
        target_height: Target height (default: 1920)
        color_grading: Color grading preset (default: "kodak_portra")
        Options: "none", "fujifilm", "fujifilm_pro400h", "fujifilm_velvia",
        "fujifilm_superia", "kodak_portra", "cinestill_800t", "natural", "the_batman_2022"
        annotation_text: Text untuk annotation (default: None)
        annotation_start_offset: Offset waktu untuk annotation dalam detik (default: 5.0)
        audio_path: Path ke audio file (.wav) (default: None)

    Returns:
        output_path jika berhasil
    """

    print("🎬 Rendering video with FFmpeg...")
    print(f"   Input: {input_path}")
    print(f"   Output: {output_path}")
    print(f"   Duration: {start_time:.2f}s - {end_time:.2f}s")

    # Get color grading preset
    if color_grading and color_grading in COLOR_GRADING_PRESETS:
        grading_preset = COLOR_GRADING_PRESETS[color_grading]
        if grading_preset:
            print(f"   Color Grading: {grading_preset['name']}")
        else:
            print("   Color Grading: None")
    else:
        print(f"   Color Grading: None (invalid preset: {color_grading})")
        grading_preset = None

    # Build video filter chain
    vf_filters = []

    # 1. Crop filter (if provided)
    if crop_params:
        crop_w = crop_params.get("width", target_width)
        crop_h = crop_params.get("height", target_height)
        crop_x = crop_params.get("x", 0)
        crop_y = crop_params.get("y", 0)

        # Ensure even dimensions
        crop_w = crop_w - (crop_w % 2)
        crop_h = crop_h - (crop_h % 2)

        vf_filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
        print(f"   Crop: {crop_w}x{crop_h} at ({crop_x}, {crop_y})")

    # 2. Scale filter (resize to target resolution)
    vf_filters.append(f"scale={target_width}:{target_height}")
    print(f"   Scale: {target_width}x{target_height}")

    # 3. Color grading filters (if provided)
    if grading_preset and "filters" in grading_preset:
        for grading_filter in grading_preset["filters"]:
            vf_filters.append(grading_filter)
        print(f"   Applied {len(grading_preset['filters'])} color grading filters")

    # --- NEW STEP: 4. Annotation Text Filter (Drawtext) ---
    if annotation_text:
        # Teks Anotasi akan tampil selama 5 detik
        display_duration = 5
        annotation_end_offset = annotation_start_offset + display_duration

        # Escape text untuk perintah FFmpeg (hindari ':' yang terdeteksi sebagai pemisah option)
        annotation_text_escaped = str(annotation_text)
        annotation_text_escaped = annotation_text_escaped.replace("'", "’")
        annotation_text_escaped = annotation_text_escaped.replace("\\", "\\\\")
        annotation_text_escaped = annotation_text_escaped.replace(":", "\\:")

        # Membuat filter drawtext yang diletakkan di bagian atas layar (y=100)
        # dan memiliki background box agar menonjol.
        annotation_filter = (
            f"drawtext=text='{annotation_text_escaped}':"
            f"fontfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf':"
            f"fontsize=72:"
            f"fontcolor=white:"
            f"box=1:boxcolor=0x000000@0.7:"
            f"x=(w-text_w)/2:"
            f"y=100:"
            f"enable='between(t,{annotation_start_offset},{annotation_end_offset})'"
        )
        vf_filters.append(annotation_filter)
        print(f"   Annotation: '{annotation_text_escaped}' @ {annotation_start_offset:.2f}s for {display_duration}s")
    # --- END NEW STEP ---

    # 5. Subtitle filter (if provided) - Sekarang menjadi langkah kelima
    if subtitle_path and os.path.exists(subtitle_path):
        # Escape subtitle path for FFmpeg
        subtitle_escaped = subtitle_path.replace("'", "\\'")
        vf_filters.append(f"subtitles=filename='{subtitle_escaped}'")
        print(f"   Subtitle: {subtitle_path}")
    else:
        print("   Subtitle: None")

    # Combine all filters
    vf_chain = ",".join(vf_filters)

    # Build FFmpeg command dengan dua input jika audio_path ada
    cmd = ["ffmpeg", "-y"]
    # Input 1: Video (Gunakan -ss sebelum -i untuk efisiensi)
    cmd.extend(["-ss", str(start_time), "-i", input_path])
    # Input 2: Audio (Jika file .wav tersedia)
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-ss", str(start_time), "-i", audio_path])
        print(f"   Audio Source: {audio_path}")
    # Pengaturan durasi dan filter
    cmd.extend([
        "-to", str(end_time - start_time),
        "-vf", vf_chain
    ])
    # Pemetaan (Mapping) Video & Audio
    if audio_path and os.path.exists(audio_path):
        # Ambil video dari input 0 (video) dan audio dari input 1 (wav)
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
    # Codec dan Output
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ])

    print("\n🔧 FFmpeg command:")
    print(f"   {' '.join(cmd)}\n")

    # Run FFmpeg
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        print("✅ FFmpeg completed successfully!")

        # Check output file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"📊 Output file: {output_path}")
            print(f"   Size: {file_size:.2f} MB")
        else:
            print(f"⚠️  Warning: Output file not found: {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg error:")
        print(f"   Return code: {e.returncode}")
        print(f"   STDERR: {e.stderr}")
        raise FFmpegRenderError(f"FFmpeg rendering failed: {e.stderr}") from e

    except OSError as e:
        print(f"❌ Unexpected error: {e}")
        raise FFmpegRenderError(f"FFmpeg execution failed: {e}") from e
