# ep007·ep008 — Gemini TTS(Charon) 적용 빌드 기록

2026-11-21 17:05 KST, 무료 등급 RPD(하루 10회) 초기화 직후 실행. `ep009`(11-21 13:04 KST 생성,
22.33초, 22시 업로드 예정)에 이어 `ep007`·`ep008`까지 같은 Charon 목소리로 맞췄다.

## 무엇이 바뀌었나
- 음성: `episodes/ep007/voice/v0..v4.wav`, `episodes/ep008/voice/v0..v4.wav` — `gemini-3.8-flash-tts`
  voice **Charon**(Google AI Studio, 무료 등급, 3 RPM 준수 25초 간격, 총 10요청 = 오늘 한도 소진).
  `tools/gen_ep_voice.py`는 ep009 고정이라 워크스페이스 스크립트(`work/tmp/gen_voice_eps.py`)로
  같은 `tools/tts_gemini.py` 경로를 써서 생성했다.
- 대본: `script.json`에 `"voice_tempo": 1.15` 추가. Charon 음성이 기본 `atempo 1.10`에서
  ep007 23.7초·ep008 23.3초로 채널 규격(20~23초)을 넘어서, 두 편만 1.15배로 당겼다.
- `tools/build.py`: `_gemini_wav`/`speak`가 장면별 tempo를 받고 `build()`가 대본의 `voice_tempo`를
  넘기도록 확장(값이 없으면 기존 `GEMINI_TTS_TEMPO` 1.10 그대로 — 다른 편 영향 없음).

## 결과 (로컬 빌드, CI 동일 코드)
| 항목 | 이전(edge-tts v5) | 이후(Charon) |
|---|---|---|
| ep007 길이 | 21.15s | **22.93s** |
| ep008 길이 | 22.17s | **22.60s** |
| 장면 경계 ep007 | — | 0 / 3.762 / 9.251 / 15.585 / 18.928 / 22.928 |
| 장면 경계 ep008 | — | 0 / 3.555 / 9.994 / 15.594 / 18.794 / 22.591 |

- 영상: 1080×1920 30fps, 자막 8개 언어(en·vi·id·es·pt·ar·fil·hi) 각 5큐, `.upload.txt` 동일 규격.
- 검수 시트: `evidence/ep007-charon-sheet.png`, `evidence/ep008-charon-sheet.png`
  (0.5·3.9·7.6·12.6·17.6·21.6초). 카드 글자·한글(`아이고`, `편의점`) 깨짐 없음, CTA 겹침 없음.
- 음성 레벨: ep007 mean -17.9 dB / ep008 -18.3 dB (ep009 Charon 빌드와 같은 프로파일).

## 재현
```bash
GEMINI_TTS_VOICE=Charon python3 work/tmp/gen_voice_eps.py ep007 ep008   # voice/v0..v4.wav
python3 tools/build.py episodes/ep007 episodes/ep008                    # script.json voice_tempo 1.15
```
