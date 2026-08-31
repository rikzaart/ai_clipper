"""
Smart Framing & Shot-Based Layout Planner (YOLOv8-based)
"""
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO


def detect_shots_and_crops(
    video_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 1080,
    target_height: int = 1920,
    **kwargs
) -> list[dict]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [{
            "start": 0.0,
            "end": end_time - start_time,
            "mode": "single",
            "x": 0,
            "y": 0,
            "w": 606,
            "h": 1080,
        }]

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    model_file = "yolov8n-face.pt" if Path("yolov8n-face.pt").exists() else "yolov8n.pt"
    try:
        model = YOLO(model_file)
    except Exception:
        cap.release()
        return [{
            "start": 0.0,
            "end": end_time - start_time,
            "mode": "single",
            "x": (width - 606) // 2,
            "y": 0,
            "w": 606,
            "h": height,
        }]

    start_frame = int(max(0.0, start_time) * fps)
    end_frame = int(min(end_time * fps, total_frames))
    step = max(1, int(0.3 * fps))

    # 1. Scene cuts detection
    cuts = [start_frame]
    prev_gray = None
    for f_idx in range(start_frame, end_frame, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if not ret:
            break
        small = cv2.resize(frame, (160, 90))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = np.mean(cv2.absdiff(gray, prev_gray))
            if diff > 26.0 and (f_idx - cuts[-1]) >= int(0.75 * fps):
                cuts.append(f_idx)
        prev_gray = gray
    cuts.append(end_frame)

    shots_plan = []
    for i in range(len(cuts) - 1):
        s_start_f, s_end_f = cuts[i], cuts[i + 1]
        t_start = (s_start_f - start_frame) / fps
        t_end = (s_end_f - start_frame) / fps

        cap.set(cv2.CAP_PROP_POS_FRAMES, (s_start_f + s_end_f) // 2)
        ret, frame = cap.read()

        faces = []
        if ret:
            results = model(frame, verbose=False)
            for r in results:
                for box in r.boxes:
                    if float(box.conf[0]) >= 0.4:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        faces.append({
                            "cx": float((x1 + x2) / 2.0),
                            "cy": float((y1 + y2) / 2.0),
                            "w": float(x2 - x1),
                            "h": float(y2 - y1),
                        })

        faces.sort(key=lambda f: f["cx"])

        # Dual speaker -> stacked split (top/bottom)
        if len(faces) >= 2 and (faces[-1]["cx"] - faces[0]["cx"]) > (width * 0.25):
            f_top, f_bot = faces[0], faces[-1]
            split_box_h = int(min(height, max(f_top["h"], f_bot["h"]) * 3.2))
            split_box_h = max(int(height * 0.65), split_box_h)
            split_box_w = int(split_box_h * (9 / 8))
            split_box_w -= (split_box_w % 2)
            split_box_h -= (split_box_h % 2)

            def get_box(face):
                bx = int(face["cx"] - (split_box_w / 2))
                by = int(face["cy"] - (split_box_h * 0.38))
                bx = max(0, min(bx, width - split_box_w))
                by = max(0, min(by, height - split_box_h))
                return bx, by

            x_top, y_top = get_box(f_top)
            x_bot, y_bot = get_box(f_bot)

            shots_plan.append({
                "start": round(t_start, 2),
                "end": round(t_end, 2),
                "mode": "split",
                "crop_w": split_box_w,
                "crop_h": split_box_h,
                "top": {"x": x_top, "y": y_top},
                "bottom": {"x": x_bot, "y": y_bot},
            })
        else:
            single_w = int(height * (9 / 16))
            single_w -= (single_w % 2)
            target_cx = faces[0]["cx"] if faces else (width / 2)
            cx = int(target_cx - (single_w / 2))
            cx = max(0, min(cx, width - single_w))

            shots_plan.append({
                "start": round(t_start, 2),
                "end": round(t_end, 2),
                "mode": "single",
                "crop_w": single_w,
                "crop_h": height,
                "x": cx,
                "y": 0,
            })

    cap.release()
    print(f"   🎬 Generated {len(shots_plan)} shot layout(s).")
    return shots_plan