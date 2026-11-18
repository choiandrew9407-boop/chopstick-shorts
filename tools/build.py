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

Needs: ffmpeg (FFMPEG env var or on PATH), Pillow, Noto Sans CJK fonts, tools/scenes.py.
Optional: Piper TTS (PIPER_MODEL env).
Usage: python tools/build.py episodes/ep001 [episodes/ep002 ...]
"""
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenes import DEFAULT_CYCLE, Particles, draw_scene, glow_sprite  # noqa: E402

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = int(H * 0.15), int(H * 0.80)  # keep text out of Shorts UI zones
ROOT = Path(__file__).resolve().parent.parent

# --- v3 tempo ---
HOOK_SEC = 1.5            # 훅 구간: 태그 숨김
CARD_BOTTOM_MARGIN = 170  # 카드 최소 하단 여백
CARD_MIN_TOP = 940        # 카드 상단은 이 아래로 내려가지 않음
GRADE = ("eq=saturation=1.08:contrast=1.05:brightness=0.01,"
         "unsharp=5:5:0.5,noise=alls=4:allf=t")
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"
VOICE_DELAY = 0.1         # 자막이 음성보다 0.1 s 먼저
SLIDE_SEC = 0.15

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


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"command failed: {' '.join(str(c) for c in cmd[:4])} ...")
    return r


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
def prep_clip(src, dur, out):
    """스톡 클립을 1080x1920 세로로 잘라 dur초로 맞춤(짧으면 반복), 소리 제거, v3 그레이딩."""
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
          "crop=1080:1920,fps=30," + GRADE)
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
        lines = wrap(d, scene["text"], f, max_w)
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
    fk, fr, fe = font("bold", 120), font("regular", 54), font("bold", 64)
    ko = wrap(d, scene["ko"], fk, max_w)
    en = wrap(d, scene["en"], fe, max_w)
    block = len(ko) * 150 + 90 + len(en) * 84
    if scene.get("card") == "top":
        top = CARD_MIN_TOP
    else:
        # v3: 카드 상단 y >= 940 보장 + 하단 여백 170px 고정
        top = max(CARD_MIN_TOP, SAFE_BOTTOM - block - CARD_BOTTOM_MARGIN)
    d.rounded_rectangle((40, top - 50, W - 40, top + block + 90), 40, fill=(0, 0, 0, 160))
    y = top
    for ln in ko:
        d.text((W // 2, y + 75), ln, font=fk, fill=(255, 226, 120), anchor="mm"); y += 150
    d.text((W // 2, y + 40), scene.get("roman", ""), font=fr, fill=(220, 220, 220), anchor="mm"); y += 90
    for ln in en:
        d.text((W // 2, y + 42), ln, font=fe, fill="white", anchor="mm"); y += 84
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


def render_still_scene(bg, lights, text, dur, idx, seed, particles, out, twist=False,
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
        frame.alpha_composite(fade_in(text, sub_alpha(t) if fade else 1.0))
        rgb = frame.convert("RGB")
        if f < slide_n:
            rgb = slide_frame(rgb, prev_frame, (f + 1) / (slide_n + 1))
        last = rgb
        ff.stdin.write(rgb.tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed while encoding a scene")
    return last


def render_video_scene(mp4, text, dur, out, prev_frame=None, slide=False, fade=True):
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
        frame.alpha_composite(fade_in(text, sub_alpha(f / FPS) if fade else 1.0))
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


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


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
               "dur": HOOK_SEC, "img": spec.get("hook_img", ""), "video": spec.get("hook_video", ""),
               "bg": spec.get("hook_bg", "seoul_night")}]
    scenes += [dict(s, kind="phrase") for s in spec["scenes"]]
    if spec.get("cta"):
        scenes.append(dict(spec["cta"], kind="phrase"))

    clips, voices, t, cues = [], [], 0.0, []
    prev_frame = None
    for i, sc in enumerate(scenes):
        kind, src = scene_source(ep_dir, sc)
        text = text_layer(sc, sc["kind"], show_tag=(sc["kind"] != "hook"))
        v = tts(sc.get("voice", ""), work / f"v{i}.wav")
        dur = HOOK_SEC if sc["kind"] == "hook" else scene_dur(sc)
        delay = 0.0 if sc["kind"] == "hook" else VOICE_DELAY  # 훅 음성은 0.0s 시작
        dur = max(dur, (wav_seconds(v) + delay + 0.2) if v else 0)
        clip = work / f"c{i}.mp4"
        cut_name, _ = transition_for(i - 1) if i else (None, 0.0)
        slide = bool(cut_name)

        if kind == "video":
            prepped = prep_clip(src, dur, work / f"p{i}.mp4")
            prev_frame = render_video_scene(prepped, text, dur, clip, prev_frame, slide,
                                            fade=(sc["kind"] != "hook"))
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
            prev_frame = render_still_scene(bg, lights, text, dur, i, seed,
                                            "none" if indoor else particles, clip,
                                            twist=bool(sc.get("twist")),
                                            prev_frame=prev_frame, slide=slide,
                                            fade=(sc["kind"] != "hook"))
        clips.append(clip)
        voices.append((v, dur, delay))
        if sc["kind"] == "phrase":
            cues.append((t, t + dur, sc))
        else:
            cues.append((t, t + dur, {"en": sc["text"], "vi": spec.get("hook_vi", sc["text"]),
                                      "id": spec.get("hook_id", sc["text"])}))
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
        mix = (f"[2]volume=0.12,afade=t=out:st={t - 1.5:.2f}:d=1.5[m];"
               f"[1][m]amix=inputs=2:duration=first:normalize=0,{LOUDNORM},aresample=44100[a]")
        run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice),
             "-stream_loop", "-1", "-i", str(music), "-filter_complex", mix,
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-t", f"{t:.3f}", "-movflags", "+faststart", str(final)])
    else:
        run([FF, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice),
             "-map", "0:v", "-map", "1:a", "-af", f"{LOUDNORM},aresample=44100", "-c:v", "copy", "-c:a", "aac",
             "-b:a", "128k", "-ar", "44100", "-shortest", "-movflags", "+faststart", str(final)])

    for lang in ("en", "vi", "id"):
        lines = []
        for n, (a, b, sc) in enumerate(cues, 1):
            body = sc[lang] if lang == "en" else sc.get(lang, sc["en"])
            if sc.get("ko"):
                body = f"{sc['ko']} ({sc.get('roman', '')})\n{body}"
            lines.append(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{body}\n")
        (out / f"{eid}.{lang}.srt").write_text("\n".join(lines), encoding="utf-8")

    (out / f"{eid}.upload.txt").write_text(
        f"TITLE: {spec['title_en']}\n\nDESCRIPTION:\n{spec.get('description_en', '')}\n\n"
        f"HASHTAGS: {' '.join(spec.get('hashtags', []))}\n", encoding="utf-8")
    shutil.rmtree(work)
    print(f"{eid}: {t:.1f}s -> {final}")


if __name__ == "__main__":
    for d in sys.argv[1:] or sorted(str(p) for p in (ROOT / "episodes").iterdir() if p.is_dir()):
        build(d)
