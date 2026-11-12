"""工坊封面：Codex 生图模型画的母版（workshop/assets/cover-master.*.png，提示词在 cover-prompt.*.txt），
导出 cover.jpg、cover.zh-CN.jpg（1254，JPEG 90）和模组缩略图 thumbnail.png（512）。封面是宣传图，不是游戏截图。

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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['derive', 'compose-zh'])
    a = ap.parse_args()
    compose_zh() if a.cmd == 'compose-zh' else derive()


if __name__ == '__main__':
    main()
