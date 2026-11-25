1. **실측 수치 4개 — 전부 통과**

- **길이 21.843초** (0.0\~21.87초, 18\~22초 규격 안). 장면 경계 0 / 3.390 / 7.890 / 12.890 / 18.090 / 21.843
- **최대 음량 -2.3 dBFS** (true peak -2.3 dBFS · -2.0 dBFS 이하 조건 충족). CI 러너 재현값은 -2.4 dBFS
- **0 dB 샘플 수 0개** (s16 디코드 최대 25,092 = -2.32 dBFS, 960k 샘플 중 풀스케일 0개)
- **첫 0.05초 피크 -6.4 dBFS** (`atrim=0:0.05` + `astats`/`volumedetect`). 클릭·WAV 헤더 혼입 없음 → 재생성 없이 진행했습니다. Charon 원본 WAV 5개도 첫 0.05초 피크 -49.7\~-62.7 dBFS로 전부 정상(0.000초 샘플부터 0)

2. **스펙·음성**

- 1080×1920 · 30fps · AAC 192k/44.1kHz 스테레오 · **9.6MB** (20MB 이하)
- 음성 `gemini-3.8-flash-tts` / **Charon 단일 모델, 5줄 = 5회 호출** (모델 혼합 0회 · 25초 간격 · 오늘 RPD 5/10 사용)
- 오디오는 v6 규격 그대로: 장면 WAV `-1.5 dB` 헤드룸 → 2패스 `loudnorm(I -14 · TP -2.5)` + `alimiter(-2.5 dBFS)` + 44.1k
- 마지막 0.14초 무음 → 0.0초 음성 즉시 시작(루프 이음). 엔딩 클립이 훅과 같은 `vid1.mp4` 0초라 영상도 이어집니다

3. **v6 루프 대본 반영**

- 0.0 훅 `A whole night, about ten dollars, on the floor.` (카드 `One night. About $10. On the floor.`, 첫 0.5초 픽셀 변화 4.2%로 정지 아님)
- 3.4 `Koreans call it jjimjilbang.` + 카드 **찜질방 (jjimjilbang) · Korean spa**
- 7.9 `I paid at the door and got pajamas, a towel, hot rooms and cold rooms.`
- 12.9 `Then everyone started cracking boiled eggs. Some on their own foreheads.` (펀치 줌 · twist)
- 18.1 엔딩 카드 **`In Korea — you slept at a spa for $10?`** + `Like if you'd try it` (음성은 `Wait. You slept at a spa for ten dollars?` 그대로, TTS 재호출 없음)
- 상단 **`IN KOREA` 배지** 0초\~엔딩 고정, 카드 이모지 0개, 한국어 표현은 `찜질방` 1개만

4. **클립 검수 — 비한국 요소 0건 (클립 4개로 장면 분리)**

- `vid0` 탈의실 (Pexels 9145017 · Ron Lach): 사물함 번호판·안내문·스티커 없음. 전체 해상도 좌/우 크롭까지 확인
- `vid1` 반 자른 삶은 달걀 (Pexels 6289329 · Klaus Nielsen): 포장지·도장·컵 없음(상단 흰 배경 확대 확인) → 훅 + 엔딩 루프
- **`vid2` 신규** 열탕 돌·국자 (Pexels 5979944 · Yaroslav Shuraev): 문자 요소 0건, 사람 얼굴 없음 → 'Hot room. Cold room.'
- **`vid3` 신규** 삶은 달걀 한 솥 (Pexels 6288842 · Klaus Nielsen): 상표·라벨 판독 가능 문자 0건 → 'everyone cracked eggs'
- 폐기 후보: Pexels 6288804(날달걀을 라메킨에 깨는 컷) — 대본은 삶은 달걀이라 불일치
- 검수 시트 `evidence/ep010-v7-1125.png`(0.5초 44프레임), 클립 원본 확대 `evidence/ep010-v7-inspect/`, CI 재현 프레임 `evidence/ep010-v7-ci.png`

5. **파일·저장**

- `work/chopstick-shorts/upload/ep010.mp4` = `downloads/chopstick-shorts/ep010/ep010.mp4` = `out/ep010/ep010.mp4` (md5 `3849f4fe…` 동일)
- 자막 8개 언어 `ep010.en/vi/id/es/pt/ar/fil/hi.srt` 각 5큐 재생성, `ep010-metadata-8langs.md` 9개 언어(ja 포함) 갱신 — 영어 제목 첫 단어 `Why`, ja 제목 `なぜ韓国人は約10ドルでスパに一晩泊まるのか`
- GitHub push `4a2fc99` + evidence `a6de67e`, Actions run `45581272827` 성공(러너 `ep010: 21.8s`, peak -2.4 dBFS, 0 dB 샘플 0개, 9.6MB)
- 이전 v5 음성·영상은 `episodes/ep010/voice/_prev-v5-1123/`·`downloads/chopstick-shorts/_prev-v5-1123/ep010/`에 백업

6. **결정 필요 1건**

- 이 편만 **BGM(`calm03.mp3`)을 뺐습니다**: v6 루프 규격(ep008·009)은 BGM 없이 음성만이고, BGM이 있으면 빌드가 마지막 1.5초를 페이드아웃해 루프 이음이 끊깁니다. BGM을 넣으려면 페이드 없이 루프되는 트랙으로 바꿔야 하니, 원하시면 말씀 주세요.

---

### 💬 클로드 · (답변을 여기에 적어 주세요)
