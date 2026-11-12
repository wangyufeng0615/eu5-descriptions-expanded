"""把 data/entries.jsonl 构建成 EU5 模组。只用标准库（Python 3.10+），不上传。

python -B tools/build.py --check                      # 只检查数据和配置
python -B tools/build.py --output dist/<新目录>        # 构建模组文件夹、ZIP 和构建回执（目录必须是新的）
python -B tools/build.py --verify dist/<目录>          # 按当前源文件重算，核对已构建的文件夹、ZIP 和回执
python -B tools/build.py --install [--only-written]   # 开发用：构建到 dist/dev 并装进本机 EU5 模组目录
python -B tools/build.py --check --game-root "<EU5 安装目录>"   # 另外核对三个原版浮窗模板有没有随游戏更新变化

数据和改写过的浮窗模板由研究工程导出（研究工程 tools/sync_workshop.sh）。模组名、版本等在 project.json。

显示方式（2026-11-11、11-12 游戏内实测）：
- 语言、语系、圣地：原版浮窗已有描述位，只写 <ID>_desc；官方已有描述的放进 replace/ 覆盖。
- 国家、文化、王朝：mod_template 里的浮窗模板在底部加一块可滚动的介绍，按 ID 选文本用可定制本地化；
  王朝经宗族领袖取文本，没有在世领袖的王朝不显示。
游戏开着时会监视模组文件并自动重载，所以安装时先写到同盘临时目录、核对哈希，再整体改名替换。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
MOD_ROOT = Path(os.environ.get('USERPROFILE') or Path.home()) / 'Documents' / 'Paradox Interactive' / 'Europa Universalis V' / 'mod'
LICENSE_FILES = ('LICENSE', 'LICENSES/MIT.txt', 'LICENSES/CC-BY-SA-4.0.txt', 'CREDITS.md')
PLAYER_DOCS = {'README.md': 'workshop/player-readme.en.md', 'README.zh-CN.md': 'workshop/player-readme.zh-CN.md'}
GUI = 'in_game/gui/zz_lde_history_tooltips.gui'
CL_FILE = 'in_game/common/customizable_localization/lde_history_entries.txt'
SPECIAL = set('[]$#"\\')
VERSION_RE = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')
KINDS = ('country', 'culture', 'dynasty', 'holy_site', 'language', 'language_family')
DESC_KINDS = ('language', 'language_family', 'holy_site')
# 类别 -> (可定制本地化名, 对象类型, 本地化键前缀, 触发条件)
CUSTOM = {
    'country': ('lde_country_desc', 'country', 'lde_ctry_', lambda i: f'exists = c:{i} this = c:{i}'),
    'culture': ('lde_culture_desc', 'culture', 'lde_cult_', lambda i: f'this = culture:{i}'),
    'dynasty': ('lde_dynasty_desc', 'character', 'lde_dyn_', lambda i: f'dynasty = dynasty:{i}'),
}
# 游戏按 32 位哈希查本地化键，和原版撞车的键（error.log 报 Localization key hash collision）在这里换名。
KEY_RENAMES = {'lde_ctry_KIM': 'lde_ctry_KIM_b',   # 撞 kanishushteu（2026-11-12）
               'lde_ctry_VEN': 'lde_ctry_VEN_b'}   # 撞 MDR_ADJ
# 游戏会在中文里的半角 - 后强行折行；原版中文在汉字之间用不断行连字符 U+2011（2026-11-12 实测）。
ZH_HYPHEN = re.compile(r'(?<=[㐀-鿿》」”）·])-(?=[㐀-鿿《「“（])')


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def project_file(root, rel):
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError(f'缺少文件或路径在工程外：{rel}')
    return p


def load_config(root):
    cfg = json.loads((root / 'project.json').read_text(encoding='utf-8'))
    if cfg.get('game_id') != 'eu5' or cfg.get('steam_app_id') != 3450310:
        raise ValueError('project.json 的 game_id / steam_app_id 不是 EU5')
    if not re.fullmatch(r'[a-z0-9_]{3,40}', cfg.get('mod_id', '')):
        raise ValueError('mod_id 只能用小写字母、数字和下划线')
    if not VERSION_RE.fullmatch(cfg.get('version', '')):
        raise ValueError('version 必须是 x.y.z')
    for k in ('name', 'name_zh'):
        v = cfg.get(k)
        if not isinstance(v, str) or not 3 <= len(v) <= 128 or len(v.encode('utf-8')) > 128:
            raise ValueError(f'{k} 不合规（工坊标题上限 128 字节）')
    if not cfg.get('short_description', '').strip():
        raise ValueError('缺 short_description')
    pid = cfg.get('publishedfileid')
    if pid is not None and (type(pid) is not int or pid <= 0):
        raise ValueError('publishedfileid 要么是 null（还没建工坊条目），要么是正整数')
    if cfg.get('licenses') != {'tools': 'MIT', 'descriptions': 'CC-BY-SA-4.0'}:
        raise ValueError('licenses 和 LICENSE 文件不一致')
    return cfg


def load_rows(root, only_written=False):
    rows, seen = [], set()
    with open(root / 'data' / 'entries.jsonl', encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            r = json.loads(line)
            kind, eid = r.get('kind'), r.get('id')
            if kind not in KINDS or not isinstance(eid, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.\-]*', eid) \
                    or (kind, eid) in seen:
                raise ValueError(f'第 {n} 行：类别或 id 不合规或重复：{kind}/{eid!r}')
            seen.add((kind, eid))
            if r.get('verdict') not in ('written', 'stub'):
                raise ValueError(f'{kind}/{eid} 的 verdict 不能发布：{r.get("verdict")}')
            if only_written and r['verdict'] != 'written':
                continue
            if r.get('official') and kind not in DESC_KINDS:
                raise ValueError(f'{kind}/{eid} 标了 official，但这一类没有可替换的官方描述')
            for lang in ('en', 'zh'):
                if not plain_ok(r.get(lang)):
                    raise ValueError(f'{kind}/{eid} 的 {lang} 正文为空、有段内换行或含游戏指令字符，先回研究工程修')
            if paras(r['en']) != paras(r['zh']):
                raise ValueError(f'{kind}/{eid} 的中英文段数不同，先回研究工程修')
            src = r.get('sources')
            if not isinstance(src, list) or not src:
                raise ValueError(f'{kind}/{eid} 没有资料来源（署名要用）；研究工程重新导出')
            for u in src:
                p = urlsplit(u)
                if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
                    raise ValueError(f'{kind}/{eid} 的来源网址不合规：{u}')
            rows.append(r)
    return sorted(rows, key=lambda r: (r['kind'], r['id']))


def check_game(root, cfg, game_root):
    """游戏更新后，原版浮窗模板变了就要在研究工程重新生成 mod_template 里的模板。"""
    want = json.loads((root / 'data' / 'vanilla_gui.json').read_text(encoding='utf-8'))
    d = Path(game_root) / 'game' / cfg['vanilla_gui_dir']
    out = {'templates_unchanged': {f: (d / f).exists() and sha256((d / f).read_bytes()) == h for f, h in want.items()}}
    m = Path(game_root).parents[1] / 'appmanifest_3450310.acf'
    if m.exists():
        b = re.search(r'"buildid"\s+"(\d+)"', m.read_text(encoding='utf-8'))
        out.update(game_build=int(b.group(1)) if b else None, checked_build=cfg.get('game_build_checked'))
    return out


def paras(t):
    return t.strip().count('\n\n') + 1


def plain_ok(t):
    """正文只允许用一个空行分段；段内换行、控制字符、游戏指令字符一律不行。"""
    if not isinstance(t, str) or not t.strip():
        return False
    parts = t.strip().split('\n\n')
    return all(p.strip() == p and p and '\n' not in p and not SPECIAL & set(p) and all(ord(c) >= 32 for c in p)
               for p in parts)


def loc_text(t, lang):
    """段落之间的空行写成本地化里的 \\n\\n，游戏显示为空一行。"""
    if lang == 'zh':
        t = ZH_HYPHEN.sub('‑', t)
    return t.strip().replace('\n\n', '\\n\\n')


def loc_key(prefix, eid):
    k = f'{prefix}{eid}'
    return KEY_RENAMES.get(k, k)


def yml(lang, rows):
    return (f'l_{lang}:\n' + ''.join(f' {k}: "{v}"\n' for k, v in rows)).encode('utf-8-sig')


def payload(root, cfg, rows):
    """模组里每个文件的内容：{相对路径: bytes}。构建和核对都用它，保证两边一致。"""
    files = {}
    meta = {'name': cfg['name'], 'version': cfg['version'], 'game_id': 'eu5',
            'supported_game_version': cfg['supported_game_version'], 'short_description': cfg['short_description'],
            'tags': cfg['tags'], 'id': cfg['mod_id'], 'relationships': [], 'game_custom_data': {}}
    files['.metadata/metadata.json'] = (json.dumps(meta, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    files['.metadata/thumbnail.png'] = project_file(root, cfg['thumbnail_file']).read_bytes()
    files[GUI] = project_file(root, 'mod_template/' + GUI).read_bytes()
    by = {k: [r for r in rows if r['kind'] == k] for k in KINDS}
    cl = []
    for kind, (cname, typ, prefix, trig) in CUSTOM.items():
        cl += [f'{cname} = {{', f'\ttype = {typ}']
        for r in by[kind]:
            cl += ['\ttext = {', f'\t\tlocalization_key = {loc_key(prefix, r["id"])}',
                   f'\t\ttrigger = {{ {trig(r["id"])} }}', '\t}']
        cl += ['\ttext = {', '\t\tlocalization_key = lde_desc_none', '\t\tfallback = yes', '\t}', '}', '']
    files[CL_FILE] = '\n'.join(cl).encode('utf-8-sig')
    for lang, key in (('english', 'en'), ('simp_chinese', 'zh')):
        new, rep = [('lde_desc_none', '')], []
        for kind in DESC_KINDS:
            for r in by[kind]:
                (rep if r.get('official') else new).append((f'{r["id"]}_desc', loc_text(r[key], key)))
        for kind, (_, _, prefix, _) in CUSTOM.items():
            new += [(loc_key(prefix, r['id']), loc_text(r[key], key)) for r in by[kind]]
        files[f'in_game/localization/{lang}/lde_history_entries_l_{lang}.yml'] = yml(lang, new)
        if rep:
            files[f'in_game/localization/{lang}/replace/lde_history_entries_replace_l_{lang}.yml'] = yml(lang, rep)
        n = sum(len(v) for v in by.values())
        if len(new) - 1 + len(rep) != n:
            raise ValueError(f'{lang} 本地化条数不对：{len(new) - 1 + len(rep)}/{n}')
    for name in LICENSE_FILES:
        files[name] = project_file(root, name).read_bytes()
    for name, src in PLAYER_DOCS.items():
        files[name] = project_file(root, src).read_bytes()
    files['sources/sources.jsonl'] = ''.join(
        json.dumps({'kind': r['kind'], 'id': r['id'], 'sources': r['sources']}, ensure_ascii=False) + '\n'
        for r in rows).encode('utf-8')
    if files['.metadata/thumbnail.png'][:8] != b'\x89PNG\r\n\x1a\n' or len(files['.metadata/thumbnail.png']) >= 1_000_000:
        raise ValueError('thumbnail.png 不是 PNG 或超过 1 MB（工坊上限）')
    return files


def counts(rows):
    by = Counter(r['kind'] for r in rows)
    return {'total': len(rows), **{k: by.get(k, 0) for k in KINDS}}


# ───────────────────────────── 构建、核对、安装

def page_counts(root, rows):
    """工坊文案、更新说明和玩家说明里写的千位数（如 [b]5,286[/b]）必须是这次构建的总数或某一类的条数，
    不是的文件列出来。链接到其他工坊条目的行（“我的其他模组”）写的是那些模组的数量，不算。"""
    allowed = set(counts(rows).values())
    bad = []
    for rel in ('workshop/description.en.txt', 'workshop/description.zh-CN.txt', 'workshop/changenotes.en.txt',
                'workshop/changenotes.zh-CN.txt', 'workshop/player-readme.en.md', 'workshop/player-readme.zh-CN.md'):
        p = root / rel
        if p.exists():
            text = '\n'.join(l for l in p.read_text(encoding='utf-8').splitlines() if 'sharedfiles/filedetails' not in l)
            nums = {int(x.replace(',', '')) for x in re.findall(r'\b\d{1,3}(?:,\d{3})+\b', text)}
            if nums - allowed:
                bad.append(f'{rel}: {sorted(nums - allowed)}')
    return bad


def write_tree(files, out):
    for name, b in files.items():
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)


def tree_digests(d):
    return {p.relative_to(d).as_posix(): sha256(p.read_bytes()) for p in sorted(d.rglob('*')) if p.is_file()}


def mod_folder_name(cfg):
    return cfg['mod_id']


def zip_name(cfg):
    return f'{cfg["mod_id"]}-{cfg["version"]}.zip'


def build(root, output):
    root, output = root.resolve(), output.resolve()
    cfg = load_config(root)
    rows = load_rows(root, cfg.get('only_written'))
    if output.exists():
        raise FileExistsError(f'输出目录已存在，换一个新目录：{output}')
    files = payload(root, cfg, rows)
    write_tree(files, output / cfg['mod_id'])
    archive = output / zip_name(cfg)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(f'{cfg["mod_id"]}/{name}', date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, files[name], compresslevel=9)
    receipt = {'name': cfg['name'], 'mod_id': cfg['mod_id'], 'version': cfg['version'],
               'publishedfileid': cfg.get('publishedfileid'), 'entries': counts(rows),
               'verdicts': dict(Counter(r['verdict'] for r in rows)), 'licenses': cfg['licenses'],
               'built_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'files': {k: sha256(v) for k, v in sorted(files.items())},
               'bytes': sum(len(v) for v in files.values()), 'archive_sha256': sha256(archive.read_bytes())}
    (output / 'build_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    verify(root, output)
    return receipt


def verify(root, output):
    root, output = root.resolve(), output.resolve()
    cfg = load_config(root)
    rows = load_rows(root, cfg.get('only_written'))
    want = {k: sha256(v) for k, v in sorted(payload(root, cfg, rows).items())}
    have = tree_digests(output / cfg['mod_id'])
    if have != want:
        raise ValueError(f'已构建的文件和当前源文件算出的不一致：{sorted(set(have.items()) ^ set(want.items()))[:5]}')
    receipt = json.loads((output / 'build_receipt.json').read_text(encoding='utf-8'))
    if receipt['files'] != want or receipt['version'] != cfg['version'] or receipt['entries'] != counts(rows):
        raise ValueError('构建回执和当前源文件不一致')
    archive = output / zip_name(cfg)
    if sha256(archive.read_bytes()) != receipt['archive_sha256']:
        raise ValueError('ZIP 哈希和回执不一致')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or sorted(z.namelist()) != sorted(f'{cfg["mod_id"]}/{k}' for k in want):
            raise ValueError('ZIP 文件清单或校验不对')
        for k, h in want.items():
            if sha256(z.read(f'{cfg["mod_id"]}/{k}')) != h:
                raise ValueError(f'ZIP 里 {k} 和回执不一致')
    return receipt


def game_running():
    if os.name != 'nt':
        return False
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq eu5.exe'], capture_output=True, text=True, errors='replace')
    return 'eu5.exe' in r.stdout.lower()


def install(cfg, src, mod_root=MOD_ROOT):
    """装进 EU5 用户模组目录：先写临时目录、核对哈希，再整体改名替换；只替换本模组自己的旧副本。"""
    name = cfg['mod_id']
    dst, tmp, old = mod_root / name, mod_root / f'.{name}.new', mod_root / f'.{name}.old'
    if dst.exists():
        try:
            mine = json.loads((dst / '.metadata' / 'metadata.json').read_text(encoding='utf-8-sig')).get('id') == name
        except (OSError, ValueError):
            mine = False
        if not mine:
            raise ValueError(f'{dst} 已存在但不是本模组，不替换')
    for p in (tmp, old):
        if p.exists():
            shutil.rmtree(p)
    shutil.copytree(src, tmp)
    if tree_digests(src) != tree_digests(tmp):
        raise RuntimeError('临时目录哈希不一致，没有替换')
    if dst.exists():
        os.replace(dst, old)
    os.replace(tmp, dst)
    shutil.rmtree(old, ignore_errors=True)
    n = len(tree_digests(dst))
    print(f'已装进 {dst}，{n} 个文件哈希一致。' + ('游戏正在运行，会自动重载，等它读完；不行就冷启动。'
                                                if game_running() else '下次启动游戏生效。'))
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='只检查数据和配置')
    mode.add_argument('--verify', type=Path, help='核对已构建的目录')
    mode.add_argument('--install', action='store_true', help='开发用：构建到 dist/dev 并装进本机')
    ap.add_argument('--output', type=Path, help='构建目录（必须是新的）')
    ap.add_argument('--only-written', action='store_true', help='和 --install 一起用：只放 written')
    ap.add_argument('--game-root', type=Path, help='EU5 安装目录，和 --check 一起用')
    a = ap.parse_args()
    cfg = load_config(ROOT)
    if a.only_written:
        if not a.install:
            ap.error('--only-written 只用于 --install；正式构建改 project.json 的 only_written')
        cfg['only_written'] = True
    if a.check:
        rows = load_rows(ROOT, cfg.get('only_written'))
        payload(ROOT, cfg, rows)
        out = {'ok': True, 'version': cfg['version'], 'entries': counts(rows),
               'verdicts': dict(Counter(r['verdict'] for r in rows))}
        out['page_count_mismatch'] = page_counts(ROOT, rows)
        if a.game_root:
            out['game'] = check_game(ROOT, cfg, a.game_root)
        print(json.dumps(out, ensure_ascii=False))
    elif a.verify:
        r = verify(ROOT, a.verify)
        print(json.dumps({'verified': True, 'version': r['version'], 'files': len(r['files']),
                          'archive_sha256': r['archive_sha256']}, ensure_ascii=False))
    elif a.install:
        # 开发副本和工坊订阅的正式版同名，播放集里分不清；只给开发安装的名字加后缀，正式构建不受影响
        cfg['name'] = f"{cfg['name']} (local dev)"
        rows = load_rows(ROOT, cfg.get('only_written'))
        out = ROOT / 'dist' / 'dev' / cfg['mod_id']
        if out.exists():
            shutil.rmtree(out)
        write_tree(payload(ROOT, cfg, rows), out)
        print(f'构建 {len(rows)} 条到 {out}')
        install(cfg, out)
    else:
        if not a.output:
            ap.error('正式构建要给 --output dist/<新目录>')
        r = build(ROOT, a.output)
        print(json.dumps({k: r[k] for k in ('version', 'entries', 'verdicts', 'bytes', 'archive_sha256')},
                         ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
