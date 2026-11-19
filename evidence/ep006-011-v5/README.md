# ep006~011 v5 검수 프레임 — 2026-11-19

ep005와 같은 규격(첫 3.0초 영어 훅만 → 한글 카드는 2번째 장면부터, 마지막 CTA에 좋아요 한 줄, 힌디어 자막)으로
ep006~011 6편을 다시 빌드한 결과입니다.

- 커밋: `fc656cd` (ep006-ep011: 3.0s English-only hook, Hindi (hi) subtitles, one-line like CTA, 8-language metadata)
- GitHub Actions: `Build shorts` 런 **#22** (`44461921430`) — success (6m38s)
- 빌드 산출물: `out/ep006~011/` · `downloads/chopstick-shorts/ep006~011.mp4` + 8개 언어 `.srt`

## 프레임

| 파일 | 시점 | 확인한 것 |
| --- | --- | --- |
| `ep0NN-hook-0.5.png` | 0.5s | 첫 3초 — 영어 질문 훅만, 한글·채널 태그 없음 |
| `ep0NN-scene2start-3.2.png` | 3.2s | 2번째 장면 진입과 함께 한글 카드 등장 |
| `ep0NN-scene2-4.0.png` | 4.0s | 한글 카드 + 로마자 + 영어, 겹침·깨짐 없음 |
| `ep0NN-cta-*.png` | 끝나기 2.2초 전 | CTA 질문 + 카드 하단 좋아요 한 줄 |
| `ep011-scene3-twist-11.0.png` / `-13.2.png` | 11.0s / 13.2s | 반전 장면 — 교체 클립(역광 실루엣), 얼굴·간판 노출 없음 |

ep008의 교체 클립(김밥 포장 용기)은 훅(0.5s)과 CTA 프레임에서 확인할 수 있습니다.

## 길이·자막

| 편 | 길이 | 자막 |
| --- | --- | --- |
| ep006 | 22.23s | en·vi·id·es·pt·ar·fil·hi (8) |
| ep007 | 22.67s | 8 |
| ep008 | 24.27s | 8 |
| ep009 | 23.93s | 8 |
| ep010 | 22.70s | 8 |
| ep011 | 23.10s | 8 |
