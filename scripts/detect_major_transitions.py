#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from common import add_execution_flags, read_json


def main():
    parser = argparse.ArgumentParser(description="Find visual transitions near configured times.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--boundaries", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--radius", type=float, default=0.9)
    add_execution_flags(parser)
    args = parser.parse_args()
    boundaries = read_json(args.boundaries)
    if not args.execute:
        print(json.dumps({"dry_run": True, "boundary_count": len(boundaries), "output_dir": str(args.output_dir)}, indent=2))
        return
    import cv2
    import numpy as np
    args.output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    fps, frames = float(capture.get(cv2.CAP_PROP_FPS)), []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames or fps <= 0:
        raise RuntimeError("unable to decode video")
    h, w = frames[0].shape[:2]
    rois = [cv2.resize(cv2.cvtColor(frame[int(h*.30):int(h*.58), int(w*.08):int(w*.92)], cv2.COLOR_BGR2GRAY), (240, 140)) for frame in frames]
    results = []
    for item in boundaries:
        center, radius = int(round(float(item["approximate_time"])*fps)), int(round(args.radius*fps))
        candidates = [(float(np.mean(cv2.absdiff(rois[index-1], rois[index]))), index) for index in range(max(1, center-radius), min(len(frames)-1, center+radius)+1)]
        if not candidates:
            raise RuntimeError(f"empty search window: {item['name']}")
        score, index = max(candidates)
        results.append({**item, "candidate_frame": index, "candidate_time": round(index/fps, 6), "score": round(score, 6)})
    output = {"fps": fps, "frame_count": len(frames), "results": results}
    (args.output_dir/"transitions.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

