#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from common import add_execution_flags, read_json


def main():
    parser = argparse.ArgumentParser(description="Create frame-review sheets for configured windows.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--windows", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    windows = read_json(args.windows)
    if not args.execute:
        print(json.dumps({"dry_run": True, "window_count": len(windows), "output_dir": str(args.output_dir)}, indent=2))
        return
    import cv2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        raise RuntimeError("unable to read fps")
    outputs = []
    for window in windows:
        panels, current = [], float(window["start"])
        while current <= float(window["end"])+1e-9:
            index = int(round(current*fps))
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                break
            frame = cv2.resize(frame, (360, 640))
            cv2.putText(frame, f"f{index} {index/fps:.3f}s", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .55, (0,255,255), 1, cv2.LINE_AA)
            panels.append(frame)
            current += float(window["step"])
        if not panels:
            raise RuntimeError(f"no frames for window: {window['name']}")
        columns, blank = 5, panels[0]*0
        panels.extend(blank.copy() for _ in range((-len(panels)) % columns))
        rows = [cv2.hconcat(panels[i:i+columns]) for i in range(0, len(panels), columns)]
        output = args.output_dir/f"{window['name']}.jpg"
        cv2.imwrite(str(output), cv2.vconcat(rows), [cv2.IMWRITE_JPEG_QUALITY, 92])
        outputs.append(str(output))
    capture.release()
    print(json.dumps({"dry_run": False, "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

