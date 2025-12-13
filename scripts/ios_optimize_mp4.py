from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def _probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,profile,level,pix_fmt,channels,sample_rate",
            "-show_entries",
            "format=format_name",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="ignore") or "ffprobe failed")
    return json.loads(result.stdout.decode() or "{}")


def _needs_ios_transcode(payload: dict) -> bool:
    streams = payload.get("streams") or []
    video = next((s for s in streams if (s.get("codec_type") or "").lower() == "video"), None)
    audio = next((s for s in streams if (s.get("codec_type") or "").lower() == "audio"), None)

    if not video or (video.get("codec_name") or "").lower() != "h264":
        return True
    if (video.get("pix_fmt") or "").lower() != "yuv420p":
        return True
    level = video.get("level")
    try:
        if level is None or int(level) > 41:
            return True
    except Exception:
        return True
    profile = (video.get("profile") or "").strip().lower()
    if profile and profile not in {"baseline", "main", "high"}:
        return True

    if audio:
        if (audio.get("codec_name") or "").lower() != "aac":
            return True
        if str(audio.get("sample_rate") or "").strip() not in {"44100", "48000"}:
            return True
    return False


def _transcode_to_ios(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-level:v",
        "4.1",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="ignore") or "ffmpeg failed")


def _iter_mp4_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    files: list[Path] = []
    for candidate in root.rglob("*.mp4"):
        if candidate.is_file():
            files.append(candidate)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcode MP4s for iPad/iOS playback (H.264 Main@4.1 + AAC).")
    parser.add_argument("--job-id", help="Job ID under ./storage/<job_id>/media")
    parser.add_argument("--path", help="MP4 file or directory to scan")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would be transcoded")
    args = parser.parse_args()

    targets: list[Path] = []
    if args.job_id:
        targets.append(Path("storage") / args.job_id / "media")
    if args.path:
        targets.append(Path(args.path))
    if not targets:
        parser.error("Provide --job-id or --path")

    mp4_files: list[Path] = []
    for root in targets:
        mp4_files.extend(_iter_mp4_files(root))

    seen: set[Path] = set()
    mp4_files = [p for p in mp4_files if not (p in seen or seen.add(p))]

    if not mp4_files:
        print("No .mp4 files found.")
        return 0

    changed = 0
    for path in mp4_files:
        try:
            payload = _probe(path)
        except Exception as exc:
            print(f"[skip] {path} (ffprobe failed: {exc})")
            continue

        if not _needs_ios_transcode(payload):
            print(f"[ok]   {path}")
            continue

        if args.dry_run:
            print(f"[todo] {path}")
            continue

        tmp_out = path.with_suffix(path.suffix + ".ios_tmp")
        try:
            _transcode_to_ios(path, tmp_out)
            os.replace(tmp_out, path)
            changed += 1
            print(f"[done] {path}")
        except Exception as exc:
            tmp_out.unlink(missing_ok=True)
            print(f"[fail] {path} ({exc})")

    if args.dry_run:
        return 0
    print(f"Transcoded {changed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

