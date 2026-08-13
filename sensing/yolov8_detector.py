"""
YOLOv8 Face Detection dengan Spatial Clustering & Subject Locking.

Fitur Utama:
1. Auto-download model 'yolov8n-face.pt'.
2. Mendeteksi SEMUA wajah di setiap frame sampel.
3. Spatial Clustering: Mengelompokkan wajah berdasarkan posisi horizontal (X).
4. Subject Locking: Memilih satu subjek utama berdasarkan konsistensi & ukuran, 
   lalu membuang noise (wajah orang lain) agar crop stabil.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os
import torch
import requests
from collections import defaultdict

def download_face_model(model_name="yolov8n-face.pt"):
    """Download model YOLO Face khusus jika belum ada"""
    if os.path.exists(model_name):
        return str(model_name)
    
    print(f"📥 Downloading {model_name} (Face Specific Model)...")
    url = "https://github.com/akanametov/yolo-face/releases/download/v0.0.0/yolov8n-face.pt"
    
    try:
        response = requests.get(url, allow_redirects=True)
        with open(model_name, 'wb') as f:
            f.write(response.content)
        print("✅ Model downloaded successfully.")
        return str(model_name)
    except Exception as e:
        print(f"⚠️ Failed to download face model: {e}")
        return "yolov8n.pt"

def _filter_dominant_subject(all_detections, screen_width):
    """
    Logika Cerdas: Mengelompokkan deteksi wajah berdasarkan posisi X,
    lalu memilih 1 cluster subjek utama untuk di-lock.
    
    Mencegah kamera lompat-lompat antara dua orang.
    """
    if not all_detections:
        return []

    # 1. Clustering Sederhana berdasarkan Center X
    # Kita anggap wajah yang jarak X-nya dekat (< 15% lebar layar) adalah orang yang sama
    threshold = 0.15 
    clusters = [] # List of {'sum_x': 0, 'count': 0, 'sum_area': 0, 'items': []}

    # Urutkan deteksi berdasarkan posisi X untuk memudahkan grouping
    sorted_dets = sorted(all_detections, key=lambda x: x['center_x'])

    for det in sorted_dets:
        placed = False
        for cluster in clusters:
            # Hitung rata-rata X cluster saat ini
            avg_x = cluster['sum_x'] / cluster['count']
            
            # Jika dekat dengan rata-rata cluster, masukkan
            if abs(det['center_x'] - avg_x) < threshold:
                cluster['sum_x'] += det['center_x']
                cluster['sum_area'] += det['area']
                cluster['count'] += 1
                cluster['items'].append(det)
                placed = True
                break
        
        # Jika tidak cocok dengan cluster manapun, buat cluster baru
        if not placed:
            clusters.append({
                'sum_x': det['center_x'],
                'sum_area': det['area'],
                'count': 1,
                'items': [det]
            })

    # 2. Scoring Cluster (Menentukan Subjek Utama)
    # Score = Konsistensi (Count) * Ukuran Rata-rata (Avg Area)
    # Kita lebih memprioritaskan yang sering muncul (Count)
    best_cluster = None
    best_score = -1

    print(f"   📊 Found {len(clusters)} unique face position(s):")
    
    for i, c in enumerate(clusters):
        avg_area = c['sum_area'] / c['count']
        avg_x = c['sum_x'] / c['count']
        
        # Bobot: 70% frekuensi muncul, 30% ukuran wajah
        # Ini mencegah orang yang lewat sebentar tapi dekat kamera (besar) menang
        score = (c['count'] ** 1.5) * (avg_area)
        
        pos_label = "Left" if avg_x < 0.4 else "Right" if avg_x > 0.6 else "Center"
        print(f"      Position {pos_label} (X={avg_x:.2f}): Frames={c['count']}, Area={avg_area:.0f}, Score={score:.2f}")

        if score > best_score:
            best_score = score
            best_cluster = c

    # 3. Return hanya item milik pemenang
    if best_cluster:
        avg_x_winner = best_cluster['sum_x'] / best_cluster['count']
        print(f"   ✅ Locking Subject at X={avg_x_winner:.2f}")
        return best_cluster['items']
    
    return all_detections

def detect_faces(video_path, sample_frames=None, start_time=None, end_time=None, interval_ms=500):
    """
    Detect faces dengan Subject Locking.
    """
    
    # Load Model
    model_file = download_face_model()
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    
    try:
        model = YOLO(model_file)
    except:
        print("⚠️ Failed loading face model, fallback to standard.")
        model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 0

    # Range Scan
    start_sec = max(0, start_time if start_time is not None else 0)
    end_sec = min(video_duration, end_time if end_time is not None else video_duration)

    # Sampling Interval (Default 250ms agar lebih presisi menangkap gerakan)
    # Semakin kecil interval, semakin akurat clustering-nya
    actual_interval_ms = 250 
    print(f"🔍 Scanning faces: {start_sec:.1f}s - {end_sec:.1f}s (Step: {actual_interval_ms}ms)")

    raw_detections = []
    current_time = start_sec

    while current_time < end_sec:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret: break

        # Inference
        results = model(frame, verbose=False, device=device)
        
        # Ambil SEMUA wajah yang valid di frame ini (bukan cuma yang terbesar)
        # Kita akan filter nanti
        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < 0.5: continue # Confidence threshold

                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                area = (x2 - x1) * (y2 - y1)
                
                # Normalize center X (0.0 - 1.0)
                center_x = ((x1 + x2) / 2) / width
                center_y = ((y1 + y2) / 2) / height

                raw_detections.append({
                    "time": float(current_time),
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": conf,
                    "center_x": center_x,
                    "center_y": center_y,
                    "area": area
                })

        current_time += (actual_interval_ms / 1000.0)

    cap.release()

    # --- TAHAP PENTING: CLUSTERING & LOCKING ---
    # Kita filter deteksi mentah untuk hanya mengambil subjek utama
    final_detections = _filter_dominant_subject(raw_detections, width)
    
    return final_detections