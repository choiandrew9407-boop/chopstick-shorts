"""서울 지하철 차내 일러스트(ep011 배려석) — AI 이미지 아님, 코드로 그린 자체 그래픽.

ep011의 일본 열차 클립(Pexels 31260217)과 노란 차체 창문 클립(vid1)을 대체한다.
비한국 요소(외국어 안내문·노선도·번호판) 0건을 보장하려고 사진 대신 직접 그린다.
차내 표기는 모두 한글("임산부 배려석")만 쓴다.

마스터 레이아웃(1000×1780, 영상과 같은 9:16 비율)을 한 번 그리고,
장면마다 다른 크롭(넓게/좌석 클로즈업/안내판 클로즈업)을 떠서 서로 다른 앵글처럼 쓴다.

    subway_wide  — 좌석벽 전체(훅·엔딩 루프 클립)
    subway_pink  — 핑크 배려석 확대(첫 장면)
    subway_sign  — 안내판·엠블럼 확대('배려석' 이름 설명)
    subway_crowd — 좌석벽 앞을 지나가는 승객 실루엣('아무도 안 앉았다' 반전)
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scenes import SS

FONT_BOLD = Path(__file__).resolve().parent.parent / "assets/fonts/NotoSansCJKkr-Bold.otf"

# 서울교통공사 차내 색
WALL = (202, 206, 210)
WALL_D = (176, 181, 186)
CEIL = (228, 230, 228)
FLOOR = (158, 163, 167)
FLOOR_L = (188, 192, 195)
STEEL = (208, 213, 218)
STEEL_D = (146, 152, 158)
PINK = (222, 54, 128)
PINK_D = (182, 34, 100)
GREY_SEAT = (178, 182, 186)
GREY_SEAT_D = (150, 155, 160)
DARK = (34, 37, 46)
WIN = (26, 29, 40)
GLASS_FRAME = (120, 126, 132)

MW, MH = 1000, 1780          # 마스터 캔버스(9:16)


def _font(size):
    for p in (FONT_BOLD,
              Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
              Path("/usr/share/fonts/opentype/noto-cjk/NotoSansCJK-Bold.ttc")):
        try:
            return ImageFont.truetype(str(p), size, index=1 if p.suffix == ".ttc" else 0)
        except Exception:
            continue
    return ImageFont.load_default()


def _emblem(size):
    """임산부 엠블럼: 핑크 원 + 흰 임신부 실루엣."""
    s = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    u = size / 100.0
    d.ellipse((0, 0, size - 1, size - 1), fill=PINK + (255,))
    w_ = (255, 255, 255, 255)
    d.ellipse((43 * u, 16 * u, 59 * u, 32 * u), fill=w_)                       # 머리
    d.polygon([(x * u, y * u) for x, y in
               [(48, 33), (54, 34), (56, 47), (65, 55), (63, 63), (56, 58),
                (55, 72), (47, 72), (46, 55), (40, 46), (44, 38)]], fill=w_)   # 몸통 + 배
    d.line((50 * u, 71 * u, 47 * u, 87 * u), fill=w_, width=max(2, int(4.6 * u)))
    d.line((54 * u, 71 * u, 58 * u, 86 * u), fill=w_, width=max(2, int(4.6 * u)))
    d.line((46 * u, 41 * u, 39 * u, 53 * u), fill=w_, width=max(2, int(4.2 * u)))
    d.ellipse((55 * u, 50 * u, 63 * u, 57 * u), fill=w_)                       # 배 위 손
    return s


def _figure(d, cx, base_y, h, rnd, color=DARK, arms_up=False):
    """서 있는 승객 실루엣(얼굴·손 없음): 머리 + 어깨 경사 + 허리 + 다리.

    인포그래픽 느낌의 평면 실루엣. 깊이별로 색을 조금씩 밝게 해서 원근을 준다.
    """
    head_r = h * .056
    neck_y = base_y - h + head_r * 2.15
    shoulder_y = neck_y + h * .022
    hip_y = base_y - h * .44
    sh_w = h * .105          # 어깨 반폭
    hip_w = h * .080         # 허리 반폭
    col = tuple(min(255, c + rnd.randint(0, 14)) for c in color)
    # 다리
    d.line((cx - hip_w * .45, hip_y, cx - hip_w * .55, base_y), fill=col, width=int(h * .055))
    d.line((cx + hip_w * .45, hip_y, cx + hip_w * .55, base_y), fill=col, width=int(h * .055))
    # 몸통: 어깨에서 허리로 좁아지는 사다리꼴
    d.polygon([(cx - sh_w, shoulder_y + h * .012), (cx - sh_w * .92, shoulder_y),
               (cx + sh_w * .92, shoulder_y), (cx + sh_w, shoulder_y + h * .012),
               (cx + hip_w, hip_y), (cx - hip_w, hip_y)], fill=col)
    # 목
    d.rectangle((cx - head_r * .38, neck_y - h * .012, cx + head_r * .38, shoulder_y + 1), fill=col)
    # 머리
    d.ellipse((cx - head_r, base_y - h, cx + head_r, base_y - h + head_r * 2), fill=col)
    # 팔: 몸통 옆으로 붙는 얇은 실루엣
    if arms_up:
        d.line((cx - sh_w * .88, shoulder_y + h * .02, cx - sh_w * 1.05, neck_y - h * .05), fill=col,
               width=int(h * .042))
        d.line((cx + sh_w * .88, shoulder_y + h * .02, cx + sh_w * 1.02, neck_y + h * .01), fill=col,
               width=int(h * .042))
    else:
        d.line((cx - sh_w * .96, shoulder_y + h * .02, cx - hip_w * 1.06, hip_y + h * .02), fill=col,
               width=int(h * .042))
        d.line((cx + sh_w * .96, shoulder_y + h * .02, cx + hip_w * 1.06, hip_y + h * .02), fill=col,
               width=int(h * .042))


def _bench(d, x0, x1, y_top, y_back, y_bot, pink_from, pink_to, seam):
    """좌석 벤치: 등받이 + 앉는 면. 핑크 배려석 구간은 점 패턴 원단."""
    d.rectangle((x0, y_top, x1, y_back), fill=GREY_SEAT)
    d.rectangle((x0, y_top, x1, y_top + (y_back - y_top) * .22), fill=(196, 200, 204))
    d.rectangle((x0, y_back, x1, y_bot), fill=(166, 170, 175))
    d.rectangle((pink_from, y_top, pink_to, y_back), fill=PINK)
    d.rectangle((pink_from, y_top, pink_to, y_top + (y_back - y_top) * .22), fill=(238, 100, 160))
    d.rectangle((pink_from, y_back, pink_to, y_bot), fill=(206, 44, 112))
    step = 14
    for x in range(int(pink_from + 8), int(pink_to - 4), step):
        for y in range(int(y_top + 12), int(y_back - 4), step):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(248, 178, 208))
    d.line((pink_from, y_back, pink_to, y_back), fill=(148, 24, 82), width=4)
    for i in range(1, seam):
        x = x0 + (x1 - x0) * i / seam
        d.line((x, y_top, x, y_back), fill=GREY_SEAT_D, width=3)
        d.line((x, y_back, x, y_bot), fill=(142, 147, 152), width=3)
    d.line((pink_from, y_top, pink_from, y_bot), fill=PINK_D, width=5)
    d.line((pink_to, y_top, pink_to, y_bot), fill=PINK_D, width=5)
    d.rectangle((x0, y_bot - 6, x1, y_bot), fill=(124, 128, 134))


def _master(seed):
    """벽·창·안내판·좌석·바닥을 그린 마스터(1000×1780 × SS)."""
    W, H = MW * SS, MH * SS
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), WALL)
    d = ImageDraw.Draw(img)
    lights = []

    def y(v):
        return v * SS

    # 천장 띠
    d.rectangle((0, 0, W, y(30)), CEIL)
    # 벽
    d.rectangle((0, y(30), W, y(660)), WALL)
    for t in (250, 430, 610):
        d.line((0, y(t), W, y(t)), fill=WALL_D, width=3 * SS)

    # 창문(어두운 터널 + 지나가는 등)
    d.rectangle((y(18), y(120), y(982), y(520)), WIN)
    for k in range(5):
        x = y(rnd.uniform(40, 960))
        d.line((x, y(120), x, y(520)), fill=(38, 42, 58), width=9 * SS)
    for k in range(3):
        x = y(rnd.uniform(80, 820))
        yy = y(rnd.uniform(200, 440))
        d.line((x, yy, x + y(rnd.uniform(60, 150)), yy), fill=(255, 228, 160), width=7 * SS)
        lights.append((x, yy, 34, (255, 220, 150)))
    d.polygon([(y(60), y(120)), (y(300), y(120)), (y(150), y(520)), (y(30), y(520))],
              fill=(44, 50, 70))
    d.line((y(18), y(120), y(982), y(120)), fill=GLASS_FRAME, width=6 * SS)
    d.line((y(18), y(520), y(982), y(520)), fill=GLASS_FRAME, width=9 * SS)

    # 손잡이대 + 링
    d.line((0, y(62), W, y(62)), fill=STEEL, width=10 * SS)
    for x in (180, 400, 620, 840):
        cx = y(x)
        d.line((cx, y(62), cx, y(96)), fill=STEEL_D, width=int(11 * SS))
        d.ellipse((cx - 26 * SS, y(96), cx + 26 * SS, y(140)), outline=(240, 242, 242), width=11 * SS)
        d.ellipse((cx - 26 * SS, y(96), cx + 26 * SS, y(140)), outline=STEEL_D, width=2 * SS)

    # 안내판(핑크, 한글만)
    sx0, sx1 = y(430), y(790)
    sy0, sy1 = y(548), y(640)
    d.rounded_rectangle((sx0, sy0, sx1, sy1), 12 * SS, fill=PINK)
    d.rounded_rectangle((sx0 + 6 * SS, sy0 + 6 * SS, sx1 - 6 * SS, sy1 - 6 * SS), 9 * SS,
                        outline=(255, 255, 255), width=4 * SS)
    em = _emblem(int((sy1 - sy0) * .62))
    img.paste(em, (int(sx0 + 14 * SS), int((sy0 + sy1) / 2 - em.height / 2)), em)
    d.text((sx0 + 14 * SS + em.width + 16 * SS, y(594)), "임산부 배려석",
           font=_font(int(34 * SS)), fill=(255, 255, 255), anchor="lm")

    # 좌석 벤치
    _bench(d, y(-20), y(1020), y(660), y(790), y(880), y(470), y(800), 8)
    # 좌석 위 엠블럼(실제 배려석 등받이 표시)
    em2 = _emblem(int(96 * SS))
    img.paste(em2, (int(y(660)), int(y(676))), em2)

    # 좌석 프레임
    d.rectangle((0, y(880), W, y(920)), fill=(118, 122, 128))
    for x in range(int(y(10)), int(y(1000)), int(y(46))):
        d.line((x, y(882), x, y(918)), fill=(96, 100, 106), width=3 * SS)

    # 바닥
    d.rectangle((0, y(920), W, H), fill=FLOOR)
    d.rectangle((0, y(920), W, y(952)), fill=FLOOR_L)
    for k in range(1, 5):  # 바닥 이음선
        yy = y(920 + 170 * k)
        d.line((0, yy, W, yy), fill=(146, 151, 155), width=3 * SS)
    # 바닥 핑크 표지
    d.polygon([(y(500), y(1000)), (y(880), y(1000)), (y(960), y(1230)), (y(540), y(1230))],
              fill=(230, 96, 156))
    d.text((y(737), y(1112)), "임산부 배려석", font=_font(int(30 * SS)), fill=(255, 255, 255),
           anchor="mm")

    # 세로 손잡이 봉
    for px in (y(96), y(908)):
        d.line((px, y(40), px, y(1000)), fill=STEEL, width=int(14 * SS))
        d.line((px + 3 * SS, y(40), px + 3 * SS, y(1000)), fill=(255, 255, 255), width=3 * SS)
        d.line((px - 4 * SS, y(40), px - 4 * SS, y(1000)), fill=STEEL_D, width=3 * SS)
    return img, lights


def _shot(w, h, seed, rect, figures=None):
    """마스터에서 rect(마스터 px, SS 배율)를 잘라 (w,h)로. figures는 잘린 결과 위에 그린다.

    rect = (x0, y0, x1, y1) — 1000×1780 좌표계(SS 곱하기 전).
    """
    img, lights = _master(seed)
    x0, y0, x1, y1 = [v * SS for v in rect]
    crop = img.crop((int(x0), int(y0), int(x1), int(y1)))
    out = crop.resize((w, h), Image.LANCZOS)
    if figures:
        d = ImageDraw.Draw(out)
        rnd = random.Random(seed + 11)
        figures(d, w, h, rnd)
    # 글로우 좌표를 잘린 화면 좌표로
    sx, sy = w / (x1 - x0), h / (y1 - y0)
    out_lights = [((lx - x0) * sx / SS, (ly - y0) * sy / SS, r, col) for lx, ly, r, col in lights
                  if x0 <= lx <= x1 and y0 <= ly <= y1]
    return out, out_lights


ASPECT = 1780 / 1000.0


def _rect(cx, cy, frac_w):
    """중심 (cx,cy)와 폭 비율 frac_w로 9:16 크롭 사각형을 만든다."""
    fw = MW * frac_w
    fh = fw * ASPECT
    return (cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2)


def subway_wide(w, h, seed):
    """좌석벽 전체 뷰 — 훅·엔딩(루프) 클립. 빈 핑크 배려석 + 안내판."""
    return _shot(w, h, seed, (40, 60, 960, 60 + 920 * ASPECT), None)


def subway_pink(w, h, seed):
    """핑크 배려석 + 안내판 확대(빈 좌석)."""
    r = _rect(650, 880, 0.62)
    return _shot(w, h, seed, r, None)


def subway_sign(w, h, seed):
    """안내판·엠블럼 확대 — '배려석' 이름 설명 장면."""
    r = _rect(610, 706, 0.46)
    return _shot(w, h, seed, r, None)


def subway_aisle(w, h, seed):
    """차량 통로 원근 뷰 — 빈 핑크 좌석이 중간에 보이는 '아무도 안 앉았다' 반전 장면.

    사람은 그리지 않는다(얼굴·식별 요소 0건). 비어 있는 차내와 좌석만 보여 준다.
    """
    W, H = w * SS, h * SS
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), WALL)
    d = ImageDraw.Draw(img)
    lights = []
    vx, vy = W * .5, H * .40
    # 천장
    d.polygon([(0, 0), (W, 0), (vx + W * .14, vy - H * .07), (vx - W * .14, vy - H * .07)], CEIL)
    d.polygon([(W * .3, 0), (W * .38, 0), (vx + W * .03, vy - H * .07), (vx - W * .03, vy - H * .07)],
              (250, 251, 242))
    lights.append((W * .34 / SS, H * .1 / SS, 70, (255, 250, 215)))
    # 바닥
    d.polygon([(0, H), (W, H), (vx + W * .12, vy + H * .02), (vx - W * .12, vy + H * .02)], FLOOR)
    for k in range(1, 7):
        t = k / 7
        yy = vy + H * .02 + (H - vy - H * .02) * (t ** 1.7)
        half = W * .12 + (W * .5 - W * .12) * (t ** 1.7)
        d.line((vx - half, yy, vx + half, yy), fill=(146, 151, 155), width=max(2, int(6 * (1 - t))))
    # 벽 + 창
    for sgn in (-1, 1):
        xo = W * (.5 + sgn * .5)
        xi = vx + sgn * W * .13
        d.polygon([(xo, 0), (xo, H), (xi, vy + H * .06), (xi, vy - H * .07)], WALL)
        d.polygon([(xo, H * .13), (xo, H * .40), (xi, vy - H * .005), (xi, vy - H * .05)], WIN)
        for k in range(3):
            t = rnd.uniform(.1, .85)
            xa = xo + (xi - xo) * t
            yy = H * .13 + (vy - H * .05 - H * .13) * t + (H * .27) * t * .3
            d.line((xa, yy, xa + sgn * W * .02, yy), fill=(255, 228, 160), width=max(3, int(8 * (1 - t))))
            lights.append((xa / SS, yy / SS, 24, (255, 215, 150)))
        # 좌석(회색) + 창 아래 띠
        d.polygon([(xo, H * .55), (xo, H * .66), (xi, vy + H * .035), (xi, vy + H * .015)],
                  GREY_SEAT)
    # 왼쪽 벤치의 핑크 배려석(중간 거리)
    d.polygon([(0, H * .50), (0, H * .64), (W * .30, vy + H * .09), (W * .30, vy + H * .03)], PINK)
    d.polygon([(0, H * .44), (0, H * .50), (W * .30, vy + H * .03), (W * .30, vy + H * .005)],
              (238, 100, 160))
    # 안내판(왼쪽 핑크)
    d.polygon([(W * .02, H * .36), (W * .27, H * .36), (W * .29, H * .43), (W * .05, H * .43)],
              PINK)
    d.text((W * .155, H * .395), "임산부 배려석", font=_font(int(H * .022)), fill=(255, 255, 255),
           anchor="mm")
    # 바닥 핑크 표지(가까운 쪽)
    d.polygon([(W * .06, H * .80), (W * .46, H * .78), (W * .56, H * .99), (W * .02, H * .99)],
              (230, 96, 156))
    d.text((W * .27, H * .885), "임산부 배려석", font=_font(int(H * .026)), fill=(255, 255, 255),
           anchor="mm")
    # 손잡이대 + 링(원근)
    for sgn in (-1, 1):
        xa, xb = W * (.5 + sgn * .60), vx + sgn * W * .07
        ya, yb = vy + H * .20, vy + H * .012
        d.line((xa, ya, xb, yb), fill=STEEL, width=int(8 * SS))
        for k in range(1, 7):
            t = k / 6.6
            x = xa + (xb - xa) * t
            yy = ya + (yb - ya) * t
            r = 28 * SS * (1 - .80 * t)
            if r < 3:
                continue
            d.line((x, yy, x, yy + r * 1.6), fill=STEEL_D, width=max(2, int(r * .35)))
            d.ellipse((x - r, yy + r * 1.6, x + r, yy + r * 2.8), outline=(240, 242, 242),
                      width=max(2, int(r * .40)))
    # 세로 봉
    for sgn in (-1, 1):
        xa, xb = W * (.5 + sgn * .36), vx + sgn * W * .10
        d.line((xa, H, xb, vy + H * .05), fill=STEEL, width=int(11 * SS))
    # 끝 문
    d.rectangle((vx - W * .10, vy - H * .05, vx + W * .10, vy + H * .04), fill=(112, 116, 122))
    d.rectangle((vx - W * .10, vy - H * .05, vx + W * .10, vy - H * .04), fill=(90, 94, 100))
    return img.resize((w, h), Image.LANCZOS), lights


SCENES = {
    "subway_wide": subway_wide,
    "subway_pink": subway_pink,
    "subway_sign": subway_sign,
    "subway_aisle": subway_aisle,
}
