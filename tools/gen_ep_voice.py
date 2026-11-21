#!/usr/bin/env python3
"""ep009 장면별 음성을 Gemini TTS로 미리 만들어 episodes/ep009/voice/에 저장한다.

무료 등급 3 RPM / 10 RPD를 지키려고 요청 사이에 25초씩 쉰다.
이미 만든 파일이 있으면 건너뛴다.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts_gemini as g

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "episodes" / "ep009"
VOICE = g.os.environ.get("GEMINI_TTS_VOICE", "Charon")


def scene_texts(ep_dir):
    spec = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    texts = []
    hook_parts = spec.get("hook_voice_parts") or [{"text": spec.get("hook_voice") or spec["hook_en"]}]
    texts.append(" ".join(p["text"].strip() for p in hook_parts if p.get("text", "").strip()))
    for sc in spec["scenes"] + ([spec["cta"]] if spec.get("cta") else []):
        parts = sc.get("voice_parts") or [{"text": sc.get("voice") or ""}]
        texts.append(" ".join(p["text"].strip() for p in parts if p.get("text", "").strip()))
    return texts


if __name__ == "__main__":
    out_dir = EP / "voice"
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = scene_texts(EP)
    first = True
    for i, t in enumerate(texts):
        dst = out_dir / f"v{i}.wav"
        if dst.exists() and dst.stat().st_size > 1000:
            print(f"skip v{i} (exists)", flush=True)
            continue
        if not first:
            time.sleep(25)
        first = False
        g.speak_to_wav(t, dst, voice=VOICE)
        print(f"OK v{i} <- {t[:60]!r}", flush=True)
