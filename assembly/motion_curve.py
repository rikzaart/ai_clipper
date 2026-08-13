"""
Motion Curve Smoothing untuk Crop Coordinates

Menggunakan exponential moving average (EMA) untuk smooth crop coordinates
dan mencegah jittery/shaky video.
"""

import numpy as np


def smooth_motion(coords_list, alpha=0.25):
    """
    Smooth motion coordinates menggunakan Exponential Moving Average (EMA)

    Formula: x_smooth = alpha * x_new + (1 - alpha) * x_prev

    Args:
        coords_list: List of coordinates, format:
            [
                {"time": 0.0, "center_x": 0.5, "center_y": 0.5},
                {"time": 1.0, "center_x": 0.6, "center_y": 0.5},
                ...
            ]
        alpha: Smoothing factor (0.0 - 1.0)
            - 0.0 = no change (very smooth, very laggy)
            - 1.0 = no smoothing (jittery)
            - 0.2-0.35 = ideal for face tracking
            - Default: 0.25

    Returns:
        Smoothed coordinates list dengan format yang sama
    """

    if not coords_list or len(coords_list) == 0:
        return coords_list

    if len(coords_list) == 1:
        return coords_list

    # Sort by time
    sorted_coords = sorted(coords_list, key=lambda x: x.get("time", 0))

    # Initialize with first coordinate
    smoothed = [sorted_coords[0].copy()]

    # Apply EMA smoothing
    for i in range(1, len(sorted_coords)):
        curr = sorted_coords[i]
        prev_smooth = smoothed[-1]

        # Smooth center_x
        if "center_x" in curr and "center_x" in prev_smooth:
            smooth_x = alpha * curr["center_x"] + (1 - alpha) * prev_smooth["center_x"]
        else:
            smooth_x = curr.get("center_x", 0.5)

        # Smooth center_y
        if "center_y" in curr and "center_y" in prev_smooth:
            smooth_y = alpha * curr["center_y"] + (1 - alpha) * prev_smooth["center_y"]
        else:
            smooth_y = curr.get("center_y", 0.5)

        # Create smoothed coordinate
        smoothed_coord = curr.copy()
        smoothed_coord["center_x"] = smooth_x
        smoothed_coord["center_y"] = smooth_y

        # Keep original values for reference
        smoothed_coord["original_x"] = curr.get("center_x", 0.5)
        smoothed_coord["original_y"] = curr.get("center_y", 0.5)

        smoothed.append(smoothed_coord)

    return smoothed


def interpolate_missing_frames(face_positions, total_frames, fps):
    """
    Interpolate face positions untuk frame yang tidak ada detection

    Args:
        face_positions: List of detected face positions
        total_frames: Total frames di video
        fps: Frame rate video

    Returns:
        Interpolated positions untuk semua frames
    """

    if not face_positions or len(face_positions) == 0:
        # No faces detected, return center position for all frames
        return [
            {
                "frame_idx": i,
                "time": i / fps if fps > 0 else 0,
                "center_x": 0.5,
                "center_y": 0.5,
                "interpolated": True
            }
            for i in range(total_frames)
        ]

    # Sort by frame index
    sorted_faces = sorted(face_positions, key=lambda x: x.get("frame_idx", 0))

    # Create interpolated list
    interpolated = []

    for frame_idx in range(total_frames):
        time = frame_idx / fps if fps > 0 else 0

        # Find closest detections before and after this frame
        before = None
        after = None

        for face in sorted_faces:
            if face["frame_idx"] <= frame_idx:
                before = face
            elif face["frame_idx"] > frame_idx and after is None:
                after = face
                break

        # Interpolate
        if before and after:
            # Linear interpolation between before and after
            t = (frame_idx - before["frame_idx"]) / (after["frame_idx"] - before["frame_idx"])
            center_x = before["center_x"] + t * (after["center_x"] - before["center_x"])
            center_y = before["center_y"] + t * (after["center_y"] - before["center_y"])
            interpolated_flag = True
        elif before:
            # Use last known position
            center_x = before["center_x"]
            center_y = before["center_y"]
            interpolated_flag = True
        elif after:
            # Use next known position
            center_x = after["center_x"]
            center_y = after["center_y"]
            interpolated_flag = True
        else:
            # No detection at all, use center
            center_x = 0.5
            center_y = 0.5
            interpolated_flag = True

        interpolated.append({
            "frame_idx": frame_idx,
            "time": time,
            "center_x": center_x,
            "center_y": center_y,
            "interpolated": interpolated_flag
        })

    return interpolated
