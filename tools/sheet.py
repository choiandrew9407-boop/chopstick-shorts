#!/usr/bin/env python3
"""MP4에서 대표 프레임을 뽑아 라벨 붙은 시트 PNG로 만든다(검수용).

사용: python tools/sheet.py out/ep008/ep008.mp4 evidence/ep008-fixed-1124.png 0.03 3.6 6.1 9.6 11.6 12.9 16.6 20.9
      (초를 생략하면 영상 길이를 8등분한 지점을 쓴다)
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FF = ("/usr/local/lib/python3.12/site-packages/imageio_ffmpeg/binaries/"
      "ffmpeg-linux-x86_64-v9.0.2")
COLS, TW, TH, BAR = 4, 540, 960, 74


def ffmpeg_bin():
    import os
    import shutil
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or FF


def duration(mp4):
    out = subprocess.run([ffmpeg_bin(), "-i", str(mp4)], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise SystemExit("duration not found")


def frame(mp4, t, out):
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-ss", f"{t:.3f}",
                    "-i", str(mp4), "-frames:v", "1", str(out)], check=True)
    return Image.open(out).convert("RGB")


def main():
    mp4, dest = Path(sys.argv[1]), Path(sys.argv[2])
    d = duration(mp4)
    times = [float(x) for x in sys.argv[3:]] or [d * (i + 0.5) / 8 for i in range(8)]
    tmp = dest.parent / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(ROOT / "assets/fonts/NotoSansCJKkr-Bold.otf"), 44)
    rows = (len(times) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TW, rows * (TH + BAR)), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    for i, t in enumerate(times):
        img = frame(mp4, t, tmp / f"f_{t:.2f}.png").resize((TW, TH), Image.LANCZOS)
        x, y = (i % COLS) * TW, (i // COLS) * (TH + BAR)
        sheet.paste(img, (x, y))
        sheet.paste(Image.new("RGB", (TW, BAR), (16, 16, 16)), (x, y + TH))
        dr.text((x + 18, y + TH + BAR // 2), f"{t:.1f}s", font=font, fill=(255, 214, 90), anchor="lm")
    sheet.save(dest)
    print(f"{dest} {sheet.size} frames={len(times)}")


if __name__ == "__main__":
    main()
