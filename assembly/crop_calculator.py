"""
Dynamic Crop Calculator untuk Vertical Video

Menghitung crop coordinates berdasarkan face positions
untuk membuat vertical video (9:16) yang focus ke wajah pembicara.
"""

import numpy as np
from assembly.motion_curve import smooth_motion, interpolate_missing_frames


def compute_dynamic_crop(
    face_positions,
    video_width,
    video_height,
    target_width=1080,
    target_height=1920,
    smoothing_alpha=0.25
):
    """
    Compute dynamic crop coordinates untuk vertical video

    Args:
        face_positions: List of face positions dari YOLO detection
        video_width: Original video width
        video_height: Original video height
        target_width: Target width (default: 1080 for 9:16)
        target_height: Target height (default: 1920 for 9:16)
        smoothing_alpha: Smoothing factor untuk motion (default: 0.25)

    Returns:
        Dict dengan crop parameters:
        {
            "x": 100,        # Top-left x coordinate
            "y": 0,          # Top-left y coordinate
            "width": 1080,   # Crop width
            "height": 1920,  # Crop height
            "center_x": 0.5, # Normalized center x (0.0 - 1.0)
            "center_y": 0.5, # Normalized center y (0.0 - 1.0)
            "valid": True    # Whether crop is valid
        }
    """

    # Calculate target aspect ratio
    target_aspect = target_width / target_height  # 9:16 = 0.5625

    # Calculate crop dimensions based on video size
    # We want to crop to 9:16 aspect ratio
    if video_width / video_height > target_aspect:
        # Video is wider than target, crop width
        crop_height = video_height
        crop_width = int(crop_height * target_aspect)
    else:
        # Video is taller than target, crop height
        crop_width = video_width
        crop_height = int(crop_width / target_aspect)

    # Ensure crop dimensions are valid
    crop_width = min(crop_width, video_width)
    crop_height = min(crop_height, video_height)

    # Ensure crop dimensions are even (required by ffmpeg)
    crop_width = crop_width - (crop_width % 2)
    crop_height = crop_height - (crop_height % 2)

    # Determine center position based on face positions
    if face_positions and len(face_positions) > 0:
        # Smooth face positions
        smoothed_positions = smooth_motion(face_positions, alpha=smoothing_alpha)

        # Calculate average center position
        avg_center_x = np.mean([p["center_x"] for p in smoothed_positions])
        avg_center_y = np.mean([p["center_y"] for p in smoothed_positions])

        print(f"📍 Face detected: center at ({avg_center_x:.2f}, {avg_center_y:.2f})")
    else:
        # No faces detected, use center
        avg_center_x = 0.5
        avg_center_y = 0.5
        print(f"⚠️  No faces detected, using center crop")

    # Calculate crop position
    # Center the crop around the detected face
    crop_x = int((avg_center_x * video_width) - (crop_width / 2))
    crop_y = int((avg_center_y * video_height) - (crop_height / 2))

    # Ensure crop is within video bounds
    crop_x = max(0, min(crop_x, video_width - crop_width))
    crop_y = max(0, min(crop_y, video_height - crop_height))

    # Validate crop parameters
    valid = (
        crop_width > 0 and
        crop_height > 0 and
        crop_x >= 0 and
        crop_y >= 0 and
        crop_x + crop_width <= video_width and
        crop_y + crop_height <= video_height
    )

    if not valid:
        print(f"❌ Invalid crop parameters!")
        print(f"   Video: {video_width}x{video_height}")
        print(f"   Crop: {crop_width}x{crop_height} at ({crop_x}, {crop_y})")
        print(f"   Using fallback: center crop")

        # Fallback to center crop
        crop_x = (video_width - crop_width) // 2
        crop_y = (video_height - crop_height) // 2
        crop_x = max(0, crop_x)
        crop_y = max(0, crop_y)

    result = {
        "x": crop_x,
        "y": crop_y,
        "width": crop_width,
        "height": crop_height,
        "center_x": avg_center_x,
        "center_y": avg_center_y,
        "valid": valid
    }

    print(f"✂️  Crop: {crop_width}x{crop_height} at ({crop_x}, {crop_y})")
    print(f"   Target: {target_width}x{target_height}")

    return result


def validate_crop_params(crop_params, video_width, video_height):
    """
    Validate crop parameters to prevent corrupt video

    Args:
        crop_params: Crop parameters dict
        video_width: Original video width
        video_height: Original video height

    Returns:
        True if valid, False otherwise
    """

    x = crop_params.get("x", 0)
    y = crop_params.get("y", 0)
    w = crop_params.get("width", 0)
    h = crop_params.get("height", 0)

    # Check for zero dimensions (causes corrupt video)
    if w <= 0 or h <= 0:
        print(f"❌ Invalid crop: width={w}, height={h} (must be > 0)")
        return False

    # Check for out of bounds
    if x < 0 or y < 0:
        print(f"❌ Invalid crop: x={x}, y={y} (must be >= 0)")
        return False

    if x + w > video_width or y + h > video_height:
        print(f"❌ Invalid crop: exceeds video bounds")
        print(f"   Video: {video_width}x{video_height}")
        print(f"   Crop: {w}x{h} at ({x}, {y})")
        return False

    # Check for even dimensions (required by some codecs)
    if w % 2 != 0 or h % 2 != 0:
        print(f"⚠️  Warning: crop dimensions not even (w={w}, h={h})")
        print(f"   Some codecs may fail. Adjusting...")
        return False

    return True
