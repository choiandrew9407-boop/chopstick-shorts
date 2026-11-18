# Chopstick Club shorts

1. Put `script.json` (+ optional `img1.png`…`img4.png`, 1080×1920) in `episodes/epNNN/`.
2. Push → GitHub Actions builds `out/epNNN/epNNN.mp4` + `en/vi/id/es/pt/ar/fil.srt` + `upload.txt`.
3. Download the artifact from the Actions run → upload to YouTube Studio, add the 7 subtitle tracks.

No image → gradient background. Background music: put CC0 / YouTube Audio Library tracks in `assets/music/` and name them in `script.json` (missing file = voice only).

## Subtitle languages (7)

`en` (English) · `vi` (Vietnamese) · `id` (Indonesian) · `es` (Spanish) · `pt` (Brazilian Portuguese) · `ar` (Modern Standard Arabic) · `fil` (Filipino/Tagalog)

`tools/build.py` writes all seven tracks for any episode that carries the matching keys:

- `hook_en`, `hook_vi`, `hook_id`, `hook_es`, `hook_pt`, `hook_ar`, `hook_fil`
- per scene: `"en"`, `"vi"`, `"id"`, `"es"`, `"pt"`, `"ar"`, `"fil"` (falls back to `"en"` when a key is missing)
- same keys inside `"cta"`

Each `.srt` keeps the Korean line + romanization on the first line and the target-language line below it, so every track matches the burned-in Korean card.

`captions/epNNN/` holds the published 7-track subtitle files for episodes that are already live (ep001–ep011). They were generated from the existing English timing (`captions/epNNN/epNNN.en.srt`) so the timecodes are identical to what YouTube already has — no video rebuild needed to update or re-upload a track.
