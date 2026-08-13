"""
Active Speaker Detector (MediaPipe Solution)
"""

import os
import cv2
import numpy as np

# --- SILENCE MEDIAPIPE LOGS ---
os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh


def get_vertical_mouth_distance(landmarks, img_height):
    upper = landmarks[13].y * img_height
    lower = landmarks[14].y * img_height
    return abs(lower - upper)


def detect_active_speaker_crop(
    video_path,
    start_time,
    end_time,
    target_width=1080,
    target_height=1920,
    sample_interval=0.3,
):
    print(f"👄 Analyzing Active Speaker: {start_time:.2f}s - {end_time:.2f}s")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return get_center_crop_fallback(video_path, target_width, target_height)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Rasio 9:16 dari tinggi video lanskap
    crop_h = height
    crop_w = int(height * 9 / 16)
    crop_w = crop_w - (crop_w % 2)

    start_frame = int(max(0, start_time) * fps)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end_frame = int(min(end_time * fps, total_frames))
    step = max(1, int(sample_interval * fps))

    speakers_data = {}

    try:
        with mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as face_mesh:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            current_frame = start_frame

            while current_frame < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break

                if current_frame % step == 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_mesh.process(rgb_frame)

                    if results.multi_face_landmarks:
                        for landmarks in results.multi_face_landmarks:
                            x_coords = [l.x for l in landmarks.landmark]
                            center_x = sum(x_coords) / len(x_coords)
                            mouth_dist = get_vertical_mouth_distance(
                                landmarks.landmark, height
                            )

                            matched_id = None
                            for sid, sdata in speakers_data.items():
                                avg_x = sdata["sum_x"] / sdata["count"]
                                if abs(center_x - avg_x) < 0.15:
                                    matched_id = sid
                                    break

                            if matched_id is None:
                                matched_id = len(speakers_data)
                                speakers_data[matched_id] = {
                                    "openings": [],
                                    "sum_x": 0,
                                    "count": 0,
                                }

                            speakers_data[matched_id]["openings"].append(mouth_dist)
                            speakers_data[matched_id]["sum_x"] += center_x
                            speakers_data[matched_id]["count"] += 1

                current_frame += 1
    except Exception as e:
        print(f"⚠️ MediaPipe Execution Error: {e}")
        cap.release()
        return get_center_crop_fallback(video_path, target_width, target_height)

    cap.release()

    best_speaker_id = None
    max_variance = -1

    for fid, data in speakers_data.items():
        if data["count"] < 3:
            continue
        variance = np.var(data["openings"])
        if variance > max_variance:
            max_variance = variance
            best_speaker_id = fid

    if best_speaker_id is not None:
        winner = speakers_data[best_speaker_id]
        avg_center_x_px = (winner["sum_x"] / winner["count"]) * width
        final_crop_x = int(avg_center_x_px - (crop_w / 2))
        final_crop_x = max(0, min(final_crop_x, width - crop_w))
        print(f"   ✅ WINNER: ID {best_speaker_id} (Variance {max_variance:.4f})")
        return {
            "x": final_crop_x,
            "y": 0,
            "width": crop_w,
            "height": crop_h,
            "valid": True,
        }

    return get_center_crop_fallback(video_path, target_width, target_height)


def get_center_crop_fallback(video_path, target_w, target_h):
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            crop_w = int(h * 9 / 16)
            crop_w = crop_w - (crop_w % 2)
            return {
                "x": max(0, (w - crop_w) // 2),
                "y": 0,
                "width": crop_w,
                "height": h,
                "valid": False,
            }
    except Exception:
        pass
    return {
        "x": 0,
        "y": 0,
        "width": 606,
        "height": 1080,
        "valid": False,
    }