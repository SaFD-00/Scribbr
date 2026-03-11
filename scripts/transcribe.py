#!/usr/bin/env python3
"""
Scribbr - Audio Transcription Script
Uses mlx-whisper (Apple Silicon optimized) to transcribe audio recordings.

Usage:
    python scripts/transcribe.py 2026-03-04
    python scripts/transcribe.py 2026-03-04 --profile cse-seminar
    python scripts/transcribe.py 2026-03-04 --model mlx-community/whisper-large-v3-mlx
"""

import argparse
import glob
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    import yaml

    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_profile_config(config: dict, profile_name: Optional[str]) -> dict:
    """Get merged config: default + profile overrides."""
    default = config.get("default", {})
    if profile_name and "profiles" in config:
        profile = config["profiles"].get(profile_name, {})
        return {**default, **profile}
    return default


def find_audio_files(data_dir: str) -> list[str]:
    """Find all audio files in the given directory."""
    patterns = ["*.m4a", "*.M4A", "*.mp3", "*.MP3", "*.wav", "*.WAV"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(data_dir, pattern)))
    return sorted(files)


def convert_to_wav(input_path: str) -> str:
    """Convert audio file to 16kHz mono WAV using ffmpeg."""
    tmp_wav = tempfile.mktemp(suffix=".wav")
    cmd = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-y",
        "-loglevel", "error",
        tmp_wav
    ]
    subprocess.run(cmd, check=True)
    return tmp_wav


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribe(audio_path: str, model_name: str) -> dict:
    """Transcribe audio using mlx-whisper."""
    import mlx_whisper

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_name,
        word_timestamps=True,
        verbose=False,
    )
    return result


def build_markdown(result: dict, date: str, source_filename: str, chunk_duration: int = 300) -> str:
    """Build markdown content from transcription result."""
    language = result.get("language", "unknown")
    segments = result.get("segments", [])

    lines = []
    lines.append("# Transcript\n")
    lines.append(f"- **Date**: {date}")
    lines.append(f"- **Source**: {source_filename}")
    lines.append(f"- **Language**: {language}")
    lines.append(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---\n")

    # Group segments into chunks for readability
    current_chunk_start = 0.0
    current_chunk_texts = []

    for seg in segments:
        seg_start = seg.get("start", 0.0)
        seg_text = seg.get("text", "").strip()

        if not seg_text:
            continue

        # Start new chunk if we've exceeded the duration
        if seg_start - current_chunk_start >= chunk_duration and current_chunk_texts:
            chunk_end = seg_start
            header = f"## [{format_timestamp(current_chunk_start)} - {format_timestamp(chunk_end)}]"
            lines.append(header)
            lines.append("")
            lines.append(" ".join(current_chunk_texts))
            lines.append("")

            current_chunk_start = seg_start
            current_chunk_texts = []

        current_chunk_texts.append(seg_text)

    # Flush remaining text
    if current_chunk_texts:
        last_seg = segments[-1] if segments else {}
        chunk_end = last_seg.get("end", current_chunk_start)
        header = f"## [{format_timestamp(current_chunk_start)} - {format_timestamp(chunk_end)}]"
        lines.append(header)
        lines.append("")
        lines.append(" ".join(current_chunk_texts))
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio recordings using mlx-whisper"
    )
    parser.add_argument(
        "date",
        help="Date folder name (e.g., 2026-03-04 or 2026-03-04_standup)"
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Profile name from config.yaml (e.g., cse-seminar, lab-meeting)"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config file (default: config.yaml in project root)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="HuggingFace model ID (overrides config)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: transcript.md)"
    )
    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).resolve().parent.parent
    config_path = args.config or str(project_root / "config.yaml")

    # Load config
    config = load_config(config_path)
    profile = get_profile_config(config, args.profile)

    # Determine settings (CLI > profile > default)
    model_name = args.model or profile.get("stt_model", "mlx-community/whisper-large-v3-mlx")
    chunk_duration = profile.get("chunk_duration", 300)
    data_base = profile.get("data_dir", "data")
    data_dir = project_root / data_base / args.date

    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)

    # Find audio files
    audio_files = find_audio_files(str(data_dir))
    if not audio_files:
        print(f"Error: No audio files (m4a/mp3/wav) found in {data_dir}")
        sys.exit(1)

    print(f"Found {len(audio_files)} audio file(s) in {data_dir}")
    print(f"Model: {model_name}")
    if args.profile:
        print(f"Profile: {args.profile}")
    print()

    for audio_path in audio_files:
        filename = os.path.basename(audio_path)
        print(f"Processing: {filename}")

        # Convert to WAV if not already
        wav_path = None
        if not audio_path.lower().endswith(".wav"):
            print("  Converting to WAV (16kHz mono)...")
            wav_path = convert_to_wav(audio_path)
            transcribe_path = wav_path
        else:
            transcribe_path = audio_path

        try:
            # Transcribe
            print("  Transcribing (this may take a while for long recordings)...")
            result = transcribe(transcribe_path, model_name)

            # Build markdown
            md_content = build_markdown(result, args.date, filename, chunk_duration)

            # Determine output path
            if args.output:
                output_path = data_dir / args.output
            elif len(audio_files) == 1:
                output_path = data_dir / "transcript.md"
            else:
                stem = Path(filename).stem
                output_path = data_dir / f"transcript_{stem}.md"

            output_path.write_text(md_content, encoding="utf-8")
            print(f"  Saved: {output_path}")

            detected_lang = result.get("language", "unknown")
            num_segments = len(result.get("segments", []))
            print(f"  Language: {detected_lang} | Segments: {num_segments}")

        finally:
            # Clean up temp WAV
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)

        print()

    print("Done!")


if __name__ == "__main__":
    main()
