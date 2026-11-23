# ep010·ep011 — Gemini TTS(Charon) 전환 빌드 기록

2026-11-23 17:05, `ep007~009`에 이어 남은 두 편(`ep010` 찜질방, `ep011` 배려석)에 Charon 목소리를 적용했다.

## 무엇이 바뀌었나
- 음성: `edge-tts`(한/영 분리) → **Gemini TTS** `gemini-3.8-flash-tts` / voice **Charon** (사전 생성본을 `episodes/<ep>/voice/v0..v4.wav`로 커밋, CI는 API를 부르지 않는다).
- 무료 등급 RPD 10을 정확히 사용(ep010 5 + ep011 5), 3 RPM 준수를 위해 요청 간 25초 대기.

## 결과
| 항목 | ep010 (찜질방) | ep011 (배려석) |
|---|---|---|
| 이전(edge-tts v5) | 20.63s | 21.30s |
| 이후(Charon) | **22.37s** | **22.90s** |
| voice_tempo | 1.15 (기본 1.10에서 23.03s였음) | 1.45 + CTA 비트 3.4→3.0s |
| 장면 경계 (en.srt) | 0 / 3.00 / 7.60 / 14.51 / 18.86 / 22.40 | 0 / 3.74 / 9.74 / 16.91 / 19.91 / 22.91 |
| 영상 규격 | 1080x1920 30fps, AAC 44.1k | 동일 |
| 음량 | mean −18.7 dB | mean −18.2 dB (ep009 Charon −17.9 dB) |

- ep011 대본이 원래 길어(음성 원본 합계 26.8초) `voice_tempo 1.45`까지 올려야 22.9초가 됐고, 마지막 CTA 비트를 3.4→3.0초로 줄여 맞췄다(음성 2.5초라 읽을 시간은 충분).
- 검수: `evidence/ep010-charon-sheet.png`, `evidence/ep011-charon-sheet.png` (0.5·4.5·10·16·20·22초 / 0.5·4.5·12·18·20.5·22.5초). 한글 카드(`찜질방`, `배려석`) 렌더 정상, 카드 글자 깨짐·CTA 겹침 없음.
- 첫 0.5초 움직이는 클립: 0.0→0.25→0.5초 프레임 차이 ep010 13.0%·8.9%, ep011 29.7%·29.7% 픽셀 변화 → 정지 이미지 아님.
- 자막: 8개 언어(en·vi·id·es·pt·ar·fil·hi) 각 5큐, stray backslash 없음.

## 재현
```bash
GEMINI_TTS_VOICE=Charon python3 work/tmp/gen_voice_eps.py ep010 ep011   # 10요청, 25초 간격
FFMPEG=<ffmpeg> python3 tools/build.py episodes/ep010 episodes/ep011
```
