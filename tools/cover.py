"""工坊封面：Codex 生图模型画的母版（workshop/assets/cover-master.*.png，提示词在 cover-prompt.*.txt），
导出 cover.jpg、cover.zh-CN.jpg（1254，JPEG 90）和模组缩略图 thumbnail.png（512）。封面是宣传图，不是游戏截图。

uv run --with pillow python tools/cover.py compose   # 在 macOS 上跑（用系统自带的兰亭黑和 Impact）
uv run --with pillow python tools/cover.py derive
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'workshop' / 'assets'


def derive():
    files = {}
    for lang, jpg in (('en', 'cover.jpg'), ('zh-CN', 'cover.zh-CN.jpg')):
        m = Image.open(ASSETS / f'cover-master.{lang}.png').convert('RGB')
        side = min(m.size)
        m = m.crop(((m.width - side) // 2, (m.height - side) // 2, (m.width + side) // 2, (m.height + side) // 2))
        m.resize((1254, 1254), Image.LANCZOS).save(ASSETS / jpg, quality=90)
        files[jpg] = f'cover-master.{lang}.png'
        if lang == 'en':
            m.resize((512, 512), Image.LANCZOS).save(ASSETS / 'thumbnail.png', optimize=True)
            files['thumbnail.png'] = 'cover-master.en.png'
    for f in files:
        assert (ASSETS / f).stat().st_size < 1_000_000, f'{f} 超过工坊 1 MB 上限'
    sha = {f: hashlib.sha256((ASSETS / f).read_bytes()).hexdigest()
           for f in sorted(set(files) | set(files.values()) | {'map-reference.png'}) if (ASSETS / f).exists()}
    print(json.dumps(sha, indent=1))
    return sha


ZH_FONT = ('/System/Library/AssetsV2/com_apple_MobileAsset_Font8/f14049099a04e570b893c01d9a4cd71f87c9e8d8.asset/'
           'AssetData/Lantinghei.ttc')  # 兰亭黑-简 特黑（macOS 自带）
ZH_LINES = (('描述扩展', 0.94), ('国家·文化·王朝', 0.6))   # (文字, 占宽比例)


def compose_zh():
    """中文封面：生图模型写的粗体汉字笔画粘连（2026-11-12），改用真字体排标题。
    取英文母版标题以下的插画和语言标签，标题区涂白后排两行中文，存成 cover-master.zh-CN.png。"""
    from PIL import ImageDraw, ImageFont
    m = Image.open(ASSETS / 'cover-master.en.png').convert('RGB')
    m = m.point(lambda v: 255 if v >= 232 else v)   # 母版底色略灰，统一成纯白，免得涂白的标题区留下接缝
    w, h = m.size
    top = int(h * 0.468)                       # 英文标题底边以下才是插画（母版 1254 高时约 587）
    d = ImageDraw.Draw(m)
    d.rectangle((0, 0, w, top), fill='white')
    face = next(i for i in range(12) if ImageFont.truetype(ZH_FONT, 10, index=i).getname()[1] in ('Heavy', '特黑'))
    y = int(h * 0.025)
    for text, share in ZH_LINES:
        size = 10
        while ImageFont.truetype(ZH_FONT, size + 4, index=face).getlength(text) < w * share:
            size += 4
        f = ImageFont.truetype(ZH_FONT, size, index=face)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        d.text(((w - (x1 - x0)) / 2 - x0, y - y0), text, font=f, fill='black')
        y += (y1 - y0) + int(h * 0.04)
    if y > top:
        raise ValueError('中文标题压到插画了')
    m.save(ASSETS / 'cover-master.zh-CN.png')
    print(f'标题底边 {y}，插画顶 {top}')


# 2026-11-13 用户定：封面去掉圆圈插画，把模组覆盖的类目全部用彩色粗体字列出来（不写“更多”）。
# 加新类目时在 CATEGORIES 里加一项，重跑 compose 和 derive。
SOURCE = 'cover-source.en.png'          # Codex 原始母版：取英文标题和左下角的 English ✓、中文 ✓ 两个语言标签
EN_FONT = '/System/Library/Fonts/Supplemental/Impact.ttf'
CATEGORIES = (                          # (英文, 中文, 颜色)；名称照游戏本地化（game_concept_*）
    ('COUNTRIES', '国家', '#E03A2F'),
    ('DYNASTIES', '王朝', '#D18B00'),
    ('CULTURES', '文化', '#24944A'),
    ('CULTURE GROUPS', '文化组', '#6E9A12'),
    ('RELIGION GROUPS', '宗教组', '#008F80'),
    ('RELIGIONS', '宗教', '#8A3FC0'),
    ('RELIGIOUS SCHOOLS', '宗教学派', '#D53633'),
    ('RELIGIOUS ASPECTS', '宗教信条', '#C2347E'),
    ('GODS', '神祇', '#4A4FC4'),
    ('CHIVALRIC ORDERS', '勋贵骑士团', '#A438A5'),
    ('HOLY SITES', '圣地', '#E5631A'),
    ('LANGUAGES', '语言', '#2470D6'),
    ('LANGUAGE FAMILIES', '语族', '#0E9AA0'),
)
EN_ROWS = ((0, 1, 2), (3, 4, 5), (6, 7), (8, 9, 10), (11, 12))
ZH_ROWS = ((0, 1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12))
TITLE_BOTTOM = 587                      # 母版 1254 高时英文标题底边
MARK_BOXES = ((21, 900, 491, 1042), (24, 1074, 442, 1213))   # 母版里 English ✓、中文 ✓ 的范围


def compose():
    """生成 cover-master.en.png 和 cover-master.zh-CN.png：标题 + 类目彩字 + 语言标签，类目和标签在标题下方垂直居中。"""
    from PIL import ImageDraw, ImageFont
    src = Image.open(ASSETS / SOURCE).convert('RGB').point(lambda v: 255 if v >= 232 else v)
    w, h = src.size
    marks = [src.crop(b) for b in MARK_BOXES]
    zh_face = next(i for i in range(12) if ImageFont.truetype(ZH_FONT, 10, index=i).getname()[1] in ('Heavy', '特黑'))

    def fit(font_of, rows, labels, gap, max_w):
        size = 400
        while max(sum(font_of(size).getlength(labels[i]) for i in r) + gap * (len(r) - 1) for r in rows) > max_w:
            size -= 2
        return font_of(size)

    for lang in ('en', 'zh-CN'):
        m = Image.new('RGB', (w, h), 'white')
        d = ImageDraw.Draw(m)
        if lang == 'en':
            m.paste(src.crop((0, 0, w, TITLE_BOTTOM)), (0, 0))
            top = TITLE_BOTTOM
            labels = [c[0] for c in CATEGORIES]
            rows, gap = EN_ROWS, int(w * 0.035)
            font = fit(lambda s: ImageFont.truetype(EN_FONT, s), rows, labels, gap, w * 0.92)
            lh = int(font.size * 1.32)
        else:
            f = ImageFont.truetype(ZH_FONT, 10, index=zh_face)
            size = 10
            while ImageFont.truetype(ZH_FONT, size + 4, index=zh_face).getlength('描述扩展') < w * 0.94:
                size += 4
            f = ImageFont.truetype(ZH_FONT, size, index=zh_face)
            x0, y0, x1, y1 = d.textbbox((0, 0), '描述扩展', font=f)
            d.text(((w - (x1 - x0)) / 2 - x0, int(h * 0.025) - y0), '描述扩展', font=f, fill='black')
            top = int(h * 0.025) + (y1 - y0)
            labels = [c[1] for c in CATEGORIES]
            rows, gap = ZH_ROWS, int(w * 0.035)
            font = fit(lambda s: ImageFont.truetype(ZH_FONT, s, index=zh_face), rows, labels, gap, w * 0.93)
            lh = int(font.size * 1.75)
        # 语言标签：两个原图标签横排，按高度缩放
        mark_h = int(h * (0.11 if lang == 'zh-CN' else 0.09))
        scaled = [mk.resize((int(mk.width * mark_h / mk.height), mark_h), Image.LANCZOS) for mk in marks]
        marks_w = sum(s.width for s in scaled) + int(w * 0.08)
        spacing = int(h * (0.08 if lang == 'zh-CN' else 0.06))
        block = lh * len(rows) + spacing + mark_h
        y = top + (h - top - block) // 2
        for r in rows:
            ws = [font.getlength(labels[i]) for i in r]
            x = (w - (sum(ws) + gap * (len(r) - 1))) / 2
            for i, tw in zip(r, ws):
                bx0, by0, _, _ = d.textbbox((0, 0), labels[i], font=font)
                d.text((x - bx0, y - by0 + (lh - font.size) // 2), labels[i], font=font, fill=CATEGORIES[i][2])
                x += tw + gap
            y += lh
        y += spacing
        x = (w - marks_w) // 2
        for s in scaled:
            m.paste(s, (x, y))
            x += s.width + int(w * 0.08)
        m.save(ASSETS / f'cover-master.{lang}.png')
        print(lang, '类目字号', font.size, '底边', y + mark_h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['derive', 'compose', 'compose-zh'])
    a = ap.parse_args()
    {'derive': derive, 'compose': compose, 'compose-zh': compose_zh}[a.cmd]()


if __name__ == '__main__':
    main()
