"""工坊描述顶部的覆盖表（2 倍 PNG，英文、中文各一张）。样式照人物模组 coverage-20261105/render.py。
在 Windows 上运行（用微软雅黑）：python -B render.py"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
S = 4
W = 720
PAD, ROW_H, HEAD_H, TOTAL_H, LEGEND_H, RADIUS = 18, 44, 34, 60, 30, 8
BG, ROW_LINE, TRACK = '#2a2e33', '#3a3f45', '#44494f'
GREEN, GREY, MUTED, WHITE = '#2ea043', '#8b949e', '#9aa4ae', '#ffffff'
BOLD = 'C:/Windows/Fonts/msyhbd.ttc'
REG = 'C:/Windows/Fonts/msyh.ttc'
VAN_R, CNT_R, BAR_X, BAR_W, PCT_R = 386, 518, 532, 78, W - PAD

TEXT = {
    'en': {'head': ('Category', 'Vanilla', 'With this mod', 'Coverage'),
           'country': ('Countries', None),
           'culture': ('Cultures', None),
           'dynasty': ('Dynasties', None),
           'language': ('Languages', None),
           'language_family': ('Language families', None),
           'holy_site': ('Holy sites', None),
           'culture_group': ('Culture groups (extends vanilla)', None),
           'religion': ('Religions (extends vanilla)', None),
           'religious_aspect': ('Religious aspects (extends vanilla)', None),
           'god': ('Gods (extends vanilla)', None),
           'total': ('All', None),
           'legend': ('Vanilla description only', 'Written or extended by this mod')},
    'zh-CN': {'head': ('类别', '原版', '本模组', '覆盖率'),
              'country': ('国家', None),
              'culture': ('文化', None),
              'dynasty': ('王朝', None),
              'language': ('语言', None),
              'language_family': ('语族', None),
              'holy_site': ('圣地', None),
              'culture_group': ('文化组（扩展了官方描述）', None),
              'religion': ('宗教（扩展了官方描述）', None),
              'religious_aspect': ('宗教信条（扩展了官方描述）', None),
              'god': ('神祇（扩展了官方描述）', None),
              'total': ('合计', None),
              'legend': ('仅原版描述', '本模组撰写或补充')},
}


def font(path, size):
    return ImageFont.truetype(path, round(size * S))


def text(draw, xy, s, f, fill, anchor='ls'):
    draw.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def bar(draw, x, y, w, h, vanilla, mod, total):
    """绿色：本模组撰写或补充的条数；紧接着的灰色：只有原版描述、本模组没有补充的条数。
    2026-11-13 起原版描述保留、我们的接在后面，所以原版有描述且我们补充了的算绿色。"""
    r = h / 2
    draw.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S, fill=TRACK)
    only = min(vanilla, total - mod)
    if only:
        ex = x + max(w * (mod + only) / total, h)
        draw.rounded_rectangle((x * S, y * S, ex * S, (y + h) * S), r * S, fill=GREY)
    gx = x + w * mod / total
    draw.rounded_rectangle((x * S, y * S, gx * S, (y + h) * S), r * S, fill=GREEN)
    if only:
        draw.rectangle(((gx - r) * S, y * S, gx * S, (y + h) * S), fill=GREEN)


def render(lang, data):
    t = TEXT[lang]
    rows = data['rows']
    H = PAD + HEAD_H + ROW_H * (len(rows) - 1) + TOTAL_H + LEGEND_H + PAD // 2
    img = Image.new('RGBA', (W * S, H * S))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W * S - 1, H * S - 1), RADIUS * S, fill=BG)
    f_head, f_name, f_sub = font(REG, 12), font(BOLD, 16), font(REG, 12)
    f_num, f_van, f_pct, f_pct_big = font(BOLD, 15), font(REG, 15), font(BOLD, 17), font(BOLD, 24)
    y = PAD
    h1, h2, h3, h4 = t['head']
    text(d, (PAD, y + 18), h1, f_head, WHITE)
    text(d, (VAN_R, y + 18), h2, f_head, WHITE, 'rs')
    text(d, (CNT_R, y + 18), h3, f_head, WHITE, 'rs')
    text(d, (PCT_R, y + 18), h4, f_head, WHITE, 'rs')
    y += HEAD_H
    for row in rows:
        total = row['key'] == 'total'
        rh = TOTAL_H if total else ROW_H
        d.line((PAD * S, y * S, (W - PAD) * S, y * S), fill=MUTED if total else ROW_LINE, width=S * (2 if total else 1))
        name, sub = t[row['key']]
        mid = y + rh / 2
        if sub:
            text(d, (PAD, mid - 3), name, f_name, WHITE)
            text(d, (PAD, mid + 15), sub, f_sub, MUTED)
        else:
            text(d, (PAD, mid + 6), name, font(BOLD, 18) if total else f_name, WHITE)
        text(d, (VAN_R, mid + 6), f"{row['vanilla']:,}", f_van, GREY, 'rs')
        text(d, (CNT_R, mid + 6), f"{row['mod']:,} / {row['total']:,}", f_num, WHITE, 'rs')
        bar(d, BAR_X, mid - (6 if total else 5), BAR_W, 12 if total else 10, row['vanilla'], row['mod'], row['total'])
        pct = 100 * row['mod'] / row['total']
        s = '100%' if row['mod'] == row['total'] else f'{int(pct * 10) / 10:.1f}%'   # 向下取整，2,086/2,087 不显示成 100.0%
        text(d, (PCT_R, mid + 8), s, f_pct_big if total else f_pct, GREEN, 'rs')
        y += rh
    y += 18
    x = PAD
    f_leg = font(REG, 12)
    for label, color in zip(t['legend'], (GREY, GREEN)):
        d.rounded_rectangle((x * S, (y - 9) * S, (x + 10) * S, (y + 1) * S), 2 * S, fill=color)
        text(d, (x + 15, y), label, f_leg, MUTED)
        x += 15 + d.textlength(label, font=f_leg) / S + 18
    out = ROOT / f'coverage.{lang}.png'
    img.resize((W * 2, H * 2), Image.Resampling.LANCZOS).save(out, optimize=True)
    return out


if __name__ == '__main__':
    data = json.loads((ROOT / 'coverage.json').read_text(encoding='utf-8'))
    for lang in TEXT:
        p = render(lang, data)
        print(p.name, Image.open(p).size, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()[:16])
