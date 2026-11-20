#!/usr/bin/env python3
"""Frame-check sheet for a built short: extract frames at given times and tile them
with a timestamp label, so hook / reason / bonus / CTA text can be inspected visually.

Usage: python3 frames.py <mp4> <out.jpg> [t1 t2 ...]
"""
import subprocess, sys, os, tempfile
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = os.environ.get("FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()


def grab(mp4, t, dst, w=300):
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t}", "-i", mp4, "-frames:v", "1",
                    "-vf", f"scale={w}:-1", dst], check=True)


def main(mp4, out, times):
    d = tempfile.mkdtemp()
    imgs = []
    for t in times:
        p = os.path.join(d, f"{t}.jpg")
        grab(mp4, t, p)
        imgs.append((t, Image.open(p)))
    w, h = imgs[0][1].size
    cols = min(5, len(imgs))
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, (h + 26) * rows), "white")
    dr = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception:
        f = ImageFont.load_default()
    for i, (t, im) in enumerate(imgs):
        x, y = (i % cols) * w, (i // cols) * (h + 26)
        sheet.paste(im, (x, y))
        dr.text((x + 6, y + h + 3), f"{t}s", fill="black", font=f)
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3:]] or [0.2, 1, 2.9, 5, 9, 13, 16, 19, 20.5])
