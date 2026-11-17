#!/usr/bin/env python3
"""Chopstick Club shorts builder.

Reads episodes/<id>/script.json and writes out/<id>/<id>.mp4 plus en/vi/id .srt files.
Needs: ffmpeg, Pillow, Noto Sans CJK fonts, tools/scenes.py. Optional: Piper TTS (PIPER_MODEL env).
Usage: python tools/build.py episodes/ep001 [episodes/ep002 ...]
"""
import json, os, shutil, subprocess, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenes import DEFAULT_CYCLE, Particles, draw_scene, glow_sprite  # noqa: E402
import math  # noqa: E402

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = int(H * 0.15), int(H * 0.80)  # keep text out of Shorts UI zones
ROOT = Path(__file__).resolve().parent.parent

FONT_DIRS = [ROOT / "assets/fonts", Path("/usr/share/fonts/opentype/noto"),
             Path("/usr/share/fonts/opentype/noto-cjk"), Path("/usr/share/fonts/noto-cjk")]


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


def background(scene, ep_dir, idx, seed):
    """Scene image (if Pickle added one) cover-fitted with room for a slow pan,
    otherwise an illustrated Korean scene. Returns (image, lights)."""
    bw, bh = int(W * 1.055), int(H * 1.055)
    img_path = ep_dir / scene.get("img", "")
    if scene.get("img") and img_path.exists():
        im = Image.open(img_path).convert("RGB")
        s = max(bw / im.width, bh / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        l, t = (im.width - bw) // 2, (im.height - bh) // 2
        return im.crop((l, t, l + bw, t + bh)), []
    name = scene.get("bg") or DEFAULT_CYCLE[idx % len(DEFAULT_CYCLE)]
    return draw_scene(name, bw, bh, seed + idx)


def text_layer(scene, kind):
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
        return layer
    fk, fr, fe = font("bold", 120), font("regular", 54), font("bold", 64)
    ko = wrap(d, scene["ko"], fk, max_w)
    en = wrap(d, scene["en"], fe, max_w)
    block = len(ko) * 150 + 90 + len(en) * 84
    if scene.get("card") == "top":
        top = SAFE_TOP + 60
    else:
        top = max(SAFE_TOP + 40, SAFE_BOTTOM - block - 150)
    d.rounded_rectangle((40, top - 50, W - 40, top + block + 90), 40, fill=(0, 0, 0, 160))
    y = top
    for ln in ko:
        d.text((W // 2, y + 75), ln, font=fk, fill=(255, 226, 120), anchor="mm"); y += 150
    d.text((W // 2, y + 40), scene.get("roman", ""), font=fr, fill=(220, 220, 220), anchor="mm"); y += 90
    for ln in en:
        d.text((W // 2, y + 42), ln, font=fe, fill="white", anchor="mm"); y += 84
    # channel tag lives inside the card, so it never collides with signs/displays
    d.text((W - 80, top + block + 55), "Chopstick Club", font=font("bold", 34),
           fill=(255, 255, 255, 170), anchor="rm")
    return layer


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:]); raise SystemExit(f"command failed: {cmd[0]}")
    return r


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


def render_clip(bg, lights, text, dur, idx, seed, particles, out):
    """Animate one scene: slow pan, twinkling lights, falling snow/petals,
    and the text card sliding up. Frames are piped straight into ffmpeg."""
    n = int(round(dur * FPS))
    dx, dy = bg.width - W, bg.height - H
    sprites = [(x, y, glow_sprite(r, c)) for x, y, r, c in lights]
    parts = Particles(W, H, seed + idx, particles) if particles != "none" else None
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(out)], stdin=subprocess.PIPE)
    direction = 1 if idx % 2 == 0 else -1
    for f in range(n):
        t = f / FPS
        k = f / max(n - 1, 1)
        ease = k * k * (3 - 2 * k)
        x = int(dx * (ease if direction == 1 else 1 - ease))
        frame = bg.crop((x, dy // 2, x + W, dy // 2 + H)).convert("RGBA")
        fx = ImageDraw.Draw(frame, "RGBA")
        for j, (lx, ly, sp) in enumerate(sprites):
            a = 0.55 + 0.45 * math.sin(t * 2.4 + j * 1.7)
            s2 = sp.copy()
            s2.putalpha(s2.getchannel("A").point(lambda v, a=a: int(v * a)))
            px, py = int(lx - x - sp.width / 2), int(ly - dy // 2 - sp.height / 2)
            if px >= 0 and py >= 0:
                frame.alpha_composite(s2, (px, py))
            else:  # alpha_composite rejects negative offsets; paste clips at the edge
                frame.paste(s2, (px, py), s2)
        if parts:
            parts.draw(fx, t)
        # text card: fade + slide up over the first 0.35 s
        p = min(1.0, t / 0.35)
        if p < 1:
            tl = text.copy()
            tl.putalpha(tl.getchannel("A").point(lambda v, p=p: int(v * p)))
            frame.alpha_composite(tl, (0, int(40 * (1 - p))))
        else:
            frame.alpha_composite(text)
        ff.stdin.write(frame.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed while encoding a scene")


def build(ep_dir):
    ep_dir = Path(ep_dir)
    spec = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    eid = spec["id"]
    out = ROOT / "out" / eid
    work = out / "work"
    shutil.rmtree(out, ignore_errors=True); work.mkdir(parents=True)
    seed = sum(map(ord, eid))

    scenes = [{"kind": "hook", "text": spec["hook_en"], "voice": spec.get("hook_voice", spec["hook_en"]),
               "dur": 2.5, "img": spec.get("hook_img", ""), "bg": spec.get("hook_bg", "seoul_night")}]
    scenes += [dict(s, kind="phrase") for s in spec["scenes"]]
    if spec.get("cta"):
        scenes.append(dict(spec["cta"], kind="phrase"))

    clips, voices, t, cues = [], [], 0.0, []
    for i, sc in enumerate(scenes):
        bg, lights = background(sc, ep_dir, i, seed)
        text = text_layer(sc, sc["kind"])
        v = tts(sc.get("voice", ""), work / f"v{i}.wav")
        dur = max(sc.get("dur", 4.5), (wav_seconds(v) + 0.5) if v else 0)
        clip = work / f"c{i}.mp4"
        indoor = sc.get("bg") in ("bapsang", "elevator") and not (ep_dir / sc.get("img", "x")).is_file()
        render_clip(bg, lights, text, dur, i, seed, "none" if indoor else spec.get("particles", "snow"), clip)
        clips.append(clip)
        voices.append((v, dur))
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
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])

    # voice track: each scene's voice padded to the scene length
    parts = []
    for i, (v, dur) in enumerate(voices):
        p = work / f"a{i}.wav"
        src = ["-i", str(v)] if v else ["-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono"]
        run(["ffmpeg", "-y", *src, "-af", f"apad=whole_dur={dur:.3f}", "-t", f"{dur:.3f}",
             "-ar", "44100", "-ac", "2", str(p)])
        parts.append(p)
    alst = work / "audio.txt"
    alst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    voice = work / "voice.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alst), "-c", "copy", str(voice)])

    final = out / f"{eid}.mp4"
    music = ROOT / "assets/music" / spec.get("music", "")
    if spec.get("music") and music.exists():
        run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", f"[2]volume=0.12,afade=t=out:st={t - 1.5:.2f}:d=1.5[m];[1][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{t:.3f}",
             "-movflags", "+faststart", str(final)])
    else:
        run(["ffmpeg", "-y", "-i", str(silent), "-i", str(voice), "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)])

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
