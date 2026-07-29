#!/usr/bin/env python3
"""Generate Storycatchers video posters matching the studiotour reference."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "assets" / "video"
ASSETS_DIR = VIDEO_DIR / "poster-assets"

WIDTH, HEIGHT = 1280, 720
BORDER = 59
PHOTO_W = WIDTH - 2 * BORDER
PHOTO_H = HEIGHT - 2 * BORDER

# Overlay positions: exact absolute canvas coords from the studiotour reference.
BADGE_POS = (100, 100)
TITLE_X = 113
TITLE_BOTTOM = 567
RED_BAR_BOX = (112, 600, 192, 614)

FONT_BOLD = ASSETS_DIR / "Montserrat-Bold.ttf"
TITLE_FONT_SIZE = 80
TITLE_MAX_WIDTH = 1050

POSTERS = [
    {
        "mp4": "2023-Storycatchers-Studio2.mp4",
        "poster": "2023-Storycatchers-Studio2-poster.jpg",
        "title": "Studio 2",
        "seek": "3",
    },
    {
        "mp4": "2024-Storycatchers-EducatieveVideoreeksen-2.mp4",
        "poster": "2024-Storycatchers-EducatieveVideoreeksen-poster.jpg",
        "title": "Educatieve videoreeksen",
        "seek": "2",
        "auto_frame": False,
    },
    {
        "mp4": "2025-Storycatchers-VoorstellingVirtueleStudio-VirtualSync-CC-ENG-7.mp4",
        "poster": "2025-Storycatchers-VoorstellingVirtueleStudio-poster.jpg",
        "title": "Virtuele studio",
        "seek": "5",
    },
    {
        "mp4": "2023-Storycatchers-HumanMattersMakingOff-1.mp4",
        "poster": "2023-Storycatchers-HumanMattersMakingOff-poster.jpg",
        "title": "Human Matters",
        "seek": "4",
    },
    {
        "mp4": "2023-Storycatchers-Pianc-5.mp4",
        "poster": "2023-Storycatchers-Pianc-poster.jpg",
        "title": "PIANC",
        "seek": "3",
    },
    {
        "mp4": "2023-UAntwerpen-230413-Cumulus-Aftermovie.mp4",
        "poster": "2023-UAntwerpen-Cumulus-Aftermovie-poster.jpg",
        "title": "Cumulus",
        "seek": "6",
    },
    {
        "mp4": "2024-Storycatchers-Evenementen-6.mp4",
        "poster": "2024-Storycatchers-Evenementen-poster.jpg",
        "title": "Evenementen",
        "seek": "49",
        "auto_frame": False,
    },
    {
        "mp4": "2025-ST-SOCIALS-PILOT-DelawareTestimonial-4.mp4",
        "poster": "2025-ST-SOCIALS-DelawareTestimonial-poster.jpg",
        "title": "Delaware",
        "seek": "2",
    },
    {
        "mp4": "2025-ST-SOCIALS-VerhaertTestimonial-1.mp4",
        "poster": "2025-ST-SOCIALS-VerhaertTestimonial-poster.jpg",
        "title": "Verhaert",
        "seek": "2",
    },
    {
        "mp4": "2021-Storycatchers-SlechtvalkenBrussel-uUMfQEyFmto.mp4",
        "poster": "2021-Storycatchers-SlechtvalkenBrussel-poster.jpg",
        "title": "Slechtvalken",
        "seek": "2",
    },
    {
        "image": "vimeo-live-streaming-frame.jpg",
        "poster": "2026-Storycatchers-LiveStreaming-poster.jpg",
        "title": "Live streaming",
    },
    {
        "image": "vimeo-webinars-frame.jpg",
        "poster": "2026-Storycatchers-Webinars-poster.jpg",
        "title": "Webinars",
    },
    {
        "image": "vimeo-badge-printing-frame.jpg",
        "poster": "2026-Storycatchers-BadgePrinting-poster.jpg",
        "title": "Badge printing",
    },
]


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def video_duration(mp4: Path) -> float:
    result = subprocess.run(
        [ffmpeg_exe(), "-i", str(mp4)],
        capture_output=True,
        text=True,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def extract_frame(mp4: Path, seek: str, dest: Path) -> None:
    subprocess.run(
        [
            ffmpeg_exe(),
            "-y",
            "-ss",
            seek,
            "-i",
            str(mp4),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )


def cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = img.resize(
        (round(src_w * scale), round(src_h * scale)), Image.Resampling.LANCZOS
    )
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def text_score(img: Image.Image) -> float:
    rgb = np.array(img.convert("RGB"), dtype=float)
    gray = rgb.mean(axis=2)
    h, w = gray.shape

    score = 0.0
    for y0, y1 in ((int(h * 0.35), h), (int(h * 0.15), int(h * 0.85))):
        zone = gray[y0:y1, :]
        if zone.size == 0:
            continue
        score += float(np.abs(np.diff(zone, axis=1)).mean()) * 2
        score += float(np.abs(np.diff(zone, axis=0)).mean())

    for y0, y1 in ((int(h * 0.35), h), (int(h * 0.15), int(h * 0.85))):
        zone = rgb[y0:y1, :, :]
        if zone.size == 0:
            continue
        white = (
            (zone[:, :, 0] > 190)
            & (zone[:, :, 1] > 190)
            & (zone[:, :, 2] > 190)
        )
        score += float(white.mean()) * 200
        cyan = (zone[:, :, 1] > zone[:, :, 0] + 20) & (
            zone[:, :, 2] > zone[:, :, 0] + 20
        )
        score += float(cyan.mean()) * 40

    bottom = rgb[int(h * 0.5) :, :, :]
    if bottom.size:
        if float(bottom.std()) < 25:
            score += 30

    return score


def pick_clean_frame(
    mp4: Path, fallback_seek: str, tmp: Path, auto_frame: bool = True
) -> Image.Image:
    if not auto_frame:
        extract_frame(mp4, fallback_seek, tmp)
        print(f"  frame seek={fallback_seek} (fixed)", file=sys.stderr)
        return Image.open(tmp)

    duration = video_duration(mp4)
    candidates = []
    if duration > 0:
        for ratio in (
            0.03,
            0.05,
            0.08,
            0.12,
            0.16,
            0.20,
            0.24,
            0.28,
            0.32,
            0.38,
            0.44,
            0.50,
            0.58,
            0.66,
        ):
            candidates.append(f"{duration * ratio:.2f}")
    candidates.append(fallback_seek)

    best_frame = None
    best_score = float("inf")
    best_seek = fallback_seek

    for seek in candidates:
        extract_frame(mp4, seek, tmp)
        frame = Image.open(tmp)
        score = text_score(frame)
        if score < best_score:
            best_score = score
            best_frame = frame.copy()
            best_seek = seek

    if best_frame is None:
        extract_frame(mp4, fallback_seek, tmp)
        best_frame = Image.open(tmp)

    print(f"  frame seek={best_seek} score={best_score:.2f}", file=sys.stderr)
    return best_frame


def title_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD), size)


def fit_title_font(title: str) -> ImageFont.FreeTypeFont:
    for size in range(TITLE_FONT_SIZE, 40, -1):
        font = title_font(size)
        bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), title, font=font)
        if bbox[2] - bbox[0] <= TITLE_MAX_WIDTH:
            return font
    return title_font(40)


def render_poster(
    frame: Image.Image,
    title: str,
    badge: Image.Image,
    red_bar: Image.Image,
) -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    photo = cover_crop(frame.convert("RGB"), PHOTO_W, PHOTO_H)
    canvas.paste(photo, (BORDER, BORDER))

    composed = canvas.convert("RGBA")
    composed.paste(badge, BADGE_POS, badge)

    draw = ImageDraw.Draw(composed)
    title_font = fit_title_font(title)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    text_h = bbox[3] - bbox[1]
    title_y = TITLE_BOTTOM - text_h
    draw.text((TITLE_X, title_y), title, fill=(255, 255, 255, 255), font=title_font)

    composed.paste(red_bar, (RED_BAR_BOX[0], RED_BAR_BOX[1]), red_bar)
    return composed.convert("RGB")


def ensure_assets() -> tuple[Image.Image, Image.Image]:
    reference = VIDEO_DIR / "2024-Storycatchers-Studiotour-poster.jpg"
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    badge_path = ASSETS_DIR / "storycatchers-badge.png"
    bar_path = ASSETS_DIR / "red-accent-bar.png"

    if not FONT_BOLD.exists():
        raise FileNotFoundError(
            f"Missing {FONT_BOLD.name}. Download Montserrat-Bold.ttf into poster-assets/."
        )

    if reference.exists():
        ref = Image.open(reference)
        ref.crop((100, 100, 425, 159)).save(badge_path)
        ref.crop(RED_BAR_BOX).save(bar_path)

    badge = Image.open(badge_path).convert("RGBA")
    red_bar = Image.open(bar_path).convert("RGBA")
    return badge, red_bar


def main() -> int:
    tmp = VIDEO_DIR / ".poster-frame.jpg"
    badge, red_bar = ensure_assets()
    created = []

    for item in POSTERS:
        poster = VIDEO_DIR / item["poster"]
        if "image" in item:
            source = VIDEO_DIR / item["image"]
            if not source.exists():
                print(f"skip missing image: {source.name}", file=sys.stderr)
                continue
            print(f"processing {poster.name} (image)...", file=sys.stderr)
            frame = Image.open(source)
        else:
            mp4 = VIDEO_DIR / item["mp4"]
            if not mp4.exists():
                print(f"skip missing mp4: {mp4.name}", file=sys.stderr)
                continue
            print(f"processing {poster.name}...", file=sys.stderr)
            frame = pick_clean_frame(
                mp4,
                item["seek"],
                tmp,
                auto_frame=item.get("auto_frame", True),
            )

        result = render_poster(frame, item["title"], badge, red_bar)
        result.save(poster, "JPEG", quality=92, optimize=True)
        created.append(poster.name)
        print(f"created {poster.name}")

    if tmp.exists():
        tmp.unlink()

    print(json.dumps(created, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
