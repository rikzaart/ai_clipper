import traceback
from pathlib import Path

import cv2

from agents.job_queue import fetch_job, mark_started
from assembly.subtitle_generator import slice_and_offset_transcript
from ingest.downloader import download_youtube
from reasoning.clip_selector import select_multi_clips_gemini
from rendering.renderer import render_final_video
from sensing.active_speaker import detect_shots_and_crops
from sensing.whisper_transcriber import extract_audio, whisper_transcribe
from utils.drive_io import upload_to_drive
from utils.sheet_io import append_clip_to_sheet, mark_job_complete, update_status

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_FOLDER_ID = "16ITj9gRgoYKgHUIa-qtXUHW4IoU03p6y"
FINISH_FOLDER_ID = "1l10aEE7w11UlHEhojzY-3ePJ_oyqIlzQ"


def run_agent(sheet, drive_service, SPREADSHEET_ID):
  print("=" * 60)
  print("🤖 AI AGENT STARTED")
  print("=" * 60)

  while True:
    try:
      row, job = fetch_job(sheet, SPREADSHEET_ID, "Jobs!A2:E")

      if not job:
        print("🛑 No pending jobs found. Process finished.")
        break

      job_id = job["job_id"]
      youtube_url = job["youtube_url"]
      target_channel = job.get("upload_channel", "main")

      print(f"\n📝 Processing job: {job_id}\n🔗 URL: {youtube_url}")
      mark_started(sheet, SPREADSHEET_ID, row)

      raw_path = PROJECT_ROOT / "raw" / f"{job_id}.mp4"
      audio_path = PROJECT_ROOT / "temp" / f"{job_id}.wav"
      transcript_out = PROJECT_ROOT / "temp" / f"{job_id}.json"

      for p in [raw_path, audio_path, transcript_out]:
        p.parent.mkdir(parents=True, exist_ok=True)

      # STEP 1: Download & Transcribe
      download_youtube(youtube_url, str(raw_path))
      extract_audio(str(raw_path), str(audio_path))
      whisper_transcribe(str(audio_path), str(transcript_out), fast_mode=True)

      # STEP 2: Gemini Reasoning
      try:
        multi_clips = select_multi_clips_gemini(
            str(transcript_out), min_duration=30, max_duration=180, n=10
        )
        if not multi_clips:
          raise ValueError("No clips returned")
      except Exception as e:  # noqa: BLE001
        print(f"⚠️ Gemini fallback: {e}")
        multi_clips = [{
            "start": 0,
            "end": 60,
            "title": "Fallback",
            "description": "",
            "tags": "#shorts",
        }]

      # STEP 3: Metadata
      cap = cv2.VideoCapture(str(raw_path))
      fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
      duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
      cap.release()

      raw_fid = None
      finished_fids = []

      # STEP 4: Process Clips
      for idx, clip in enumerate(multi_clips):
        clip_start = float(clip["start"])
        clip_end = float(clip["end"])
        clip_title = clip.get("title", f"Clip {idx+1}")

        subtitle_path = (
            PROJECT_ROOT / "temp" / f"{job_id}_clip{idx+1:02d}.ass"
        )
        finished_path = (
            PROJECT_ROOT / "finished" / f"{job_id}_clip{idx+1:02d}.mp4"
        )
        subtitle_path.parent.mkdir(parents=True, exist_ok=True)
        finished_path.parent.mkdir(parents=True, exist_ok=True)

        shots_plan = detect_shots_and_crops(str(raw_path), clip_start, clip_end)
        slice_and_offset_transcript(
            str(transcript_out), str(subtitle_path), clip_start, clip_end
        )

        render_final_video(
            input_path=str(raw_path),
            start_time=clip_start,
            end_time=min(clip_end, duration),
            output_path=str(finished_path),
            shots=shots_plan,
            subtitle_path=str(subtitle_path) if subtitle_path.exists() else None,
            target_width=1080,
            target_height=1920,
            color_grading="kodak_portra",
            annotation_text=clip.get("annotation_text"),
            annotation_start_offset=clip.get("annotation_start_offset", 5.0),
        )

        if idx == 0:
          raw_fid = upload_to_drive(
              str(raw_path), RAW_FOLDER_ID, drive_service
          )
        fin_fid = upload_to_drive(
            str(finished_path), FINISH_FOLDER_ID, drive_service
        )
        finished_fids.append(fin_fid)

        append_clip_to_sheet(
            sheet=sheet,
            SPREADSHEET_ID=SPREADSHEET_ID,
            parent_job_id=job_id,
            drive_file_id=fin_fid,
            title=clip_title,
            description=clip.get("description", ""),
            tags=clip.get("tags", "#short #viral"),
            target_channel=target_channel,
        )

      mark_job_complete(
          sheet=sheet,
          SPREADSHEET_ID=SPREADSHEET_ID,
          row=row,
          raw_fid=raw_fid or (finished_fids[0] if finished_fids else ""),
          fin_fid=finished_fids[-1] if finished_fids else "",
      )
      print(f"✅ Job {job_id} Completed")

    except Exception as e:  # noqa: BLE001
      print(f"❌ Error: {e}")
      traceback.print_exc()
      try:
        update_status(sheet, SPREADSHEET_ID, row, "error")
      except Exception as status_err:  # noqa: BLE001
        print(f"⚠️ Failed to mark job as error: {status_err}")
      break  # Hentikan worker jika terjadi fatal error pada antrean
