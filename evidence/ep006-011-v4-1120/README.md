# ep006~011 스토리형 v4 재빌드 검수 — 2026-11-20

노션 `Chopstick Club 쇼츠 — 스토리형 대본 v4 (ep006~011)`(`41dbd7d1-3908-81da-a1b3-ffd988f730b7`)의 새 대본으로
**ep006~011 6편을 전부 스토리형 v4로 교체**해 로컬 빌드한 결과입니다. ep001~005는 손대지 않았습니다.

## 규격 (적용 확인)

- 0~3.0초는 **영어 훅만** (한글 카드·채널 태그 없음), 한글 카드는 두 번째 장면부터.
- 한 편에 **큰 질문 1개 → 이유 → 방법 → 결론 + `Yes or no?`** 한 줄기. 핵심 한국어 표현은 **편당 1개**만 카드·음성에 들어감.
- `voice_parts`: 한국어 표현만 `ko-KR-InJoonNeural`, 나머지는 `en-US-AndrewMultilingualNeural`. 카드·자막 문구와 내레이션 자막을 분리(`sub_<lang>`).
- 좋아요 1줄은 **카드에만** (음성 없음), 자막에도 넣지 않음.
- 자막 8개 언어(en·vi·id·es·pt·ar·fil·hi), **한 줄 42자 이내**로 줄바꿈.
- 클립은 편당 2장면, 나머지 설명 장면은 기존 자체 배경(bapsang·seoul_night). AI 이미지 0장.

## 편별 구성과 실측 길이

| 편 | 훅 | 이유 | 핵심 표현 장면 | 결론·CTA | 길이 |
| --- | --- | --- | --- | --- | --- |
| ep006 | vid1 벨 3.0s | bg bapsang 6.2s | vid0 상차림 6.0s · **저기요** | vid1 벨 5.8s (훅과 같은 클립 → 루프) | **21.00s** |
| ep007 | vid0 맨발 3.0s | vid0 이어서 5.35s | bg bapsang 6.5s · **아이고** | vid1 허리 6.45s | **21.27s** |
| ep008 | vid0 김밥 3.0s | bg seoul_night 6.58s · **편의점** | vid0 이어서 5.75s | vid1 전자레인지 5.97s | **21.27s** |
| ep009 | vid1 에스프레소 3.0s | bg seoul_night 6.32s | vid0 카공 6.36s · **카공** | vid0 5.2s 지점부터 5.63s | **21.33s** |
| ep010 | vid1 삶은 달걀 3.0s | bg seoul_night 7.27s · **찜질방** | vid1 달걀 4.61s | vid0 탈의실 6.42s | **21.30s** |
| ep011 | vid0 창가 좌석 3.0s | vid0 이어서 5.3s · **배려석** | vid1 실루엣 6.5s | vid1 실루엣(6.5s 지점부터) 6.2s | **21.00s** |

길이는 mp4 `mvhd`(타임스케일·듀레이션)와 ffmpeg 컨테이너 Duration 양쪽으로 실측했고 값이 일치합니다.
`durations.json` 참고. 모든 편이 20~22초 안에 들어옵니다.

## 프레임

| 파일 | 시점 | 확인한 것 |
| --- | --- | --- |
| `ep0NN-hook-0.05.png` / `-hook-0.5.png` | 0.05s / 0.5s | 첫 0.5초부터 움직이는 실사 클립 + 영어 질문만, 한글·태그 없음 |
| `ep0NN-scene1-card.png` | 첫 설명 장면 +0.7s | 영어 카드(한국어 없는 장면) 또는 한국어 카드, 배경 위 가독성 |
| `ep0NN-ko-card-sN.png` | 한국어 장면 +1.3s | 한국어 카드 + 로마자 + 영어, 겹침·깨짐 없음 |
| `ep0NN-cta-*.png` / `-end-*.png` | 끝 1.8s / 0.15s 전 | 결론 질문 + `Yes or no?` + 좋아요 한 줄, 마지막 프레임까지 카드 유지 |
| `ep0NN-sheet.png` | 위 6장 | 2×3 검수 시트 |

## 빌드 환경 메모

- 이 작업 환경에는 시스템 ffmpeg이 없어 `imageio-ffmpeg`(정적 ffmpeg 9.0.2)로 빌드했습니다(`FFMPEG` 환경변수). CI는 기존대로 `apt ffmpeg`.
- 음성은 `edge-tts==7.3.1` 고정, `EDGE_EN_RATE=+5%` / `EDGE_KO_RATE=+3%` (기존 편과 동일).
- `tools/build.py` 변경 4가지(다른 편 영향 없음):
  1. 한국어 없는 장면의 **영어 전용 카드**(72px 굵게) — `text_layer`.
  2. 카드 문구와 내레이션 자막 분리(`sub_<lang>` 우선 사용).
  3. `.srt`를 한 줄 42자로 줄바꿈(`srt_wrap`).
  4. `video_ss` — 같은 클립을 앞 장면과 다른 지점에서 다시 쓸 때 시작 오프셋.

## 자막·메타데이터

- `out/ep0NN/` → `downloads/chopstick-shorts/`에 `ep0NN.mp4`, 8개 언어 `.srt`, `ep0NN.upload.txt` 최신화.
- 8개 언어 제목·설명: `epNNN-metadata-8langs.md` (레포 루트, 6개).
- 해시태그는 편별 공통 `#Korea #LearnKorean #KoreanCulture #AsianCulture` + 편별 태그 + `#shorts`.
