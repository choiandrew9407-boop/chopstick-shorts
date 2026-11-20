# ep007~011 · 3초 즉답형 v5 재빌드 기록 (2026-11-21)

노션 45차 `Chopstick Club 쇼츠 — 3초 즉답형 v5 (ep007~011 훅 개편)` 규격으로 다섯 편을 다시 만들었다.
빌드는 GitHub Actions `Build shorts`에서 수행했고, 아래 산출물은 워크플로 아티팩트에서 그대로 꺼낸 것이다.

## 1. 빌드·산출물

| 편 | 길이 | 워크플로 런 | 아티팩트 |
|---|---|---|---|
| ep007 아이고 | 20.80초 | 44822621321 (success, 커밋 5a6ac79) | shorts-28 |
| ep008 편의점 | 20.90초 | 44822621321 (success) | shorts-28 |
| ep009 카공 | 21.00초 | 44823535587 (success, workflow_dispatch) | shorts-29 |
| ep010 찜질방 | 20.63초 | 44822621321 (success) | shorts-28 |
| ep011 배려석 | 21.30초 | 44822621321 (success) | shorts-28 |

- 저장 위치: `downloads/chopstick-shorts/` (평면 파일 + 편별 폴더). v4 산출물은 `downloads/chopstick-shorts/v4-archive-1120/`로 옮겨 둠.
- 각 편 구성: `.mp4`(1080x1920, 30fps) · `.en/.vi/.id/.es/.pt/.ar/.fil/.hi .srt`(8개) · `.upload.txt`
- ep009만 워크플로를 따로 돌린 이유: 마지막 커밋(자막 역슬래시 수정)이 ep009를 건드리지 않아 자동 선택에서 빠졌기 때문. `gh workflow run build.yml -f episodes=episodes/ep009`로 다시 빌드했다.

## 2. v5 구조 (전 편 동일)

| 구간 | 내용 |
|---|---|
| 0~3초 | 결과가 보이는 실사 클립 + 영어 단정문 1줄(한글 없음, 태그 없음) |
| 3~15초 | 이유 2장면(한국어 표현 카드는 3초부터) |
| 15~18초 | 작은 추가 사실 1개 |
| 18~end | `Yes or no?` 비교 질문 + 좋아요 1줄, 엔딩 클립 = 훅 클립(루프) |

편별 실제 경계는 `check_durs.py`로 확인했다(예: ep009 3.0 / 9.6 / 13.6 / 16.8 / 21.0초).

## 3. 대본 변경점

- 영어 훅을 질문이 아닌 **단정문**으로: ep009 `Koreans leave laptops here. Nobody steals.` / ep011 `Empty seat. Crowded train. Nobody sits.` / ep008 `Dinner for $4 — inside a convenience store.` / ep010 `Sleep here all night for about $10.` / ep007 `One Korean word for pain, shock, and tired.`
- 한국어 표현은 편당 1개 유지: 카공(kagong)·배려석(baeryeoseok)·편의점(pyeonuijeom)·찜질방(jjimjilbang)·아이고(aigo).
- ep011 15~18초: 좌석 표시등 시범 사례는 확인 근거가 없어 클로드 대체 문장 `Most people just keep it empty, all day.` 사용.
- ep010 가격은 지역별 차이가 있어 `about $10` 유지.

## 4. 클립 교체

- **ep009 신규 `vid2.mp4`**: Pexels `cozy-outdoor-cafe-vibes-with-latte-and-laptop-31933844` (Buse Çolak, 1080x1920, 6.48초, 무료 라이선스). 사람 없이 카페 테이블 위에 남겨진 노트북·라떼·책. 0~3초 훅과 엔딩 루프에 사용. 에스프레소 붓기(vid1)는 화면에서 제외.
- **ep008 훅**: 클로드 안의 vid1(전자레인지 문) 대신 vid0(김밥)으로 훅을 옮겼다. 0초 화면이 어두운 문이라 "0~0.5초 결과 노출" 규격에 맞지 않았기 때문. 전자레인지는 이유 장면으로 이동.
- ep007·ep010·ep011은 기존 클립 배치만 v5에 맞게 재배치(새 다운로드 없음).

## 5. 검수

- `*_v5_frames.jpg`: 로컬 빌드 프레임(초기 검수)
- `*_v5_ci_frames.jpg`: **워크플로 아티팩트 mp4**에서 뽑은 최종 프레임(0.2/1.5/2.9/4.5/9/13/16/18.5/끝초)
- 확인한 것: 훅 3초에 한글·태그 없음, 카드 텍스트 잘림 없음, CTA의 `Yes or no?`와 좋아요 1줄 노출, 엔딩이 훅 클립으로 이어짐, 해상도 1080x1920·길이 20.6~21.3초.

## 6. 남은 약점

- ep011 훅 화면이 파란 빈 좌석(일본 전철 창가)이라 "분홍 배려석"이 화면에 직접 나오지 않는다. 대본 문구와 화면의 'crowded'도 완전히 일치하진 않는다(빈 차량). 다음 개편 때 서울 지하철 분홍 좌석 클립으로 교체하는 게 좋다.
