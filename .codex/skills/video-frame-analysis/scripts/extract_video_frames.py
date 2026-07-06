#!/usr/bin/env python3
"""Extract sampled video frames with a timestamp manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract video frames and write manifest.json")
    parser.add_argument("video", help="Input video path")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second to sample")
    parser.add_argument("--out", default="frames", help="Output directory")
    parser.add_argument("--quality", type=int, default=3, help="ffmpeg q:v value, lower is higher quality")
    parser.add_argument("--overwrite", action="store_true", help="Replace output directory if it exists")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = Path(args.video).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()

    if not video.exists():
        raise SystemExit(f"Video not found: {video}")
    if args.fps <= 0:
        raise SystemExit("--fps must be greater than 0")
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg was not found on PATH")

    if out_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"Output directory already exists: {out_dir}. Use --overwrite to replace it.")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = out_dir / "frame_%05d.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={args.fps}",
        "-q:v",
        str(args.quality),
        str(pattern),
    ]
    subprocess.run(cmd, check=True)

    frames = []
    for index, frame_path in enumerate(sorted(out_dir.glob("frame_*.jpg")), start=1):
        seconds = (index - 1) / args.fps
        frames.append(
            {
                "index": index,
                "file": frame_path.name,
                "timestamp_seconds": round(seconds, 3),
                "timestamp": format_timestamp(seconds),
            }
        )

    manifest = {
        "video": str(video),
        "fps": args.fps,
        "frame_count": len(frames),
        "frames": frames,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out_dir), "frame_count": len(frames)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
