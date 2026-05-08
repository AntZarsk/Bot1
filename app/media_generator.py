from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import requests

from app.config import settings
from app.models import MediaAsset
from app.utils import ensure_dir


def _build_safe_name(title: str) -> str:
    safe_name = "".join(ch for ch in title.lower() if ch.isalnum() or ch in {" ", "-", "_"}).strip()
    return "_".join(safe_name.split())[:60] or "cover"


def _is_probably_jpeg(content: bytes) -> bool:
    # JPEG signature: starts with FF D8 FF
    return len(content) >= 3 and content[0:3] == b"\xff\xd8\xff"


def generate_cover_image(prompt: str, title: str) -> MediaAsset:
    if not prompt.strip():
        raise ValueError("Image prompt is empty")

    ensure_dir(settings.media_dir)
    safe_name = _build_safe_name(title)
    output_path = settings.media_dir / f"{safe_name}.jpg"

    url = f"{settings.pollinations_base_url}/{requests.utils.quote(prompt)}"
    try:
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        content = response.content

        # Some failures from image endpoints return HTML/JSON/error bytes with 200,
        # which Telegram then treats as an invalid photo.
        if not _is_probably_jpeg(content):
            raise RuntimeError("Pollinations did not return a valid JPEG payload")

        output_path.write_bytes(content)
    except Exception as exc:
        fallback_image = Path("test_telegram.jpg")
        if fallback_image.exists():
            shutil.copyfile(fallback_image, output_path)
        else:
            raise RuntimeError(f"Failed to generate image and fallback image is missing: {exc}") from exc

    return MediaAsset(path=str(output_path), source_url=url)


def generate_video_from_image(image_path: str, title: str) -> MediaAsset:
    ensure_dir(settings.media_dir)

    input_path = Path(image_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    safe_name = _build_safe_name(title)
    output_path = settings.media_dir / f"{safe_name}.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(input_path),
        "-t",
        "8",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "ffmpeg failed")
    except Exception as exc:
        raise RuntimeError(f"Failed to generate video: {exc}") from exc

    return MediaAsset(path=str(output_path), source_url=str(input_path))
