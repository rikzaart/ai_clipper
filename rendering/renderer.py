"""
Video Renderer with Dynamic Multi-Shot Layout Compositor
"""
import os
import subprocess


class FFmpegRenderError(Exception):
    pass


COLOR_GRADING_PRESETS = {
    "none": None,
    "kodak_portra": {
        "name": "Kodak Portra",
        "filters": [
            "curves=r='0/0.06 0.5/0.5 1/1':g='0/0.06 0.5/0.5 1/1':b='0/0.08 0.5/0.5 1/1'",
            "eq=contrast=1.04:brightness=0.02:saturation=0.9",
            "colorbalance=rs=0.07:gs=0.03:bs=-0.07:rm=0.04:gm=0.01:bm=-0.04:rh=0.02:gh=0:bh=-0.02",
            "curves=master='0/0 0.6/0.65 1/0.98'",
            "noise=alls=2:allf=t+u",
        ],
    },
}


def render_final_video(
    input_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    shots: list = None,
    crop_params: dict = None,
    subtitle_path: str = None,
    target_width: int = 1080,
    target_height: int = 1920,
    color_grading: str = "kodak_portra",
    annotation_text: str = None,
    annotation_start_offset: float = 5.0,
    audio_path: str = None,
):
    print("🎬 Rendering video with FFmpeg...")
    half_h = target_height // 2

    if not shots:
        shots = [crop_params] if crop_params else [{
            "start": 0.0,
            "end": end_time - start_time,
            "mode": "single",
            "crop_w": 606,
            "crop_h": 1080,
            "x": 0,
            "y": 0,
        }]

    filter_complex = []
    shot_labels = []

    for idx, s in enumerate(shots):
        s_start, s_end = s["start"], s["end"]
        out_lbl = f"[v{idx}]"
        shot_labels.append(out_lbl)

        if s.get("mode") == "split":
            cw, ch = s["crop_w"], s["crop_h"]
            xt, yt = s["top"]["x"], s["top"]["y"]
            xb, yb = s["bottom"]["x"], s["bottom"]["y"]

            filter_complex.append(
                f"[0:v]trim=start={s_start}:end={s_end},setpts=PTS-STARTPTS,split=2[s{idx}a][s{idx}b];"
                f"[s{idx}a]crop={cw}:{ch}:{xt}:{yt},scale={target_width}:{half_h},setsar=1/1[s{idx}top];"
                f"[s{idx}b]crop={cw}:{ch}:{xb}:{yb},scale={target_width}:{half_h},setsar=1/1[s{idx}bot];"
                f"[s{idx}top][s{idx}bot]vstack,setsar=1/1{out_lbl}"
            )
        else:
            cw, ch = s.get("crop_w", target_width), s.get("crop_h", target_height)
            cx, cy = s.get("x", 0), s.get("y", 0)
            filter_complex.append(
                f"[0:v]trim=start={s_start}:end={s_end},setpts=PTS-STARTPTS,"
                f"crop={cw}:{ch}:{cx}:{cy},scale={target_width}:{target_height},setsar=1/1{out_lbl}"
            )

    # Concat all shot segments
    if len(shot_labels) > 1:
        filter_complex.append(f"{''.join(shot_labels)}concat=n={len(shot_labels)}:v=1:a=0,format=yuv420p,setsar=1/1[v_base]")
        current_stream = "[v_base]"
    else:
        current_stream = shot_labels[0]

    # Post processing
    post_filters = []
    if color_grading in COLOR_GRADING_PRESETS and COLOR_GRADING_PRESETS[color_grading]:
        post_filters.extend(COLOR_GRADING_PRESETS[color_grading]["filters"])

    if annotation_text:
        end_offset = annotation_start_offset + 5.0
        escaped_txt = (
            str(annotation_text)
            .replace("'", "’")
            .replace("\\", "\\\\")
            .replace(":", "\\:")
        )
        post_filters.append(
            f"drawtext=text='{escaped_txt}':"
            "expansion=none:"
            f"fontfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf':"
            f"fontsize=68:fontcolor=white:box=1:boxcolor=0x000000@0.7:"
            f"x=(w-text_w)/2:y=120:enable='between(t,{annotation_start_offset},{end_offset})'"
        )

    if subtitle_path and os.path.exists(subtitle_path):
        escaped_sub = str(subtitle_path).replace("'", "\\'")
        post_filters.append(f"subtitles=filename='{escaped_sub}'")

    if post_filters:
        filter_complex.append(f"{current_stream}{','.join(post_filters)}[v_out]")
        map_video = "[v_out]"
    else:
        map_video = current_stream

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", str(input_path),
        "-filter_complex", ";".join(filter_complex),
        "-map", map_video,
        "-map", "0:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ FFmpeg completed successfully!")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e.stderr}")
        raise FFmpegRenderError(f"FFmpeg failed: {e.stderr}") from e
