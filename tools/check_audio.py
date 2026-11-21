#!/usr/bin/env python3
"""생성한 샘플을 Gemini 텍스트 모델로 전사해 한국어 단어 발음을 확인한다 (검수용, 저장소 밖에서 임시 실행)."""
import base64
import json
import sys
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts_gemini as g

MODEL = "gemini-3.5-flash"
PROMPT = (
    "You are checking a TTS render for a Korean-culture YouTube Short. "
    "1) Transcribe the audio word for word. "
    "2) Quote exactly how the Korean word 카공 (kagong) was pronounced in the audio — "
    "did it come out as natural Korean, as English letters, or garbled? "
    "3) Rate naturalness 1-10 for an English-language narration that mixes one Korean word. "
    "Answer briefly in 4 lines."
)


def wav_b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


def check(path):
    key = g.api_key()
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": PROMPT},
            {"inlineData": {"mimeType": "audio/wav", "data": wav_b64(path)}},
        ]}],
        "generationConfig": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read().decode())
    parts = body["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("=" * 20, p)
        try:
            print(check(p), flush=True)
        except Exception as e:
            print("FAIL", e)
