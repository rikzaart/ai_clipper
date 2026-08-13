import time
import cv2
import json
import traceback
from pathlib import Path

from ingest.downloader import download_youtube
from sensing.whisper_transcriber import extract_audio, whisper_transcribe
# ============================================
# PERUBAHAN: Ganti YOLO dengan Active Speaker
# ============================================
# from sensing.yolov8_detector import detect_faces
from sensing.active_speaker import detect_active_speaker_crop
# ============================================
from assembly.crop_calculator import validate_crop_params
from assembly.subtitle_generator import slice_and_offset_transcript
from rendering.renderer import render_final_video
from utils.drive_io import upload_to_drive
from reasoning.clip_selector import select_clip_gemini, select_multi_clips_gemini
from agents.job_queue import fetch_job, mark_started
from utils.sheet_io import update_status, append_clip_to_sheet, mark_job_complete

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FOLDER_ID = "1jEGoMYQp2-2DHAkNJeglT4m8Eta9MB81"
FINISH_FOLDER_ID = "1LPcTBGS7cnPFZ5S1qbcB26YjxqQKqSrB"

def run_agent(sheet, drive_service, SPREADSHEET_ID):
    print("="*60)
    print("🤖 AI AGENT STARTED (M4 OPTIMIZED - Active Speaker)")
    print("="*60)

    while True:
        try:
            row, job = fetch_job(sheet, SPREADSHEET_ID, "Jobs!A2:E")

            if not job:
                print("No jobs. Waiting...")
                time.sleep(5)
                continue

            job_id = job["job_id"]
            youtube_url = job["youtube_url"]
            target_channel = job.get("upload_channel", "main")

            print(f"\n{'='*60}")
            print(f"📝 Processing job: {job_id}")
            print(f"🔗 URL: {youtube_url}")
            print(f"📺 Target Channel: {target_channel}")
            print(f"{'='*60}\n")

            mark_started(sheet, SPREADSHEET_ID, row)

            # Define paths dengan pathlib
            raw_path = PROJECT_ROOT / "raw" / f"{job_id}.mp4"
            audio_path = PROJECT_ROOT / "temp" / f"{job_id}.wav"
            transcript_out = PROJECT_ROOT / "temp" / f"{job_id}.json"
            
            # Buat folder jika belum ada
            for p in [raw_path, audio_path, transcript_out]:
                p.parent.mkdir(parents=True, exist_ok=True)

            # STEP 1: Download
            print("📥 STEP 1: Downloading...")
            download_youtube(youtube_url, str(raw_path))

            # STEP 2: Transcribe
            print("🎤 STEP 2: Extracting & Transcribing...")
            extract_audio(str(raw_path), str(audio_path))
            whisper_transcribe(str(audio_path), str(transcript_out), fast_mode=True)

            # STEP 3: Gemini Reasoning
            print("🧠 STEP 3: Gemini Reasoning...")
            try:
                multi_clips = select_multi_clips_gemini(
                    str(transcript_out),
                    min_duration=30,   
                    max_duration=180,  
                    n=10
                )
                print(f"✅ Gemini selected {len(multi_clips)} clips.")
                if not multi_clips: 
                    raise Exception("0 clips found")
            except Exception as e:
                print(f"⚠️ Gemini failed: {e}. Using fallback.")
                multi_clips = [{
                    'start': 0, 
                    'end': 60, 
                    'title': 'Fallback', 
                    'description': 'Auto-generated clip', 
                    'viral_score': 5, 
                    'tags': '#fallback #shorts'
                }]

            # STEP 4: Video Properties
            print("📊 STEP 4: Analyze Metadata...")
            cap = cv2.VideoCapture(str(raw_path))
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps if fps > 0 else 0
            cap.release()

            raw_fid = None
            finished_fids = []

            # ============================================
            # STEP 5-9: Loop per Clip
            # ============================================
            for idx, clip_selection in enumerate(multi_clips):
                clip_start = float(clip_selection['start'])
                clip_end = float(clip_selection['end'])
                clip_title = clip_selection.get('title', f'Clip {idx+1}')
                clip_description = clip_selection.get('description', '')
                clip_tags = clip_selection.get('tags', '#short #viral')
                viral_score = clip_selection.get('viral_score', 7.0)
                
                # Extract Annotation Data
                annotation_text = clip_selection.get('annotation_text', None)
                annotation_offset = clip_selection.get('annotation_start_offset', 5.0)

                # Setup Paths
                subtitle_path = PROJECT_ROOT / "temp" / f"{job_id}_clip{idx+1:02d}.ass"
                finished_path = PROJECT_ROOT / "finished" / f"{job_id}_clip{idx+1:02d}.mp4"
                subtitle_path.parent.mkdir(parents=True, exist_ok=True)
                finished_path.parent.mkdir(parents=True, exist_ok=True)
                
                print(f"\n🎬 Processing Clip {idx+1}: {clip_title}")
                print(f"   Time: {clip_start:.2f}s - {clip_end:.2f}s")

                # ============================================
                # STEP 5: SMART CROP (PER CLIP) - DENGAN ACTIVE SPEAKER
                # ============================================
                print(f"   🔍 Detecting Active Speaker ({clip_start:.1f}s - {clip_end:.1f}s)...")
                
                # ============================================
                # PERUBAHAN: Satu baris panggil detect_active_speaker_crop
                # ============================================
                crop_params = detect_active_speaker_crop(
                    str(raw_path),
                    clip_start,
                    clip_end,
                    target_width=1080,
                    target_height=1920
                )
                # ============================================
                
                # Validasi crop
                if not crop_params.get('valid', False):
                    print("   ⚠️ Active speaker detection failed/unstable. Using Center Crop.")
                    crop_w = int(video_height * (9/16))
                    crop_params = {
                        "x": (video_width - crop_w)//2, 
                        "y": 0,
                        "width": crop_w, 
                        "height": video_height,
                        "valid": False
                    }
                else:
                    print(f"   ✅ Smart Crop Lock: X={crop_params['x']}px")

                # ============================================
                # STEP 6: SUBTITLE
                # ============================================
                subtitle_path = slice_and_offset_transcript(
                    str(transcript_out), str(subtitle_path), clip_start, clip_end
                )

                # ============================================
                # STEP 7: RENDER
                # ============================================
                clip_end_safe = min(clip_end, duration)
                render_final_video(
                    str(raw_path),
                    start_time=clip_start,
                    end_time=clip_end_safe,
                    output_path=str(finished_path),
                    crop_params=crop_params,
                    subtitle_path=str(subtitle_path) if subtitle_path else None,
                    target_width=1080,
                    target_height=1920,
                    color_grading="kodak_portra",
                    annotation_text=annotation_text,
                    annotation_start_offset=annotation_offset
                )

                # ============================================
                # STEP 8: Upload
                # ============================================
                if idx == 0:
                    raw_fid = upload_to_drive(str(raw_path), RAW_FOLDER_ID, drive_service)
                    print(f"📤 Uploaded raw video: {raw_fid}")
                else:
                    raw_fid = "SKIPPED"
                
                fin_fid = upload_to_drive(str(finished_path), FINISH_FOLDER_ID, drive_service)
                finished_fids.append(fin_fid)
                print(f"📤 Uploaded finished clip: {fin_fid}")
                
                # ============================================
                # STEP 9: Simpan ke Sheet
                # ============================================
                append_clip_to_sheet(
                    sheet=sheet,
                    SPREADSHEET_ID=SPREADSHEET_ID,
                    parent_job_id=job_id,
                    drive_file_id=fin_fid,
                    title=clip_title,
                    description=clip_description,
                    tags=clip_tags,
                    target_channel=target_channel
                )

            # ============================================
            # Mark Job Complete
            # ============================================
            raw_fid_for_job = raw_fid if raw_fid and raw_fid != "SKIPPED" else finished_fids[0] if finished_fids else ""
            fin_fid_for_job = finished_fids[-1] if finished_fids else ""
            
            mark_job_complete(
                sheet=sheet,
                SPREADSHEET_ID=SPREADSHEET_ID,
                row=row,
                raw_fid=raw_fid_for_job,
                fin_fid=fin_fid_for_job
            )

            print(f"\n✅ Job {job_id} Completed! {len(multi_clips)} clips added to Clips sheet.")

        except Exception as e:
            print(f"❌ Critical Error: {e}")
            traceback.print_exc()
            try:
                update_status(sheet, SPREADSHEET_ID, row, "error")
            except: 
                pass
            time.sleep(5)