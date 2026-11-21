# ep009 — Gemini TTS(Charon) 전환 빌드 기록

2026-11-21, 은석님 지시("쇼츠 목소리를 Google AI Studio 잘생긴 남자 목소리로")에 따른 첫 재빌드.

## 무엇이 바뀌었나
- 음성 엔진: `edge-tts`(ko-KR-InJoonNeural + en-US-AndrewMultilingualNeural 분리 합성) → **Gemini TTS**
  (`gemini-3.8-flash-tts`, voice **Charon**, 무료 등급).
- 한국어 단어(`카공`)를 한 목소리로 자연스럽게 읽으므로 한/영 파트 분리 합성을 쓰지 않는다.
- Gemini 음성이 약 8~20% 느려 `atempo 1.10`(피치 유지)으로 당겨 22초 규격을 지킨다.

## 결과
| 항목 | 이전(edge-tts v5) | 이후(Charon) |
|---|---|---|
| 길이 | 22.30s | **22.33s** |
| 장면 경계 (en.srt) | 0 / 3.00 / 9.60 / 13.60 / 16.80 / 21.00 | 0 / 3.344 / 9.944 / 14.938 / 18.138 / 22.340 |
| 영상·자막 | 1080x1920 30fps, 8개 언어 | 동일 |

- 빌드: GitHub Actions run `44864677458` 성공(빌드 41초), 아티팩트 `shorts-31`.
- 검수: `evidence/ep009-gemini-charon-sheet.png` (0.5·3.9·7.6·12.6·17.6·21.6초 프레임).
- 음성 검수: 훅 구간 전사 "Koreans leave a laptop, nobody steals it." 정상, 카공 구간 음성 검수는
  `voice_samples/README.md` 참고(Charon "kah-gong" 9/10).

## 재현
```bash
GEMINI_TTS_VOICE=Charon python3 tools/gen_ep_voice.py   # episodes/ep009/voice/v0..v4.wav
python3 tools/build.py episodes/ep009
```
