#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from common import add_execution_flags, read_json


def main():
    parser = argparse.ArgumentParser(description="Detect caption boundaries near planned overlay times.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--radius", type=float, default=1.0)
    add_execution_flags(parser)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"dry_run": True, "video": str(args.video), "manifest": str(args.manifest), "output": str(args.output), "radius": args.radius}, indent=2))
        return
    import cv2
    import numpy as np
    rows = read_json(args.manifest).get("matched", [])
    if len(rows) != 1 or not rows[0].get("text_overlays"):
        raise RuntimeError("exactly one matched row with text_overlays is required")
    capture = cv2.VideoCapture(str(args.video))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames or fps <= 0:
        raise RuntimeError("unable to decode video")

    def scores_for(overlay):
        values = []
        for frame in frames:
            height, width = frame.shape[:2]
            center = int(round((1.0 - float(overlay["transform_y"])) * height / 2.0))
            half = max(24, int(round((0.14 if overlay.get("role") == "title" else 0.10) * height / 2.0)))
            gray = cv2.cvtColor(frame[max(0, center-half):min(height, center+half), int(width*.025):int(width*.975)], cv2.COLOR_BGR2GRAY)
            values.append(float(((gray >= 185) & (cv2.dilate((gray <= 105).astype(np.uint8), np.ones((7, 7), np.uint8), iterations=1) > 0)).mean()))
        return np.array(values)

    def detect(scores, at, direction):
        center, radius, window = int(round(at*fps)), int(round(args.radius*fps)), max(2, int(round(fps*.10)))
        candidates = []
        for index in range(max(window, center-radius), min(len(scores)-window-1, center+radius)+1):
            before, after = float(np.mean(scores[index-window:index])), float(np.mean(scores[index:index+window]))
            delta = after-before
            candidates.append((delta if direction == "on" else -delta, index))
        if not candidates:
            raise RuntimeError("caption boundary search window is empty")
        delta, index = max(candidates)
        return {"frame": index, "time": round(index/fps, 6), "directed_delta": round(delta, 8)}

    detections = []
    for overlay in rows[0]["text_overlays"]:
        scores = scores_for(overlay)
        start, end = float(overlay["start"]), float(overlay["start"])+float(overlay["duration"])
        detections.append({"track_name": overlay["track_name"], "text": overlay["text"], "planned_start": start, "planned_end": end, "detected_on": {"frame": 0, "time": 0.0} if start <= 0 else detect(scores, start, "on"), "detected_off": {"frame": len(frames), "time": round(len(frames)/fps, 6)} if end >= len(frames)/fps-1/fps else detect(scores, end, "off")})
    result = {"video": str(args.video.resolve()), "fps": fps, "frame_count": len(frames), "cloud_calls": 0, "detections": detections}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

