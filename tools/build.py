#!/usr/bin/env python3
"""Chopstick Club shorts builder — v3 (real-clip pipeline + tempo patch).

Per scene the background comes from the first of these that exists:
    `video`  real stock clip (MP4 from Pexels/Pixabay/Mixkit) — cut to 1080x1920, graded, cover-cropped
    `img`    photo/illustration PNG
    `bg`     illustrated Korean background drawn by tools/scenes.py
A scene with a `video` keeps the subtitle card and channel tag over the footage and drops the
ken-burns pan (the footage already moves).

v3 tempo patch (Claude 25차): hook 1.5 s, card bottom margin 170 px with card top >= 940 px,
ken-burns 1.00->1.06 with a 1.00->1.12 punch on `twist` scenes, slide cut every 3rd cut,
subtitle fade 0.12 s, voice +0.1 s, -14 LUFS loudnorm.

v4 voice (Claude/은석님 피드백): 네이티브 발음 분리 합성.
    장면마다 `voice_parts` [{"lang":"ko"|"en","text":...}]를 받아 **한국어는 ko-KR-InJoonNeural,
    영어는 en-US-AndrewMultilingualNeural**(edge-tts, 무료)로 따로 만들고 0.12 s 간격 + 파트별
    레벨 정규화 후 이어 붙인다. 로마자(ppalli-ppalli)를 영어 음성으로 읽던 문제를 없앤다.
    `voice_parts`가 없는 장면은 기존 `voice` 문자열을 영어 뉴럴 음성으로 읽는다(ep004~011 호환).
    edge-tts가 없거나 실패하면 Piper(PIPER_MODEL)로 fallback.

v5 voice (은석님 "Google AI Studio 잘생긴 남자 목소리"): 장면 음성을 **Gemini TTS**(Google AI Studio,
    기본 `gemini-3.8-flash-tts` + `Charon`)로 바꿨다. 순서는 ① `episodes/<ep>/voice/v{i}.wav` 사전 생성본
    (저장소에 커밋, API 호출 0회) ② `GEMINI_TTS_VOICE`가 지정돼 있으면 API 실시간 생성 ③ 실패하면 기존
    edge-tts 한/영 분리 ④ Piper. Gemini는 한국어 단어(카공)를 한 목소리로 자연스럽게 읽으므로
    ko/en 파트를 나누지 않고 이어 붙인다. 속도는 `GEMINI_TTS_TEMPO`(기본 1.08배)로 21~22초 규격에 맞춘다.

v6 audio/loop (은석님 2026-11-23 "소리 치직거리고 루프 어디 감"): 장면 음성에 -1.5 dB 헤드룸을 주고
    (`_gemini_wav`), 최종 믹스는 **2패스 loudnorm(I=-14, TP=-2.5) + alimiter(-2.5 dBFS) + aresample=44100**
    으로 피크를 -2 dB 이하에 고정한다(기존 1패스 loudnorm은 피크가 0 dBFS까지 올라가 AAC 뒤 치직거렸다).
    오디오는 192k. 장면에 `beats`를 주면 한 음성 줄 안에서 카드가 여러 번 바뀌고(펀치 줌 동반),
    최종 MP4가 20MB를 넘으면 영상만 CRF 23으로 자동 재인코딩한다.

Needs: ffmpeg (FFMPEG env var or on PATH), Pillow, Noto Sans CJK fonts, tools/scenes.py.
Optional: edge-tts (권장), Piper TTS (PIPER_MODEL env, fallback), GEMINI_API_KEY(실시간 Gemini TTS).
Usage: python tools/build.py episodes/ep001 [episodes/ep002 ...]
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenes import DEFAULT_CYCLE, Particles, draw_scene, glow_sprite  # noqa: E402

# 자막 트랙 언어: 영/베트남/인도네시아 + 대륙별 대표 4개(스페인/포르투갈(브라질)/아랍/필리핀) + 힌디어
LANGS = ("en", "vi", "id", "es", "pt", "ar", "fil", "hi")

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = int(H * 0.15), int(H * 0.80)  # keep text out of Shorts UI zones
ROOT = Path(__file__).resolve().parent.parent

# --- v3 tempo ---
HOOK_SEC = 1.5            # 훅 구간: 태그 숨김
CARD_BOTTOM_MARGIN = 170  # 카드 최소 하단 여백
CARD_MIN_TOP = 940        # 카드 상단은 이 아래로 내려가지 않음
GRADE = ("eq=saturation=1.08:contrast=1.05:brightness=0.01,"
         "unsharp=5:5:0.5,noise=alls=4:allf=t")
LOUDNORM = "loudnorm=I=-14:TP=-2.5:LRA=7"   # (v6) 2-pass + 리미터 — loudnorm_filter() 참고
LOUD_I, LOUD_TP, LOUD_LRA = -14.0, -2.5, 7.0
LIMIT_DB = -2.5                 # 최종 브릭월 리미터(-2.5 dBFS): AAC 인코딩 오버슈트 여유
AUDIO_BITRATE = "192k"          # 128k → 192k (재인코딩 시 치직거림 여지 축소)
MAX_MB = 20.0                   # 유튜브 브라우저 업로드 한도(별도 재압축 불필요)
VOICE_DELAY = 0.1         # 자막이 음성보다 0.1 s 먼저
SLIDE_SEC = 0.15

# --- v4 voice (edge-tts neural, native Korean/English split) ---
EN_VOICE = os.environ.get("EDGE_EN_VOICE", "en-US-AndrewMultilingualNeural")
KO_VOICE = os.environ.get("EDGE_KO_VOICE", "ko-KR-InJoonNeural")
RATE = {"en": os.environ.get("EDGE_EN_RATE", "+5%"), "ko": os.environ.get("EDGE_KO_RATE", "+3%")}
PART_GAP = 0.12           # 한국어 단어 <-> 영어 문장 사이 숨
PART_MEAN_DB = -20.0      # 파트별 평균 음량 목표(두 목소리 크기 맞춤)
TRIM_SILENCE = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,"
                "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,areverse")
EDGE_PIP_SPEC = "edge-tts==7.3.1"   # 워크플로에 pip 설치가 없어도 build.py가 직접 설치

# --- v5 voice (Gemini TTS, Google AI Studio) ---
GEMINI_VOICE = os.environ.get("GEMINI_TTS_VOICE", "")      # 비우면 사전 생성본/edge-tts
GEMINI_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
GEMINI_TEMPO = float(os.environ.get("GEMINI_TTS_TEMPO", "1.10"))  # 21~22초 규격 맞춤
VOICE_SUBDIR = "voice"            # episodes/<ep>/voice/v{i}.wav (커밋된 사전 생성본)

FONT_DIRS = [ROOT / "assets/fonts", Path("/usr/share/fonts/opentype/noto"),
             Path("/usr/share/fonts/opentype/noto-cjk"), Path("/usr/share/fonts/noto-cjk")]


def ffmpeg_bin():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


FF = ffmpeg_bin()


def font(weight, size):
    names = {"bold": ["NotoSansCJK-Bold.ttc", "NotoSansCJKkr-Bold.otf", "Pretendard-Bold.otf"],
             "regular": ["NotoSansCJK-Regular.ttc", "NotoSansCJKkr-Regular.otf", "Pretendard-Regular.otf"]}[weight]
    for d in FONT_DIRS:
        for n in names:
            p = d / n
            if p.exists():
                # index 1 = KR face inside the .ttc collections
                return ImageFont.truetype(str(p), size, index=1 if p.suffix == ".ttc" else 0)
    raise SystemExit("Korean font not found: install fonts-noto-cjk or put Pretendard in assets/fonts")


# 이모지·변형선택자·ZWJ: Noto Sans CJK에 글리프가 없어 카드에 두부(□) 박스로 찍힌다.
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F\u200D\u20E3]")


def clean(text):
    """카드에 그릴 텍스트에서 폰트가 못 그리는 이모지를 지운다(자막 .srt에는 그대로 남는다)."""
    return _EMOJI.sub("", text or "").strip()


def wrap(draw, text, fnt, max_w):
    """단어 단위 최소 raggedness 줄바꿈.

    왼쪽부터 채우는 방식은 마지막 줄에 단어 하나만 남기 쉽다(예: "Would you study here? Yes or / no?").
    줄 폭의 제곱합을 최소로 하는 분할을 골라 두 줄이 고르게 나뉜다. 글자 수·줄 수는 그대로다.
    """
    words = text.split(" ")
    n = len(words)
    if n <= 1:
        return [text]
    INF = float("inf")
    dp = [INF] * (n + 1)
    prev = [0] * (n + 1)
    dp[0] = 0.0
    for j in range(1, n + 1):
        for i in range(j):
            w = draw.textlength(" ".join(words[i:j]), font=fnt)
            if w > max_w and j - i > 1:   # 넘치는 줄은 단어 하나짜리만 허용
                continue
            cost = (max_w - w) ** 2
            if dp[i] + cost < dp[j]:
                dp[j] = dp[i] + cost
                prev[j] = i
    lines, j = [], n
    while j > 0:
        lines.append(" ".join(words[prev[j]:j]))
        j = prev[j]
    return lines[::-1]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"command failed: {' '.join(str(c) for c in cmd[:4])} ...")
    return r


# ---------------------------------------------------------------- v6 audio
def _loudnorm_measure(src):
    """1패스 측정: loudnorm JSON(입력 I/TP/LRA/thresh)을 돌려준다. 실패하면 None."""
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", str(src), "-af",
                        f"loudnorm=I={LOUD_I:g}:TP={LOUD_TP:g}:LRA={LOUD_LRA:g}:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    blocks = re.findall(r"\{[^{}]*\}", r.stderr or "")
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1])
    except Exception:
        return None


def loudnorm_filter(src):
    """(v6) 2패스 loudnorm + 브릭월 리미터 + 44.1k 리샘플.

    기존 1패스 `loudnorm=I=-16:TP=-1.5`는 게인만 계산해 적용하므로 피크가 0 dBFS까지
    올라가고(측정 max_volume 0.0 dB, 0 dB 샘플 79개) AAC 인코딩 뒤 치직거림이 됐다.
    여기서는 ① 측정값을 넣은 2패스 loudnorm(TP -2.5 dBFS) ② alimiter(-2.5 dBFS, 자동 레벨 끔)
    ③ aresample=44100 순으로 걸어 최종 피크를 -2 dB 이하로 고정한다.
    """
    m = _loudnorm_measure(src)
    f = f"loudnorm=I={LOUD_I:g}:TP={LOUD_TP:g}:LRA={LOUD_LRA:g}"
    if m and m.get("input_i") not in (None, "-inf", "-nan"):
        f += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}")
    lim = 10 ** (LIMIT_DB / 20.0)          # dBFS → 선형 진폭
    return f + (f",alimiter=limit={lim:.6f}:attack=5:release=80:level=0"
                ",aresample=44100")


def max_volume_db(path):
    """최종 파일의 디코드 피크(dBFS)를 잰다. 클리핑 검사·보고용."""
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr or "")
    z = re.search(r"histogram_0db:\s*(\d+)", r.stderr or "")
    return (float(m.group(1)) if m else None), (int(z.group(1)) if z else 0)


# ---------------------------------------------------------------- v3 helpers
def scene_dur(scene):
    if "dur" in scene:
        return float(scene["dur"])
    return 3.2 if scene.get("twist") else 2.5


def zoom_at(t, dur, twist):
    """배경 확대율. 기본 켄번스 1.00→1.06, 반전 장면은 0.2s 펀치 1.00→1.12 후 유지."""
    if twist:
        return 1.0 + 0.12 * min(t / 0.2, 1.0)
    return 1.0 + 0.06 * (t / max(dur, 0.01))


def pan_dir(idx):
    return 1 if idx % 2 == 0 else -1   # 장면마다 이동 방향 교대


def transition_for(cut_idx):
    """기본 하드 컷, 3컷마다 1번만 0.15s 슬라이드. 크로스페이드 금지."""
    return ("slideleft", SLIDE_SEC) if cut_idx % 3 == 2 else (None, 0.0)


def sub_alpha(t):
    """자막 0.12s 등장. 음성은 장면 시작 +0.1s에 붙여 '자막이 0.1s 먼저'가 되게."""
    return min(max(t / 0.12, 0.0), 1.0)


# ---------------------------------------------------------------- clip prep
def prep_clip(src, dur, out, ss=0.0):
    """스톡 클립을 1080x1920 세로로 잘라 dur초로 맞춤(짧으면 반복), 소리 제거, v3 그레이딩.

    `ss`는 클립 안에서 시작할 지점(초) — 같은 클립을 앞 장면과 다른 구간에서 다시 쓸 때 쓴다.
    """
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
          "crop=1080:1920,fps=30," + GRADE)
    if ss:
        vf = f"trim=start={ss:.3f},setpts=PTS-STARTPTS," + vf
    run([FF, "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src),
         "-t", f"{dur:.3f}", "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", str(out)])
    return out


def grade_image(src, out):
    """사진 장면에도 같은 그레이딩을 걸어 클립과 질감을 통일한다."""
    run([FF, "-y", "-loglevel", "error", "-i", str(src), "-vf", GRADE, str(out)])
    return out


def scene_source(ep_dir, scene):
    v = scene.get("video")
    if v and (ep_dir / v).is_file():
        return ("video", ep_dir / v)
    i = scene.get("img")
    if i and (ep_dir / i).is_file():
        return ("img", ep_dir / i)
    return ("bg", scene.get("bg"))


# ---------------------------------------------------------------- overlays
def text_layer(scene, kind, show_tag=True):
    """Transparent 1080x1920 overlay: hook text, or Korean / romanization / English card."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    max_w = W - 140
    if kind == "hook":
        f = font("bold", 92)
        lines = wrap(d, clean(scene["text"]), f, max_w)
        lh = 118
        y = (H - lh * len(lines)) // 2 - 80
        pad = 48
        d.rounded_rectangle((40, y - pad, W - 40, y + lh * len(lines) + pad), 36, fill=(0, 0, 0, 150))
        for i, ln in enumerate(lines):
            d.text((W // 2, y + i * lh + lh // 2), ln, font=f, fill="white", anchor="mm")
        if show_tag:
            d.text((W - 80, y + lh * len(lines) + pad - 14), "Chopstick Club", font=font("bold", 34),
                   fill=(255, 255, 255, 170), anchor="rm")
        return layer
    fl = font("bold", 50)
    if not scene.get("ko"):
        # v4 스토리형: 한국어 표현이 없는 설명·결론 장면은 영어 한 줄기 카드로 크게 보여 준다.
        fe2 = font("bold", 72)
        en = wrap(d, clean(scene["en"]), fe2, max_w)
        li = wrap(d, clean(scene.get("like", "")), fl, max_w) if scene.get("like") else []
        block = len(en) * 94 + len(li) * 66
        top = max(CARD_MIN_TOP, SAFE_BOTTOM - block - CARD_BOTTOM_MARGIN)
        d.rounded_rectangle((40, top - 50, W - 40, top + block + 60), 40, fill=(0, 0, 0, 160))
        y = top
        for ln in en:
            d.text((W // 2, y + 47), ln, font=fe2, fill="white", anchor="mm"); y += 94
        for ln in li:
            d.text((W // 2, y + 36), ln, font=fl, fill=(255, 226, 120), anchor="mm"); y += 66
        if show_tag:
            d.text((W - 80, top + block + 30), "Chopstick Club", font=font("bold", 34),
                   fill=(255, 255, 255, 170), anchor="rm")
        return layer
    fk, fr, fe = font("bold", 120), font("regular", 54), font("bold", 64)
    ko = wrap(d, clean(scene["ko"]), fk, max_w)
    en = wrap(d, clean(scene["en"]), fe, max_w)
    # `like`: 카드 맨 아래 한 줄짜리 좋아요 CTA(마지막 장면용, 영어 고정)
    li = wrap(d, clean(scene.get("like", "")), fl, max_w) if scene.get("like") else []
    block = len(ko) * 150 + 90 + len(en) * 84 + len(li) * 66
    if scene.get("card") == "top":
        top = CARD_MIN_TOP
    else:
        # v3: 카드 상단 y >= 940 보장 + 하단 여백 170px 고정
        top = max(CARD_MIN_TOP, SAFE_BOTTOM - block - CARD_BOTTOM_MARGIN)
    d.rounded_rectangle((40, top - 50, W - 40, top + block + 90), 40, fill=(0, 0, 0, 160))
    y = top
    for ln in ko:
        d.text((W // 2, y + 75), ln, font=fk, fill=(255, 226, 120), anchor="mm"); y += 150
    d.text((W // 2, y + 40), clean(scene.get("roman", "")), font=fr, fill=(220, 220, 220), anchor="mm"); y += 90
    for ln in en:
        d.text((W // 2, y + 42), ln, font=fe, fill="white", anchor="mm"); y += 84
    for ln in li:
        d.text((W // 2, y + 36), ln, font=fl, fill=(255, 226, 120), anchor="mm"); y += 66
    # channel tag lives inside the card, so it never collides with signs/displays
    if show_tag:
        d.text((W - 80, top + block + 55), "Chopstick Club", font=font("bold", 34),
               fill=(255, 255, 255, 170), anchor="rm")
    return layer


def fade_in(img, alpha):
    if alpha >= 1:
        return img
    out = img.copy()
    out.putalpha(out.getchannel("A").point(lambda v, a=alpha: int(v * a)))
    return out


# ---------------------------------------------------------------- v6 beats
def scene_layers(sc, kind, dur, show_tag=True):
    """장면 하나의 자막 카드 목록 [(t0, t1, layer), ...].

    `beats`가 있으면 한 음성 줄 안에서 카드가 여러 번 바뀐다(예: "Hot water? FREE" →
    "Microwave? FREE" → "Window seat? FREE too"). 한 번의 TTS 호출을 그대로 쓰면서
    화면을 빠르게 튀겨 "템포감"을 내는 용도. 각 비트 길이는 글자 수 비례로 나눈다.
    """
    beats = sc.get("beats")
    if not beats:
        return [(0.0, float("inf"), text_layer(sc, kind, show_tag))]
    w = [max(len((b.get("en") or b.get("text") or "")), 8) for b in beats]
    tot = float(sum(w)) or 1.0
    out, acc = [], 0.0
    for b, ww in zip(beats, w):
        d = dur * ww / tot
        merged = {k: v for k, v in sc.items() if k != "beats"}
        merged.update(b)
        out.append((acc, acc + d, text_layer(merged, kind, show_tag)))
        acc += d
    return out


def pick_layer(layers, t):
    """t초에 걸리는 (시작시각, 레이어). 각 비트는 시작 0.12s 동안 페이드인."""
    cur = layers[0]
    for L in layers:
        if t >= L[0]:
            cur = L
        else:
            break
    return cur[0], cur[2]


def slide_frame(new_frame, prev_frame, p):
    """새 장면이 오른쪽에서 밀고 들어오는 0.15s 슬라이드 컷(타임라인 길이는 그대로)."""
    canvas = Image.new("RGB", (W, H))
    if prev_frame is not None:
        canvas.paste(prev_frame, (-int(W * p), 0))
    canvas.paste(new_frame, (W - int(W * p), 0))
    return canvas


# ---------------------------------------------------------------- encoders
def open_encoder(out):
    return subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(out)],
                            stdin=subprocess.PIPE)


def render_still_scene(bg, lights, layers, dur, idx, seed, particles, out, twist=False,
                       prev_frame=None, slide=False, fade=True):
    """Illustrated / photo scene: ken-burns zoom + pan, twinkling lights, particles, text card."""
    n = int(round(dur * FPS))
    sprites = [(x, y, glow_sprite(r, c)) for x, y, r, c in lights]
    parts = Particles(W, H, seed + idx, particles) if particles != "none" else None
    ff = open_encoder(out)
    slide_n = int(round(SLIDE_SEC * FPS)) if slide and prev_frame is not None else 0
    last = None
    for f in range(n):
        t = f / FPS
        z = zoom_at(t, dur, twist)
        cw, ch = W / z, H / z
        k = min(t / max(dur, 0.01), 1.0)
        ease = k * k * (3 - 2 * k)
        dx, dy = bg.width - cw, bg.height - ch
        x = dx * (ease if pan_dir(idx) == 1 else 1 - ease)
        y = dy / 2
        frame = bg.crop((int(x), int(y), int(x + cw), int(y + ch))).resize((W, H), Image.LANCZOS).convert("RGBA")
        fx = ImageDraw.Draw(frame, "RGBA")
        for j, (lx, ly, sp) in enumerate(sprites):
            a = 0.55 + 0.45 * math.sin(t * 2.4 + j * 1.7)
            s2 = sp.copy()
            s2.putalpha(s2.getchannel("A").point(lambda v, a=a: int(v * a)))
            px, py = int((lx - x) / z - sp.width / 2), int((ly - y) / z - sp.height / 2)
            if px >= 0 and py >= 0:
                frame.alpha_composite(s2, (px, py))
            else:  # alpha_composite rejects negative offsets; paste clips at the edge
                frame.paste(s2, (px, py), s2)
        if parts:
            parts.draw(fx, t)
        t0, layer = pick_layer(layers, t)
        frame.alpha_composite(fade_in(layer, sub_alpha(t - t0) if fade else 1.0))
        rgb = frame.convert("RGB")
        if f < slide_n:
            rgb = slide_frame(rgb, prev_frame, (f + 1) / (slide_n + 1))
        last = rgb
        ff.stdin.write(rgb.tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed while encoding a scene")
    return last


def render_video_scene(mp4, layers, dur, out, prev_frame=None, slide=False, fade=True,
                       punches=()):
    """Real stock footage: decode the prepped clip frame by frame, put the subtitle card on top."""
    n = int(round(dur * FPS))
    dec = subprocess.Popen([FF, "-loglevel", "error", "-i", str(mp4), "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = open_encoder(out)
    size = W * H * 3
    slide_n = int(round(SLIDE_SEC * FPS)) if slide and prev_frame is not None else 0
    last = None
    last_buf = None
    for f in range(n):
        buf = dec.stdout.read(size)
        if len(buf) < size:  # clip ran short: hold the last frame we decoded
            buf = last_buf if last_buf is not None else Image.new("RGB", (W, H)).tobytes()
        last_buf = buf
        frame = Image.frombytes("RGB", (W, H), buf).convert("RGBA")
        t = f / FPS
        # (v6) 비트 카드가 바뀔 때마다 배경을 0.22s 동안 살짝 당겼다 놓는다(펀치 줌).
        for p0 in punches:
            if p0 - 0.02 <= t < p0 + 0.22:
                z = 1.0 + 0.07 * (1.0 - max(t - p0, 0.0) / 0.22) ** 0.6
                cw, chh = int(W / z), int(H / z)
                lx, ty = (W - cw) // 2, (H - chh) // 2
                frame = frame.crop((lx, ty, lx + cw, ty + chh)).resize((W, H), Image.LANCZOS)
                break
        t0, layer = pick_layer(layers, t)
        frame.alpha_composite(fade_in(layer, sub_alpha(t - t0) if fade else 1.0))
        rgb = frame.convert("RGB")
        if f < slide_n:
            rgb = slide_frame(rgb, prev_frame, (f + 1) / (slide_n + 1))
        last = rgb
        enc.stdin.write(rgb.tobytes())
    dec.stdout.close()
    dec.wait()
    enc.stdin.close()
    if enc.wait():
        raise SystemExit("ffmpeg failed while encoding a video scene")
    return last


def wav_seconds(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def tts(text, out):
    """Piper TTS if PIPER_MODEL is set and piper is installed; else None (silent video)."""
    model = os.environ.get("PIPER_MODEL")
    if not (model and shutil.which("piper") and text):
        return None
    subprocess.run(["piper", "--model", model, "--output_file", str(out)], input=text,
                   text=True, capture_output=True, check=True)
    return out


def script_parts(sc):
    """장면의 발음 단위 목록. `voice_parts`가 없으면 기존 `voice`(영어) 한 덩어리."""
    parts = sc.get("voice_parts")
    if parts:
        out = [{"lang": (p.get("lang") or "en"), "text": p["text"].strip()}
               for p in parts if (p.get("text") or "").strip()]
        if out:
            return out
    v = (sc.get("voice") or "").strip()
    return [{"lang": "en", "text": v}] if v else []


def _edge_cmd():
    """edge-tts CLI(있으면) 또는 `python -m edge_tts`."""
    exe = shutil.which("edge-tts")
    return [exe] if exe else [sys.executable, "-m", "edge_tts"]


_EDGE_OK = None


def edge_available(auto_install=True):
    """edge-tts 사용 가능 여부. 없으면 pip로 설치를 한 번 시도(워크플로 권한 없이도 동작)."""
    global _EDGE_OK
    if _EDGE_OK is not None:
        return _EDGE_OK

    def _probe():
        try:
            return subprocess.run(_edge_cmd() + ["--help"], capture_output=True,
                                  text=True, timeout=90).returncode == 0
        except Exception:
            return False

    ok = _probe()
    if not ok and auto_install:
        sys.stderr.write(f"[tts] edge-tts not found; pip install {EDGE_PIP_SPEC}\n")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", EDGE_PIP_SPEC],
                           check=True, capture_output=True, timeout=600)
        except Exception as e:
            sys.stderr.write(f"[tts] pip install edge-tts failed: {e}\n")
        ok = _probe()
    _EDGE_OK = ok
    return ok


def _edge_part(text, lang, wav):
    """edge-tts로 한 덩어리 합성 → 44.1k 모노 WAV(앞뒤 무음 정리)."""
    voice = KO_VOICE if lang == "ko" else EN_VOICE
    mp3 = wav.with_suffix(".mp3")
    err = "unknown error"
    for attempt in range(3):
        r = subprocess.run(_edge_cmd() + ["--voice", voice,
                                           f"--rate={RATE.get(lang, '+0%')}", "--text", text,
                                           "--write-media", str(mp3)], capture_output=True, text=True)
        if r.returncode == 0 and mp3.exists() and mp3.stat().st_size > 1000:
            break
        err = (r.stderr or r.stdout or "").strip()[-300:]
        time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"edge-tts {voice}: {err}")
    run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-af", TRIM_SILENCE,
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(wav)])
    mp3.unlink(missing_ok=True)


def _mean_db(wav):
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", str(wav),
                        "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def _match_level(wav):
    """한국어·영어 목소리 크기를 같은 평균 음량으로 맞춘다(파트별 ±12 dB 한도)."""
    db = _mean_db(wav)
    if db is None:
        return
    gain = max(-12.0, min(12.0, PART_MEAN_DB - db))
    tmp = wav.with_name(wav.stem + "_lvl.wav")
    run([FF, "-y", "-loglevel", "error", "-i", str(wav), "-af", f"volume={gain:.1f}dB",
         "-c:a", "pcm_s16le", str(tmp)])
    tmp.replace(wav)


def _join_parts(wavs, out, gap=PART_GAP):
    """파트들을 gap초 무음으로 이어 한 WAV로."""
    with wave.open(str(wavs[0])) as w0:
        rate, width, ch = w0.getframerate(), w0.getsampwidth(), w0.getnchannels()
    silence = b"\x00" * int(rate * gap) * width * ch
    with wave.open(str(out), "wb") as o:
        o.setnchannels(ch); o.setsampwidth(width); o.setframerate(rate)
        for i, w in enumerate(wavs):
            with wave.open(str(w)) as r:
                o.writeframes(r.readframes(r.getnframes()))
            if i < len(wavs) - 1:
                o.writeframes(silence)


def _gemini_wav(src, out, tempo=None):
    """Gemini TTS WAV을 파이프라인 규격으로: 앞뒤 무음 정리 + atempo(기본 1.10배) + 44.1k 모노.

    Gemini 음성은 edge-tts보다 8~15% 느려 그대로 쓰면 22초를 넘는다(ep009 24.1초).
    atempo는 피치를 유지하므로 목소리 결은 그대로다.
    `tempo`를 주면 그 값을 쓰고(대본의 `voice_tempo`), 없으면 GEMINI_TTS_TEMPO 기본값.
    """
    tempo = GEMINI_TEMPO if tempo is None else float(tempo)
    af = TRIM_SILENCE
    if abs(tempo - 1.0) > 0.01:
        af += f",atempo={min(max(tempo, 0.5), 2.0):.3f}"
    # (v6) Gemini 출력은 피크가 0 dBFS라 24k→44.1k 리샘플 뒤 s16 양자화에서 잘린다.
    #       -1.5 dB 헤드룸을 두고 저장(최종 loudnorm이 다시 -14 LUFS로 올린다).
    af += ",volume=-1.5dB"
    run([FF, "-y", "-loglevel", "error", "-i", str(src), "-af", af,
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(out)])
    return out


def speak(sc, work, stem, ep_dir=None, tempo=None):
    """장면 하나의 목소리 트랙.

    ① episodes/<ep>/voice/<stem>.wav 사전 생성본(커밋됨, API 호출 없음)
    ② GEMINI_TTS_VOICE 지정 시 Gemini API 실시간 생성
    ③ edge-tts(한/영 분리) ④ Piper
    """
    parts = script_parts(sc)
    if not parts:
        return None
    out = work / f"{stem}.wav"

    if ep_dir is not None:
        pre = Path(ep_dir) / VOICE_SUBDIR / f"{stem}.wav"
        if pre.is_file() and pre.stat().st_size > 1000:
            return _gemini_wav(pre, out, tempo)

    if GEMINI_VOICE:
        try:
            from tts_gemini import speak_to_wav   # 같은 tools/ 디렉터리
            tmp = work / f"{stem}_raw.wav"
            speak_to_wav(" ".join(p["text"] for p in parts), tmp,
                         voice=GEMINI_VOICE, model=GEMINI_MODEL)
            return _gemini_wav(tmp, out, tempo)
        except Exception as e:      # 키 없음·한도 초과·네트워크 → edge-tts
            sys.stderr.write(f"[tts] Gemini TTS failed on {stem}: {e}\n[tts] falling back to edge-tts\n")

    if edge_available():
        try:
            wavs = []
            for j, p in enumerate(parts):
                w = work / f"{stem}_{j}_{p['lang']}.wav"
                _edge_part(p["text"], p["lang"], w)
                _match_level(w)
                wavs.append(w)
            _join_parts(wavs, out)
            return out
        except Exception as e:  # edge-tts 불통(차단·네트워크) → Piper
            sys.stderr.write(f"[tts] edge-tts failed on {stem}: {e}\n[tts] falling back to Piper\n")
    return tts(" ".join(p["text"] for p in parts), out)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


SRT_LINE = 42   # 자막 한 줄 최대 글자수(은석님 규격)


def srt_wrap(text):
    """자막 본문을 한 줄 42자 이내로 끊는다(이미 여러 줄이면 각 줄마다)."""
    out = []
    for seg in (text or "").split("\n"):
        out.extend(textwrap.wrap(seg, width=SRT_LINE, break_long_words=False) or [""])
    return "\n".join(out)


# ---------------------------------------------------------------- build
def build(ep_dir):
    ep_dir = Path(ep_dir)
    spec = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    eid = spec["id"]
    out = ROOT / "out" / eid
    work = out / "work"
    shutil.rmtree(out, ignore_errors=True)
    work.mkdir(parents=True)
    seed = sum(map(ord, eid))
    particles = spec.get("particles", "snow")

    scenes = [{"kind": "hook", "text": spec["hook_en"], "voice": spec.get("hook_voice", spec["hook_en"]),
               "voice_parts": spec.get("hook_voice_parts"), "dur": spec.get("hook_dur", HOOK_SEC),
               "img": spec.get("hook_img", ""), "video": spec.get("hook_video", ""),
               "bg": spec.get("hook_bg", "seoul_night")}]
    scenes += [dict(s, kind="phrase") for s in spec["scenes"]]
    if spec.get("cta"):
        scenes.append(dict(spec["cta"], kind="phrase"))

    clips, voices, t, cues = [], [], 0.0, []
    prev_frame = None
    for i, sc in enumerate(scenes):
        kind, src = scene_source(ep_dir, sc)
        v = speak(sc, work, f"v{i}", ep_dir, spec.get("voice_tempo"))
        dur = scene_dur(sc)
        delay = 0.0 if sc["kind"] == "hook" else VOICE_DELAY  # 훅 음성은 0.0s 시작
        dur = max(dur, (wav_seconds(v) + delay + 0.2) if v else 0)
        layers = scene_layers(sc, sc["kind"], dur, show_tag=(sc["kind"] != "hook"))
        clip = work / f"c{i}.mp4"
        cut_name, _ = transition_for(i - 1) if i else (None, 0.0)
        slide = bool(cut_name)

        if kind == "video":
            prepped = prep_clip(src, dur, work / f"p{i}.mp4", float(sc.get("video_ss") or 0.0))
            prev_frame = render_video_scene(prepped, layers, dur, clip, prev_frame, slide,
                                            fade=(sc["kind"] != "hook"),
                                            punches=[L[0] for L in layers[1:]])
        else:
            if kind == "img":
                graded = grade_image(src, work / f"g{i}.png")
                bg = Image.open(graded).convert("RGB")
                # cover-fit with 5.5% room for the slow zoom/pan
                bw, bh = int(W * 1.055), int(H * 1.055)
                s = max(bw / bg.width, bh / bg.height)
                bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
                l, tp = (bg.width - bw) // 2, (bg.height - bh) // 2
                bg = bg.crop((l, tp, l + bw, tp + bh))
                lights = []
            else:
                bg, lights = draw_scene(src or DEFAULT_CYCLE[i % len(DEFAULT_CYCLE)],
                                        int(W * 1.055), int(H * 1.055), seed + i)
            indoor = (sc.get("bg") in ("bapsang", "elevator"))
            prev_frame = render_still_scene(bg, lights, layers, dur, i, seed,
                                            "none" if indoor else particles, clip,
                                            twist=bool(sc.get("twist")),
                                            prev_frame=prev_frame, slide=slide,
                                            fade=(sc["kind"] != "hook"))
        clips.append(clip)
        voices.append((v, dur, delay))
        if sc["kind"] == "phrase":
            cues.append((t, t + dur, sc))
        else:
            cues.append((t, t + dur, {"en": sc["text"],
                                      **{l: spec.get(f"hook_{l}", sc["text"])
                                         for l in LANGS if l != "en"}}))
        t += dur

    # video track
    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    silent = work / "video.mp4"
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])

    # voice track: each scene's voice delayed 0.1s and padded to the scene length
    parts = []
    for i, (v, dur, delay) in enumerate(voices):
        p = work / f"a{i}.wav"
        src = ["-i", str(v)] if v else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        ms = int(delay * 1000)
        af = (f"adelay={ms}|{ms}," if ms else "") + f"apad=whole_dur={dur:.3f}"
        run([FF, "-y", "-loglevel", "error", *src, "-af", af, "-t", f"{dur:.3f}",
             "-ar", "44100", "-ac", "2", str(p)])
        parts.append(p)
    alst = work / "audio.txt"
    alst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    voice = work / "voice.wav"
    run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(alst), "-c", "copy", str(voice)])

    final = out / f"{eid}.mp4"
    music = ROOT / "assets/music" / spec.get("music", "")
    if spec.get("music") and music.exists():
        # BGM이 있을 때만 믹스 → 믹스 결과를 2패스 loudnorm(TP -2.5 dBFS)에 넘긴다.
        mixed = work / "mix.wav"
        run([FF, "-y", "-loglevel", "error", "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex",
             (f"[1]volume=0.10,afade=t=out:st={t - 1.5:.2f}:d=1.5[m];"
              "[0][m]amix=inputs=2:duration=first:normalize=0[o]"),
             "-map", "[o]", "-c:a", "pcm_s16le", str(mixed)])
        run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(mixed),
             "-map", "0:v", "-map", "1:a", "-af", loudnorm_filter(mixed),
             "-c:v", "copy", "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "44100",
             "-t", f"{t:.3f}", "-movflags", "+faststart", str(final)])
    else:
        run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice),
             "-map", "0:v", "-map", "1:a", "-af", loudnorm_filter(voice), "-c:v", "copy", "-c:a", "aac",
             "-b:a", AUDIO_BITRATE, "-ar", "44100", "-shortest", "-movflags", "+faststart", str(final)])

    # 20MB 초과면 영상만 CRF 23으로 한 번 더 줄인다(브라우저 업로드 한도 통과, 오디오는 그대로).
    mb = final.stat().st_size / 1e6
    if mb > MAX_MB:
        small = work / "small.mp4"
        run([FF, "-y", "-loglevel", "error", "-i", str(final), "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "23", "-maxrate", "4M", "-bufsize", "8M",
             "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(small)])
        if small.stat().st_size < final.stat().st_size:
            small.replace(final)

    for lang in LANGS:
        # 번역이 없는 언어는 만들지 않는다(영어 문장이 '힌디어 자막'으로 올라가는 사고 방지).
        # hook_<lang>이 있으면 그 언어는 대본에 반영된 것으로 본다.
        if lang != "en" and f"hook_{lang}" not in spec:
            print(f"{eid}: hook_{lang} 없음 — {lang} 자막 건너뜀")
            continue
        lines = []
        for n, (a, b, sc) in enumerate(cues, 1):
            # v4는 카드 문구(sc[lang])와 내레이션 자막(sub_<lang>)을 따로 둔다.
            body = (sc.get(f"sub_{lang}") or sc[lang]) if lang == "en" else \
                (sc.get(f"sub_{lang}") or sc.get(lang, sc["en"]))
            body = srt_wrap(body)
            if sc.get("ko"):
                body = f"{sc['ko']} ({sc.get('roman', '')})\n{body}"
            lines.append(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{body}\n")
        (out / f"{eid}.{lang}.srt").write_text("\n".join(lines), encoding="utf-8")

    (out / f"{eid}.upload.txt").write_text(
        f"TITLE: {spec['title_en']}\n\nDESCRIPTION:\n{spec.get('description_en', '')}\n\n"
        f"HASHTAGS: {' '.join(spec.get('hashtags', []))}\n", encoding="utf-8")
    pk, z = max_volume_db(final)
    shutil.rmtree(work)
    print(f"{eid}: {t:.1f}s -> {final}  peak {pk} dBFS (0dB samples {z}), "
          f"{final.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    for d in sys.argv[1:] or sorted(str(p) for p in (ROOT / "episodes").iterdir() if p.is_dir()):
        build(d)
