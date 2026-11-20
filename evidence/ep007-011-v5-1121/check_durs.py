#!/usr/bin/env python3
"""Simulate build.py timing for an episode: per-scene VO length and final duration.

Usage: FFMPEG=<ffmpeg> python3 check_durs.py episodes/ep009 [episodes/ep010 ...]
Prints each scene's VO seconds, the effective duration build.py will use
(max(spec dur, vo + delay + 0.2)), and the running timeline so the v5
0-3 / 3-15 / 15-18 / 18-21 cadence and the 20-22 s total can be checked.
"""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # work/chopstick-shorts
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402


def main(dirs):
    for d in dirs:
        ep = Path(d)
        spec = json.loads((ep / "script.json").read_text(encoding="utf-8"))
        scenes = [{"kind": "hook", "text": spec["hook_en"], "voice": spec.get("hook_voice", spec["hook_en"]),
                   "voice_parts": spec.get("hook_voice_parts"), "dur": spec.get("hook_dur", 3.0),
                   "img": spec.get("hook_img", ""), "video": spec.get("hook_video", ""),
                   "bg": spec.get("hook_bg", "seoul_night")}]
        scenes += [dict(s, kind="phrase") for s in spec["scenes"]]
        if spec.get("cta"):
            scenes.append(dict(spec["cta"], kind="phrase"))

        work = Path(tempfile.mkdtemp())
        t = 0.0
        print(f"=== {spec['id']}")
        for i, sc in enumerate(scenes):
            v = build.speak(sc, work, f"v{i}")
            vo = build.wav_seconds(v) if v else 0.0
            delay = 0.0 if sc["kind"] == "hook" else build.VOICE_DELAY
            dur = max(build.scene_dur(sc), (vo + delay + 0.2) if v else 0)
            name = sc["kind"] if i == 0 else (sc.get("ko") or sc.get("en", "")[:22])
            print(f"  {i} {sc['kind']:6s} {name[:26]:28s} vo={vo:5.2f}  dur={dur:5.2f}  {t:5.2f} -> {t + dur:5.2f}")
            t += dur
        print(f"  TOTAL {t:.2f}s  (target 20-22, max 23)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["episodes/ep009"])
