#!/usr/bin/env python3
import argparse
import json
import subprocess
import wave
from pathlib import Path

from common import add_execution_flags, read_json


def write_clip(source, target, start, end):
    with wave.open(str(source), "rb") as src:
        rate = src.getframerate()
        src.setpos(int(round(start*rate)))
        frames = src.readframes(int(round((end-start)*rate)))
        with wave.open(str(target), "wb") as dst:
            dst.setparams(src.getparams())
            dst.writeframes(frames)


def main():
    parser = argparse.ArgumentParser(description="Re-transcribe configured ambiguous regions with local whisper.cpp.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--segments", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--language", default="auto")
    add_execution_flags(parser)
    args = parser.parse_args()
    segments = read_json(args.segments)
    if not args.execute:
        print(json.dumps({"dry_run": True, "segment_count": len(segments), "model": str(args.model), "output_dir": str(args.output_dir)}, indent=2))
        return
    if not args.audio.is_file() or not args.model.is_file():
        raise RuntimeError("audio or model file is missing")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for item in segments:
        clip = args.output_dir/f"{item['name']}.wav"
        output_base = args.output_dir/item["name"]
        write_clip(args.audio, clip, float(item["start"]), float(item["end"]))
        command = ["whisper-cli", "-m", str(args.model), "-f", str(clip), "-l", args.language]
        if item.get("prompt"):
            command.extend(["--prompt", item["prompt"]])
        command.extend(["-otxt", "-osrt", "-of", str(output_base), "-np"])
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        results.append({**item, "transcript": output_base.with_suffix(".txt").read_text(encoding="utf-8").strip()})
    output = args.output_dir/"refined_segments.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

