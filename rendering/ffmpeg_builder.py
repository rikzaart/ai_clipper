def build_ffmpeg_command(input_video, segment, crop, subs, output):
    cmd = f"""
    ffmpeg -y -i "{input_video}" 
    -vf "crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}" 
    -ss {segment['start']} -to {segment['end']}
    -vf subtitles='{subs}'
    "{output}"
    """
    return " ".join(cmd.split())
