"""Korean-themed illustrated backgrounds for Chopstick Club shorts (no AI, no cost).

Each scene function draws a flat-illustration background and returns
(image, lights) where lights = [(x, y, r, (R, G, B))] that glow/twinkle in the video.
Scenes: seoul_night, hanok, pojangmacha, bapsang, elevator
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 2  # supersampling factor for smooth edges


def _grad(w, h, top, bottom):
    g = Image.new("RGB", (1, 256))
    for y in range(256):
        k = y / 255
        g.putpixel((0, y), tuple(int(top[i] * (1 - k) + bottom[i] * k) for i in range(3)))
    return g.resize((w, h))


def _ridge(w, base, amp, rnd, step=40):
    pts, y = [], base
    for x in range(-step, w + step * 2, step):
        y = base + amp * math.sin(x / (w / 2.3) + rnd.random()) + rnd.uniform(-amp * .25, amp * .25)
        pts.append((x, y))
    return pts


def _font(size, bold=True):
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
              "/usr/share/fonts/opentype/noto-cjk/NotoSansCJK-Bold.ttc"):
        try:
            return ImageFont.truetype(p, size, index=1)
        except OSError:
            pass
    return ImageFont.load_default()


def _stars(d, w, h, rnd, n=140):
    for _ in range(n):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.choice([1, 1, 2, 3])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 240))


def _snowcap_city(d, w, ground, rnd, lights, color, win_on, scale, height_rng):
    x = -20 * scale
    while x < w:
        bw = rnd.randint(110, 220) * scale
        bh = rnd.randint(*height_rng) * scale
        top = ground - bh
        d.rectangle((x, top, x + bw, ground), fill=color)
        # apartment number painted on side, Korean-apartment style
        if rnd.random() < .3 and bw > 150 * scale:
            d.text((x + bw / 2, top + 40 * scale), str(rnd.randint(101, 115)), font=_font(int(34 * scale)),
                   fill=tuple(min(255, c + 45) for c in color), anchor="mm")
        cols, rows = int(bw // (34 * scale)), int((bh - 80 * scale) // (40 * scale))
        for c in range(cols):
            for r_ in range(rows):
                if rnd.random() < win_on:
                    wx, wy = x + 14 * scale + c * 34 * scale, top + 70 * scale + r_ * 40 * scale
                    col = rnd.choice([(255, 214, 120), (255, 236, 170), (190, 220, 255)])
                    d.rectangle((wx, wy, wx + 16 * scale, wy + 20 * scale), fill=col)
                    if rnd.random() < .04:
                        lights.append(((wx + 8 * scale) / SS, (wy + 10 * scale) / SS, 10, col))
        x += bw + rnd.randint(4, 20) * scale


def seoul_night(w, h, seed):
    W, H = w * SS, h * SS
    rnd = random.Random(seed)
    img = _grad(W, H, (10, 14, 40), (58, 52, 110))
    d = ImageDraw.Draw(img)
    _stars(d, W, H * .5, rnd)
    lights = []
    # moon
    d.ellipse((W * .72, H * .1, W * .72 + 180 * SS, H * .1 + 180 * SS), fill=(255, 244, 214))
    # Namsan ridge + N Seoul Tower
    ridge = _ridge(W, H * .52, 50 * SS, rnd)
    d.polygon(ridge + [(W + 100, H), (-100, H)], fill=(24, 30, 62))
    tx, ty = W * .32, H * .52 - 40 * SS
    d.rectangle((tx - 14 * SS, ty - 470 * SS, tx + 14 * SS, ty), fill=(225, 225, 240))
    d.rounded_rectangle((tx - 70 * SS, ty - 560 * SS, tx + 70 * SS, ty - 470 * SS), 30 * SS, fill=(235, 235, 250))
    d.rectangle((tx - 60 * SS, ty - 520 * SS, tx + 60 * SS, ty - 505 * SS), fill=(120, 170, 255))
    d.rectangle((tx - 6 * SS, ty - 760 * SS, tx + 6 * SS, ty - 560 * SS), fill=(210, 210, 230))
    lights.append((tx / SS, (ty - 760 * SS) / SS, 16, (255, 80, 80)))
    for k in range(5):
        lights.append(((tx - 50 * SS + k * 25 * SS) / SS, (ty - 512 * SS) / SS, 9, (140, 190, 255)))
    # apartment rows
    _snowcap_city(d, W, H * .74, rnd, lights, (34, 38, 78), .35, SS, (260, 520))
    _snowcap_city(d, W, H * .86, rnd, lights, (22, 24, 52), .45, SS * 1.2, (220, 480))
    # Han river with reflections
    d.rectangle((0, H * .86, W, H), fill=(16, 22, 56))
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(H * .87, H)
        ln = rnd.uniform(20, 90) * SS
        d.line((x, y, x + ln, y), fill=rnd.choice([(255, 210, 120), (120, 160, 255), (80, 90, 160)]), width=3 * SS)
    return img.resize((w, h), Image.LANCZOS), lights


def _roof(d, cx, y, half, depth, color, tile):
    pts_top, pts_bot = [], []
    for i in range(0, 101):
        t = (i - 50) / 50
        lift = (abs(t) ** 4) * depth * .55
        pts_bot.append((cx + t * half, y + depth - lift))
        pts_top.append((cx + t * half * .78, y - (1 - abs(t) ** 2) * depth * .25 + depth * .05))
    d.polygon(pts_top + pts_bot[::-1], fill=color)
    for i in range(1, 40):
        t = (i - 20) / 20
        x = cx + t * half * .9
        lift = (abs(t) ** 4) * depth * .55
        d.line((x * 1, y + depth * .1, x, y + depth - lift - 6), fill=tile, width=6)
    d.line(pts_bot, fill=(230, 230, 225), width=10)


def hanok(w, h, seed):
    W, H = w * SS, h * SS
    rnd = random.Random(seed)
    img = _grad(W, H, (246, 160, 112), (120, 92, 160))
    d = ImageDraw.Draw(img)
    lights = []
    d.ellipse((W * .15, H * .2, W * .15 + 260 * SS, H * .2 + 260 * SS), fill=(255, 220, 160))
    ridge = _ridge(W, H * .45, 60 * SS, rnd, 60)
    d.polygon(ridge + [(W + 100, H), (-100, H)], fill=(96, 82, 130))
    ridge2 = _ridge(W, H * .52, 40 * SS, rnd, 60)
    d.polygon(ridge2 + [(W + 100, H), (-100, H)], fill=(74, 66, 108))
    # back house (small) and main house
    for cx, base, half, sc in ((W * .78, H * .6, W * .28, .6), (W * .45, H * .66, W * .62, 1.0)):
        depth = 230 * SS * sc
        body_top, body_bot = base + depth * .9, base + depth * .9 + 520 * SS * sc
        d.rectangle((cx - half * .7, body_top, cx + half * .7, body_bot), fill=(240, 232, 214))
        n = 5
        for i in range(n + 1):
            x = cx - half * .7 + i * (half * 1.4 / n)
            d.rectangle((x - 14 * SS * sc, body_top, x + 14 * SS * sc, body_bot), fill=(110, 66, 40))
            if i < n:  # lattice doors (changhoji)
                x2 = x + half * 1.4 / n
                d.rectangle((x + 40 * SS * sc, body_top + 70 * SS * sc, x2 - 40 * SS * sc, body_bot - 40 * SS * sc),
                            fill=(255, 238, 196))
                for gx in range(1, 4):
                    gx_ = x + 40 * SS * sc + gx * (x2 - x - 80 * SS * sc) / 4
                    d.line((gx_, body_top + 70 * SS * sc, gx_, body_bot - 40 * SS * sc), fill=(150, 100, 70), width=4 * SS)
                for gy in range(1, 6):
                    gy_ = body_top + 70 * SS * sc + gy * (body_bot - body_top - 110 * SS * sc) / 6
                    d.line((x + 40 * SS * sc, gy_, x2 - 40 * SS * sc, gy_), fill=(150, 100, 70), width=4 * SS)
        d.rectangle((cx - half * .75, body_top - 20 * SS * sc, cx + half * .75, body_top + 10 * SS * sc), fill=(78, 120, 104))
        _roof(d, cx, base, half, depth, (62, 62, 72), (44, 44, 52))
        d.rectangle((cx - half * .8, body_bot, cx + half * .8, body_bot + 60 * SS * sc), fill=(170, 160, 150))
        if sc == 1.0:
            for lx in (cx - half * .45, cx + half * .45):
                ly = body_top + 40 * SS
                d.line((lx, body_top, lx, ly), fill=(60, 40, 30), width=4 * SS)
                d.ellipse((lx - 40 * SS, ly, lx + 40 * SS, ly + 100 * SS), fill=(230, 70, 50))
                lights.append((lx / SS, (ly + 50 * SS) / SS, 36, (255, 160, 90)))
    # stone wall foreground
    d.rectangle((0, H * .9, W, H), fill=(120, 108, 100))
    for i in range(30):
        x, y = rnd.uniform(0, W), rnd.uniform(H * .9, H)
        d.ellipse((x, y, x + 120 * SS, y + 60 * SS), outline=(96, 86, 80), width=4 * SS)
    return img.resize((w, h), Image.LANCZOS), lights


def pojangmacha(w, h, seed):
    W, H = w * SS, h * SS
    rnd = random.Random(seed)
    img = _grad(W, H, (12, 10, 30), (40, 26, 52))
    d = ImageDraw.Draw(img)
    lights = []
    # alley buildings with neon signs
    signs = ["포차", "치킨", "노래방", "분식", "호프", "편의점", "국밥", "24시"]
    x = 0
    while x < W:
        bw = rnd.randint(260, 420) * SS
        top = rnd.randint(150, 600) * SS
        d.rectangle((x, top, x + bw, H * .62), fill=rnd.choice([(36, 30, 58), (44, 36, 66), (30, 28, 50)]))
        for k in range(rnd.randint(1, 2)):
            word = rnd.choice(signs)
            col = rnd.choice([(255, 70, 120), (80, 230, 255), (255, 200, 60), (140, 255, 120)])
            sy = top + (120 + k * 260) * SS
            f = _font(int(76 * SS))
            tw = d.textlength(word, font=f)
            d.rounded_rectangle((x + bw / 2 - tw / 2 - 30 * SS, sy - 60 * SS, x + bw / 2 + tw / 2 + 30 * SS, sy + 60 * SS),
                                20 * SS, outline=col, width=6 * SS, fill=(20, 16, 34))
            d.text((x + bw / 2, sy), word, font=f, fill=col, anchor="mm")
            lights.append(((x + bw / 2) / SS, sy / SS, 70, col))
        x += bw + 10 * SS
    # orange tent
    d.polygon([(W * .02, H * .48), (W * .98, H * .48), (W * 1.05, H * .62), (-W * .05, H * .62)], fill=(232, 96, 44))
    d.rectangle((-10, H * .62, W + 10, H), fill=(250, 142, 66))
    for k in range(7):  # tent stripes
        xs = k * W / 6
        d.line((xs, H * .62, xs, H), fill=(236, 120, 52), width=10 * SS)
    # string lights
    for k in range(9):
        lx = W * (.06 + k * .11)
        ly = H * .5 + 30 * SS * math.sin(k * 1.3)
        d.ellipse((lx - 18 * SS, ly - 18 * SS, lx + 18 * SS, ly + 18 * SS), fill=(255, 230, 150))
        lights.append((lx / SS, ly / SS, 30, (255, 210, 120)))
    # table with soju
    d.rounded_rectangle((W * .08, H * .78, W * .92, H * .86), 30 * SS, fill=(200, 200, 205))
    d.rectangle((W * .08, H * .86, W * .92, H), fill=(170, 170, 178))
    for bx in (W * .3, W * .5, W * .66):
        d.rounded_rectangle((bx - 34 * SS, H * .66, bx + 34 * SS, H * .8), 18 * SS, fill=(40, 150, 90))
        d.rectangle((bx - 14 * SS, H * .625, bx + 14 * SS, H * .67), fill=(40, 150, 90))
        d.rectangle((bx - 30 * SS, H * .72, bx + 30 * SS, H * .76), fill=(230, 245, 235))
    for gx in (W * .2, W * .78):
        d.polygon([(gx - 34 * SS, H * .75), (gx + 34 * SS, H * .75), (gx + 26 * SS, H * .8), (gx - 26 * SS, H * .8)],
                  fill=(220, 235, 245))
    d.ellipse((W * .38, H * .8, W * .6, H * .84), fill=(255, 255, 255))
    d.ellipse((W * .41, H * .805, W * .57, H * .832), fill=(210, 80, 60))  # tteokbokki
    return img.resize((w, h), Image.LANCZOS), lights


def bapsang(w, h, seed):
    W, H = w * SS, h * SS
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), (150, 98, 60))
    d = ImageDraw.Draw(img)
    for _ in range(160):  # wood grain
        y = rnd.uniform(0, H)
        d.line((0, y, W, y + rnd.uniform(-30, 30)), fill=rnd.choice([(140, 90, 54), (162, 108, 66), (134, 86, 52)]),
               width=rnd.randint(2, 6) * SS)
    lights = []

    def bowl(cx, cy, r, rim, inside, dots=None):
        d.ellipse((cx - r * 1.06, cy - r * 1.06 + 14 * SS, cx + r * 1.06, cy + r * 1.06 + 14 * SS), fill=(110, 70, 44))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rim)
        d.ellipse((cx - r * .82, cy - r * .82, cx + r * .82, cy + r * .82), fill=inside)
        if dots:
            for _ in range(int(r / 2)):
                a, rr = rnd.uniform(0, 6.28), rnd.uniform(0, r * .75)
                x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
                s = rnd.uniform(4, 9) * SS
                d.ellipse((x - s, y - s * .6, x + s, y + s * .6), fill=rnd.choice(dots))

    bowl(W * .32, H * .45, 230 * SS, (250, 250, 248), (255, 255, 255), [(240, 240, 235), (255, 255, 255)])  # rice
    bowl(W * .7, H * .42, 250 * SS, (60, 50, 50), (214, 96, 54), [(240, 140, 90), (90, 160, 80), (250, 220, 200)])  # stew
    bowl(W * .25, H * .7, 150 * SS, (240, 240, 236), (196, 46, 36), [(220, 70, 50), (250, 230, 200)])  # kimchi
    bowl(W * .55, H * .72, 140 * SS, (240, 240, 236), (240, 200, 60), [(250, 230, 120)])  # egg roll-ish
    bowl(W * .8, H * .74, 130 * SS, (240, 240, 236), (110, 160, 70), [(80, 140, 60), (140, 190, 90)])  # namul
    # spoon & chopsticks (metal, Korean style)
    d.rounded_rectangle((W * .05, H * .2, W * .07, H * .58), 10 * SS, fill=(200, 200, 210))
    d.ellipse((W * .03, H * .14, W * .09, H * .23), fill=(210, 210, 220))
    d.line((W * .1, H * .14, W * .12, H * .6), fill=(190, 190, 200), width=12 * SS)
    d.line((W * .125, H * .14, W * .14, H * .6), fill=(190, 190, 200), width=12 * SS)
    for k in range(5):  # steam points
        lights.append((W * .7 / SS + (k - 2) * 40, H * .36 / SS, 26, (255, 240, 220)))
    return img.resize((w, h), Image.LANCZOS), lights


def elevator(w, h, seed):
    W, H = w * SS, h * SS
    img = _grad(W, H, (196, 200, 210), (150, 156, 170))
    d = ImageDraw.Draw(img)
    for k in range(12):  # brushed steel
        x = k * W / 12
        d.line((x, 0, x, H), fill=(180, 184, 196), width=3 * SS)
    d.rounded_rectangle((W * .22, H * .08, W * .78, H * .50), 40 * SS, fill=(70, 74, 84))
    d.rounded_rectangle((W * .3, H * .10, W * .7, H * .16), 20 * SS, fill=(20, 20, 26))
    d.text((W * .5, H * .13), "▲ 15", font=_font(int(80 * SS)), fill=(255, 90, 60), anchor="mm")
    lights = []
    labels = [("1", "2"), ("3", "4"), ("5", "6"), ("열림", "닫힘")]
    for r, (a, b) in enumerate(labels):
        for c, t in enumerate((a, b)):
            cx, cy = W * (.40 + c * .20), H * (.215 + r * .07)
            hot = t == "닫힘"
            rr = 58 * SS
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                      fill=(255, 190, 70) if hot else (210, 212, 220), outline=(40, 40, 46), width=5 * SS)
            d.text((cx, cy), t, font=_font(int((42 if len(t) > 1 else 56) * SS)), fill=(30, 30, 36), anchor="mm")
            if hot:
                lights.append((cx / SS, cy / SS, 80, (255, 200, 90)))
    return img.resize((w, h), Image.LANCZOS), lights


SCENES = {"seoul_night": seoul_night, "hanok": hanok, "pojangmacha": pojangmacha,
          "bapsang": bapsang, "elevator": elevator}
DEFAULT_CYCLE = ["seoul_night", "bapsang", "hanok", "pojangmacha", "seoul_night"]


def draw_scene(name, w, h, seed):
    """이름 → 배경 이미지. SCENES에 없으면 확장 모듈(subway_scenes)에서 찾는다.

    subway_scenes가 scenes의 SS·_font를 쓰므로 순환 임포트를 피하려고 여기서 지연 임포트한다.
    """
    if name in SCENES:
        return SCENES[name](w, h, seed)
    try:
        import subway_scenes
        fn = subway_scenes.SCENES.get(name)
    except Exception:
        fn = None
    if fn:
        return fn(w, h, seed)
    return seoul_night(w, h, seed)


class Particles:
    """Gentle snow (winter) or petals, drawn per frame."""

    def __init__(self, w, h, seed, kind="snow", n=70):
        rnd = random.Random(seed)
        self.w, self.h, self.kind = w, h, kind
        self.p = [(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(3, 9), rnd.uniform(40, 120), rnd.uniform(0, 6.28))
                  for _ in range(n)]

    def draw(self, d, t):
        for x0, y0, r, speed, ph in self.p:
            y = (y0 + speed * t) % (self.h + 40) - 20
            x = x0 + 30 * math.sin(t * .8 + ph)
            if self.kind == "petal":
                d.ellipse((x - r * 1.4, y - r * .8, x + r * 1.4, y + r * .8), fill=(255, 190, 210, 210))
            else:
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 170))


def glow_sprite(r, color):
    size = int(r * 4)
    s = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse((size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r), fill=color + (255,))
    return s.filter(ImageFilter.GaussianBlur(r * .6))
