# Chopstick Club shorts

1. Put `script.json` (+ optional `img1.png`…`img4.png`, 1080×1920) in `episodes/epNNN/`.
2. Push → GitHub Actions builds `out/epNNN/epNNN.mp4` + `en/vi/id.srt` + `upload.txt`.
3. Download the artifact from the Actions run → upload to YouTube Studio, add vi/id subtitle tracks.

No image → gradient background. Background music: put CC0 / YouTube Audio Library tracks in `assets/music/` and name them in `script.json` (missing file = voice only).
