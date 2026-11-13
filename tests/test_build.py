"""python -B -m unittest discover -s tests -v"""
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'tools'))
import build  # noqa: E402
import release  # noqa: E402


def tiny_png():
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b''))


SRC = ['https://en.wikipedia.org/wiki/Kingdom_of_England']
ROWS = [
    {'kind': 'country', 'id': 'ENG', 'verdict': 'written', 'official': False,
     'en': 'England was a kingdom.', 'zh': '英格兰是一个王国。', 'sources': SRC},
    {'kind': 'country', 'id': 'VEN', 'verdict': 'written', 'official': False,
     'en': 'Venice was a republic.', 'zh': '威尼斯是一个共和国。', 'sources': SRC},
    {'kind': 'culture', 'id': 'english', 'verdict': 'stub', 'official': False,
     'en': 'The English.', 'zh': '英格兰人。', 'sources': SRC},
    {'kind': 'dynasty', 'id': 'plantagenet_dynasty', 'verdict': 'written', 'official': False,
     'en': 'The Plantagenets.', 'zh': '金雀花王朝。', 'sources': SRC},
    {'kind': 'language', 'id': 'english_language', 'verdict': 'written', 'official': True,
     'en': 'English is a language.', 'zh': '英语是一种语言。', 'sources': SRC},
    {'kind': 'holy_site', 'id': 'chartres_cathedral', 'verdict': 'written', 'official': False,
     'en': 'A cathedral.', 'zh': '一座主教座堂，属塞尔维亚-克罗地亚语区。', 'sources': SRC},
]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / 'repo'
        for rel in ('project.json', 'LICENSE', 'CREDITS.md', 'LICENSES', 'mod_template', 'workshop/player-readme.en.md',
                    'workshop/player-readme.zh-CN.md'):
            src, dst = REPO / rel, self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if src.is_dir() else shutil.copyfile)(src, dst)
        cfg = json.loads((self.root / 'project.json').read_text(encoding='utf-8'))
        (self.root / cfg['thumbnail_file']).parent.mkdir(parents=True, exist_ok=True)
        (self.root / cfg['thumbnail_file']).write_bytes(tiny_png())
        self.write_rows(ROWS)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_rows(self, rows):
        (self.root / 'data').mkdir(exist_ok=True)
        (self.root / 'data' / 'entries.jsonl').write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')

    def files(self):
        return build.payload(self.root, build.load_config(self.root), build.load_rows(self.root))


class TestBuild(Fixture):
    def test_build_verify_and_contents(self):
        out = self.tmp / 'dist' / 'r'
        r = build.build(self.root, out)
        self.assertEqual(r['entries']['total'], 6)
        cfg = build.load_config(self.root)
        mod = out / cfg['mod_id']
        meta = json.loads((mod / '.metadata' / 'metadata.json').read_text(encoding='utf-8'))
        self.assertEqual((meta['id'], meta['name'], meta['version']), (cfg['mod_id'], cfg['name'], cfg['version']))
        for name in ('.metadata/thumbnail.png', build.GUI, build.CL_FILE, 'sources/sources.jsonl', 'LICENSE',
                     'README.md', 'in_game/localization/simp_chinese/lde_history_entries_l_simp_chinese.yml',
                     'in_game/localization/english/replace/lde_history_entries_replace_l_english.yml'):
            self.assertTrue((mod / name).is_file(), name)
        cl = (mod / build.CL_FILE).read_text(encoding='utf-8-sig')
        self.assertIn('trigger = { exists = c:ENG this = c:ENG }', cl)
        self.assertIn('trigger = { this = culture:english }', cl)
        self.assertIn('trigger = { dynasty = dynasty:plantagenet_dynasty }', cl)
        self.assertEqual(cl.count('fallback = yes'), 3)
        build.verify(self.root, out)
        with self.assertRaises(FileExistsError):
            build.build(self.root, out)

    def test_official_goes_to_replace(self):
        f = self.files()
        new = f['in_game/localization/english/lde_history_entries_l_english.yml'].decode('utf-8-sig')
        rep = f['in_game/localization/english/replace/lde_history_entries_replace_l_english.yml'].decode('utf-8-sig')
        self.assertIn(' english_language_desc: "English is a language."\n', rep)
        self.assertNotIn('english_language_desc', new)
        self.assertIn(' chartres_cathedral_desc: "A cathedral."\n', new)

    def test_official_raw_is_kept_before_our_text(self):
        god = {'kind': 'god', 'id': 'nyambe_god', 'verdict': 'written', 'official': True,
               'en': 'Nyambe was worshipped widely.\n\nHe withdrew to the sky.', 'zh': '尼扬贝受到广泛崇拜。\n\n他退居天上。',
               'official_raw': {'en': "$nyambe_god$ is the main [gods|e] of the #bold Bantu#!.",
                                'zh': "$nyambe_god$是[gods|e]。"}, 'sources': SRC}
        self.write_rows([god])
        f = self.files()
        en = f['in_game/localization/english/replace/lde_history_entries_replace_l_english.yml'].decode('utf-8-sig')
        zh = f['in_game/localization/simp_chinese/replace/lde_history_entries_replace_l_simp_chinese.yml'].decode('utf-8-sig')
        self.assertIn(' nyambe_god_desc: "$nyambe_god$ is the main [gods|e] of the #bold Bantu#!.\\n\\n'
                      'Nyambe was worshipped widely.\\n\\nHe withdrew to the sky."\n', en)
        self.assertIn(' nyambe_god_desc: "$nyambe_god$是[gods|e]。\\n\\n尼扬贝受到广泛崇拜。\\n\\n他退居天上。"\n', zh)
        for bad_raw in ({'en': 'has "quote"', 'zh': '可'}, {'en': 'two\nlines', 'zh': '可'}, {'en': 'ok'}, 'text'):
            self.write_rows([{**god, 'official_raw': bad_raw}])
            with self.assertRaises(ValueError):
                build.load_rows(self.root)
        self.write_rows([{**god, 'official': False}])
        with self.assertRaises(ValueError):
            build.load_rows(self.root)

    def test_hash_collision_rename(self):
        f = self.files()
        en = f['in_game/localization/english/lde_history_entries_l_english.yml'].decode('utf-8-sig')
        self.assertIn(' lde_ctry_VEN_b: "Venice was a republic."\n', en)
        self.assertNotIn(' lde_ctry_VEN:', en)
        self.assertIn('localization_key = lde_ctry_VEN_b', f[build.CL_FILE].decode('utf-8-sig'))

    def test_zh_hyphen_between_han_is_nonbreaking(self):
        zh = self.files()['in_game/localization/simp_chinese/lde_history_entries_l_simp_chinese.yml'].decode('utf-8-sig')
        self.assertIn('塞尔维亚‑克罗地亚语', zh)
        en = build.loc_text('Serbo-Croatian', 'en')
        self.assertEqual(en, 'Serbo-Croatian')

    def test_verify_detects_tampering(self):
        out = self.tmp / 'dist' / 'r'
        build.build(self.root, out)
        p = out / build.load_config(self.root)['mod_id'] / build.GUI
        p.write_bytes(p.read_bytes() + b'#')
        with self.assertRaises(ValueError):
            build.verify(self.root, out)

    def test_paragraphs_become_loc_newlines(self):
        self.write_rows([{**ROWS[0], 'en': 'First part.\n\nSecond part.', 'zh': '第一段。\n\n第二段。'}])
        f = self.files()
        en = f['in_game/localization/english/lde_history_entries_l_english.yml'].decode('utf-8-sig')
        self.assertIn(' lde_ctry_ENG: "First part.\\n\\nSecond part."\n', en)

    def test_only_written(self):
        rows = build.load_rows(self.root, only_written=True)
        self.assertNotIn('english', [r['id'] for r in rows])

    def test_rejects_bad_rows(self):
        for bad in ({**ROWS[0], 'sources': []}, {**ROWS[0], 'en': 'has [brackets]'}, {**ROWS[0], 'zh': '两行\n文字'},
                    {**ROWS[0], 'verdict': 'skip'}, {**ROWS[0], 'en': 'Three\n\n\nnewlines.'},
                    {**ROWS[0], 'en': 'Two\n\nparagraphs.'}, {**ROWS[0], 'kind': 'deity'},
                    {**ROWS[0], 'official': True}):
            self.write_rows([bad])
            with self.assertRaises(ValueError):
                build.load_rows(self.root)
        self.write_rows([ROWS[0], ROWS[0]])
        with self.assertRaises(ValueError):
            build.load_rows(self.root)

    def test_page_counts(self):
        (self.root / 'workshop' / 'description.en.txt').write_text('[b]1,566[/b] countries', encoding='utf-8')
        bad = build.page_counts(self.root, build.load_rows(self.root))
        self.assertIn('workshop/description.en.txt: [1566]', bad)
        (self.root / 'workshop' / 'description.en.txt').write_text('[b]6[/b] entries; [url=https://steamcommunity.com/sharedfiles/filedetails/?id=1]2,000+[/url]', encoding='utf-8')
        self.assertNotIn('workshop/description.en.txt', ' '.join(build.page_counts(self.root, build.load_rows(self.root))))

    def test_install_replaces_only_own_copy(self):
        out = self.tmp / 'dist' / 'r'
        build.build(self.root, out)
        cfg = build.load_config(self.root)
        mods = self.tmp / 'mod'
        build.install(cfg, out / cfg['mod_id'], mods)
        build.install(cfg, out / cfg['mod_id'], mods)
        (mods / cfg['mod_id'] / '.metadata' / 'metadata.json').write_text('{"id": "other"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            build.install(cfg, out / cfg['mod_id'], mods)


class TestRelease(unittest.TestCase):
    def test_versions_and_changelog(self):
        self.assertEqual(release.parse_version('1.2.3'), (1, 2, 3))
        with self.assertRaises(ValueError):
            release.parse_version('1.2')
        cl = release.add_changelog_entry('# Changelog\n\n', '1.0.0', '2026-11-03', ['First.'])
        self.assertIn('## 1.0.0 — 2026-11-03', cl)


if __name__ == '__main__':
    unittest.main()
