# ep008·ep009 23초 이하 단축 + ep006~011 체크리스트 반영 (2026-11-19)

## 최종 재생 시간 (ffprobe 없음 → ffmpeg Duration 기준)

| 편 | 이전 | 최종 | 변경 |
| --- | --- | --- | --- |
| ep006 | 22.23s | 21.00s | CTA 양자택일 질문 교체(좋아요 문장을 음성에서 빼 질문만 읽음) |
| ep007 | 22.67s | 21.50s | 〃 |
| ep008 | 24.27s | **22.17s** | CTA 음성 5.45s→3.50s + 장면 5.6/4.6/5.3→5.4/4.4/5.1, CTA 4.3→4.2 |
| ep009 | 23.93s | **22.30s** | CTA 음성 5.54s→2.93s, CTA 4.4→4.2, 훅 클립 교체 |
| ep010 | 22.70s | 21.60s | CTA 양자택일 질문 교체(음성 단축) |
| ep011 | 23.10s | 21.90s | 〃 |

ep008·ep009 모두 23.0s 이하고 권장 범위(20~22.5s) 안. 자막(.srt 8개 언어)도 같은 커밋/빌드에서 재생성되어 마지막 큐가 영상 길이와 일치한다
(ep008 마지막 큐 00:00:17,958→00:00:22,158 / 영상 22.17s).

## 첫 0.5초 훅 = 움직이는 실사 클립 확인

영상 자체의 0.05s 프레임과 0.45s 프레임을 비교한 픽셀 차(540×960 그레이스케일 평균):

| 편 | 훅 클립 | 0.05→0.45s 차 | 판정 |
| --- | --- | --- | --- |
| ep006 | vid0 (식당 홀) | 20.93 | 움직임 충분 |
| ep007 | vid0 (고기 굽는 손) | 41.00 | 움직임 충분 |
| ep008 | vid0 (야간 상점가) | 24.97 | 움직임 충분 |
| ep009 | **vid1 (에스프레소 붓기)** | 25.79 | 교체 후 충분 |
| ep010 | vid0 (사우나 탈의실) | 7.84 | 카메라 이동 있음(정지 아님) |
| ep011 | vid1 (지하철 창문 실루엣) | 7.07 | 카메라 이동 있음(정지 아님) |

- ep009는 기존 훅이 카페 와이드 클립(0.1초당 프레임 차 2 안팎)으로 가장 느려 **훅을 vid1(에스프레소를 붓는 손)로 바꾸고**, vid0은 '아아 한 잔' 장면으로 옮겼다. CTA도 vid1로 되돌려 끝→처음 루프를 만든다.
- ep010은 클립 순서를 바꿀 대안이 없다(다른 클립은 삶은 달걀 접사). 첫 0.05s·0.45s 프레임에서 사물함·벤치 위치가 실제로 이동해 정지 화면·줌이 아님을 확인했고, 6편 중 가장 느린 편이라 클로드에게 한 번 더 볼 지점으로 남긴다.
- 정지 이미지·켄번스 줌으로 시작하는 편은 없다(전부 실사 스톡 클립, 훅 구간 페이드 없음).

## 마지막 CTA (나라를 특정하지 않는 양자택일 + 좋아요 1줄)

| 편 | 질문 | 좋아요 줄 |
| --- | --- | --- |
| ep006 | Would you shout this at your table? Yes or no? | Like if you'd shout this |
| ep007 | Do you say aigo too? Yes or no? | Like if you've said aigo |
| ep008 | Would you eat this for five dollars? Yes or no? | Like if you'd eat this |
| ep009 | Would you study here? Yes or no? | Like if you study in cafés |
| ep010 | Would you sleep here for ten dollars? Yes or no? | Like if you'd sleep here |
| ep011 | Would you take this seat? Yes or no? | Like if you'd stand instead |

8개 언어 자막·카드 번역도 같은 질문으로 맞췄고, 나라 이름은 넣지 않았다.

## 해시태그

ep006~011 전부 `#Korea #LearnKorean #KoreanCulture #AsianCulture` + 편별 태그 + `#shorts` 로 통일했다
(`script.json` → `.upload.txt` 자동 반영, `ep006~011-metadata-8langs.md` 8개 언어 블록 동일).

## 파일

- 영상·자막: `out/ep006~011/` → `downloads/chopstick-shorts/ep006~011.mp4` + `epNNN.{en,vi,id,es,pt,ar,fil,hi}.srt` + `.upload.txt`
- 검수 프레임: 이 폴더(`evidence/ep008-009-trim-1119/`) — `epNNN-hook0.05.jpg`, `epNNN-hook0.45.jpg`, `epNNN-cta.jpg`, `ep008-21.0.jpg`, `ep009-21.2.jpg`, 전체 시트 `ep008-009-trim-1119.jpg`
- 훅 클립 원본 프레임 비교: `evidence/hookcheck/` (`epNNN.jpg` = 0.0/0.25/0.5s 3연속)
