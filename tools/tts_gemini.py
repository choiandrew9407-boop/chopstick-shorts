#!/usr/bin/env python3
"""Gemini TTS (Google AI Studio) backend for Chopstick Club.

한 번의 REST 호출로 텍스트 하나를 WAV로 만든다.
`gemini-3.8-flash-tts` 무료 등급 한도는 3 RPM / 10 RPD / 10K TPM 이므로
장면마다 부르면 하루 2편이 한계다 — build.py는 `voice_gemini.wav`가 이미 있으면
API를 부르지 않는다(사전 생성 오디오를 커밋하는 방식).

키는 환경변수 GEMINI_API_KEY 또는 `private/gemini_api.key`(워크스페이스, 저장소 밖)에서 읽는다.
키는 절대 로그·파일·저장소에 남기지 않는다.

사용:
    python tools/tts_gemini.py --text "Koreans leave a laptop." --voice Neno --out a.wav
    python tools/tts_gemini.py --script "path.txt" --voice Charon --out b.wav
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
DEFAULT_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Neno")
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
KEY_FILES = [ROOT.parent.parent / "private/gemini_api.key", Path("/workspace/private/gemini_api.key")]


def api_key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if k:
        return k.strip()
    for p in KEY_FILES:
        try:
            if p.is_file():
                return p.read_text().strip()
        except OSError:
            pass
    raise SystemExit("GEMINI_API_KEY 없음 — private/gemini_api.key 또는 환경변수로 지정하세요")


def transcript(text):
    """AI Studio Generate Speech가 만드는 형태 그대로: '## Transcript:' 아래에 대사."""
    body = text.strip()
    if body.startswith("## Transcript:"):
        return body
    return "## Transcript:\n" + body


def synthesize(text, voice=DEFAULT_VOICE, model=DEFAULT_MODEL, key=None,
               temperature=1.0, timeout=180, retries=3):
    """텍스트 → (pcm bytes, sample_rate). 실패하면 RuntimeError."""
    key = key or api_key()
    url = f"{API_ROOT}/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": transcript(text)}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }
    data = json.dumps(payload).encode()
    err = "unknown"
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            err = f"HTTP {e.code}: {detail}"
            if e.code in (429, 500, 503):     # RPM/일시 오류 → 잠시 쉬고 재시도
                time.sleep(8 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini TTS {voice} 실패 — {err}")
        except Exception as e:                # 네트워크
            err = str(e)
            time.sleep(5 * (attempt + 1))
            continue
        for cand in body.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    mime = inline.get("mimeType") or inline.get("mime_type") or ""
                    rate = 24000
                    m = re.search(r"rate=(\d+)", mime)
                    if m:
                        rate = int(m.group(1))
                    return base64.b64decode(inline["data"]), rate
        err = f"응답에 오디오 없음: {json.dumps(body)[:300]}"
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"Gemini TTS {voice} 실패 — {err}")


def write_wav(pcm, rate, out, channels=1, width=2):
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out


def speak_to_wav(text, out, voice=DEFAULT_VOICE, model=DEFAULT_MODEL, key=None):
    pcm, rate = synthesize(text, voice=voice, model=model, key=key)
    return write_wav(pcm, rate, Path(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--script", help="대사가 든 텍스트 파일")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", required=True)
    ap.add_argument("--temperature", type=float, default=1.0)
    a = ap.parse_args()
    text = a.text
    if not text and a.script:
        text = Path(a.script).read_text(encoding="utf-8")
    if not text:
        text = sys.stdin.read()
    p = speak_to_wav(text, a.out, voice=a.voice, model=a.model)
    with wave.open(str(p)) as w:
        dur = w.getnframes() / w.getframerate()
    print(f"{a.voice}: {dur:.2f}s -> {p}")


if __name__ == "__main__":
    main()
