"""第一次建本模组的工坊条目，可见性固定为私密，经由正在运行、已登录的 Steam 客户端（Windows 桌面会话里运行，不能在 SSH 里）。

python -B tools/steam_create.py 1.0.0 --notes-file workshop/changenotes.en.txt --output dist/create-1.0.0.json

只在 project.json 的 publishedfileid 还是 null 时运行；Steam 一返回条目编号就写进 project.json，之后重跑会直接拒绝，避免建出重复条目。
上传 dist/release-<版本>/ 里的模组文件夹、英文标题和描述、主封面、标签；中文标题描述和中文封面之后用 steam_page.py 补。
不读凭据，不接受条款：Steam 要求作者先接受工坊协议时，条目会建好但停下报错，交给作者。改公开由作者在网页上做。
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steam_page as SP  # noqa: E402
from steam_upload import check_release  # noqa: E402

ROOT = SP.ROOT
PRIVATE = 2  # k_ERemoteStoragePublishedFileVisibilityPrivate
COMMUNITY = 0  # k_EWorkshopFileTypeCommunity


class CreateResult(C.Structure):
    _fields_ = [('result', C.c_int), ('item', C.c_uint64), ('agreement', C.c_bool)]


class StringArray(C.Structure):
    _fields_ = [('strings', C.POINTER(C.c_char_p)), ('count', C.c_int32)]


class Creator(SP.Steam):
    def __init__(self):  # 和 Steam.__init__ 相同，只是不要求已有条目编号
        os.environ['SteamAppId'] = os.environ['SteamGameId'] = str(SP.APP)
        self.dll = C.CDLL(SP.DLL)
        if not self.bind('SteamAPI_Init', SP.B)():
            raise RuntimeError('Steam API initialization failed')
        self.ugc = self.bind('SteamAPI_SteamUGC_v016', SP.P)()
        self.utils = self.bind('SteamAPI_SteamUtils_v010', SP.P)()
        user = self.bind('SteamAPI_SteamUser_v021', SP.P)()
        self.owner = self.bind('SteamAPI_ISteamUser_GetSteamID', SP.U64, SP.P)(user)
        if not self.ugc or not self.utils or not self.owner:
            raise RuntimeError('Required Steam session is unavailable')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--notes-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project_path = ROOT / 'project.json'
    project = json.loads(project_path.read_text(encoding='utf-8'))
    if project.get('publishedfileid'):
        raise SystemExit(f'project.json 已有条目编号 {project["publishedfileid"]}，不再新建；更新用 steam_upload.py')
    folder, receipt = check_release(ROOT, args.version)
    notes = args.notes_file.read_text(encoding='utf-8-sig').strip()
    if notes.splitlines()[0].strip() != args.version:
        raise ValueError('Change notes must start with the requested version')
    page = json.loads((ROOT / 'workshop/page.json').read_text(encoding='utf-8'))
    title = page['titles']['english']
    desc = (ROOT / page['descriptions']['english']).read_text(encoding='utf-8')
    cover = ROOT / page['cover_images']['english']
    assert cover.is_file() and cover.stat().st_size < 1_000_000
    record = {'version': args.version, 'folder': str(folder), 'archive_sha256': receipt['archive_sha256']}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(record, out, ensure_ascii=False, indent=2)

    def save():
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    steam = Creator()
    try:
        made = steam.wait(steam.ug('CreateItem', SP.U64, [SP.U32, C.c_int], SP.APP, COMMUNITY), CreateResult, 3403)
        record.update(item=made.item, needs_agreement=made.agreement)
        save()
        project['publishedfileid'] = made.item
        project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if made.agreement:
            raise RuntimeError('条目已建好，但 Steam 要求作者先接受工坊协议：交给作者在网页上处理')
        h = steam.ug('StartItemUpdate', SP.U64, [SP.U32, SP.U64], SP.APP, made.item)
        assert steam.ug('SetItemUpdateLanguage', SP.B, [SP.U64, SP.S], h, b'english')
        assert steam.ug('SetItemTitle', SP.B, [SP.U64, SP.S], h, title.encode())
        assert steam.ug('SetItemDescription', SP.B, [SP.U64, SP.S], h, desc.encode())
        assert steam.ug('SetItemVisibility', SP.B, [SP.U64, C.c_int], h, PRIVATE)
        tags = (C.c_char_p * len(page['tags']))(*[t.encode() for t in page['tags']])
        assert steam.ug('SetItemTags', SP.B, [SP.U64, C.POINTER(StringArray)], h, C.byref(StringArray(tags, len(page['tags']))))
        assert steam.ug('SetItemContent', SP.B, [SP.U64, SP.S], h, str(folder).encode())
        assert steam.ug('SetItemPreview', SP.B, [SP.U64, SP.S], h, str(cover).encode())
        record['submission_started'] = True
        save()
        res = steam.wait(steam.ug('SubmitItemUpdate', SP.U64, [SP.U64, SP.S], h, notes.encode()), SP.UpdateResult, 3404)
        if res.agreement:
            raise RuntimeError('Steam 要求作者先接受工坊协议')
        SP.ITEM = made.item
        record['after'] = steam.query('english')
        if record['after']['visibility'] != PRIVATE:
            raise RuntimeError(f'可见性不是私密：{record["after"]["visibility"]}')
        record['private'] = True
        save()
        print(json.dumps({k: v for k, v in record.items() if k != 'after'}, ensure_ascii=False, indent=2))
    finally:
        steam.bind('SteamAPI_Shutdown', None)()


if __name__ == '__main__':
    main()
