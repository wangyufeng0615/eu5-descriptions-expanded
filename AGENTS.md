# 描述扩展（Descriptions Expanded: Countries, Cultures, Dynasties & More）：发布工程

这里把研究工程写好的国家、文化、王朝、语言、语族、圣地介绍构建成 EU5 模组，装进本机游戏做实验，也从这里发布到创意工坊。模组 ID `descriptions_expanded`，工坊条目 3838927963 公开，当前版本 1.1.1（2026-11-14）。正文、对象识别和写作规则都在研究工程，这里不改正文。

用户 2026-11-12 定：以后所有新类别的描述（宗教、文化组、神祇等）都加进这个模组，不再另开新模组，所以模组名不写具体类别以外的限定。

## 三处位置

| | 位置 | 管什么 |
|---|---|---|
| 研究工程 | MacBook `~/personal/paradox-mods/eu5-history-entries/research`（本地 Git，暂无远端） | 5,294 个对象的身份卡、介绍、写作规则、批量写作调度器、评审工具 |
| 发布工程 | 本目录，Windows `V:\paradox-mods\eu5-history-entries\workshop`（本地 Git，暂无远端） | 构建、装进游戏、工坊文案和发布 |
| 测试副本 | Windows `文档\Paradox Interactive\Europa Universalis V\mod\history_entries` | 2026-11-12 研究工程直接构建的测试版（模组 ID `history_entries`），不在任何播放集里；本工程装上 `descriptions_expanded` 后删掉它，两个不要同时启用 |

## 数据怎么流动

只单向：研究工程 `tools/export_workshop.py` 把通过自检的 `written`、`stub` 导出到本目录的 `data/entries.jsonl`，连同三个改写过的浮窗模板 `mod_template/in_game/gui/zz_lde_history_tooltips.gui` 和原版模板哈希 `data/vanilla_gui.json`。这里只读不改；改正文回研究工程改，再同步。

在 MacBook 上一步做完（导出、拷到这里、提交、构建并装进游戏）：

```bash
cd ~/personal/paradox-mods/eu5-history-entries/research && tools/sync_workshop.sh
```

## 检查与构建

```bat
cd /d V:\paradox-mods\eu5-history-entries\workshop
python -B -m unittest discover -s tests -v
python -B tools\build.py --check [--game-root "C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V"]
python -B tools\build.py --install            :: 构建到 dist\dev 并装进模组目录（名字带 "(local dev)"）
python -B tools\build.py --uninstall          :: 测完删掉开发副本（游戏要先关）
python -B tools\build.py --output dist\<新目录>
python -B tools\build.py --verify dist\<新目录>
```

只用 Python 标准库（3.10+）。`--check` 校验数据（每条要有中英文正文和资料来源、段数一致、没有段内换行和游戏指令字符）、配置和生成结果，并核对工坊文案里的千位数只能是总数或某一类的条数；带 `--game-root` 时再核对三个原版浮窗模板有没有随游戏更新变化、当前 Steam 构建号。

## 发布

1. **更新数据**：研究工程评审流程跑完后 `tools/sync_workshop.sh`，进游戏看几个国家、文化、王朝、圣地的浮窗（中英文各看）。
2. **准备版本**：`python -B tools\release.py <版本> --note "..." --install --commit`。升版本号、写 `CHANGELOG.md`、跑测试和检查、构建到 `dist\release-<版本>\`、核对、装进游戏并提交；失败会改回去。`project.json` 初始版本是 0.0.0，本模组首次打包为 1.0.0。用 `--install` 时会另外装入本地副本。
3. **第一次上传**：作者确认后，在登录了 Steam 的桌面会话里依次运行（都用计划任务放进桌面会话：`schtasks /create ... /ru <用户名> /it` 再 `/run`，跑完删任务）：
   1. `python -B tools\steam_create.py 0.1.0 --notes-file workshop\changenotes.en.txt --output dist\create-0.1.0.json`：建私密条目，Steam 返回编号就写进 `project.json`。
   2. `python -B tools\steam_page.py --host-images --output dist\host-images.json`：把覆盖表图（`workshop/assets/coverage-20261112/`，`render.py` 在 Windows 上生成）存进 Steam 云并公开分享，网址记进 `page.json` 的 `description_image_urls`。托管要求条目已存在，所以放在建条目之后。
   3. 把两张图的网址各写成一行 `[img]<网址>[/img]`，插在 `description.*.txt` 的标题下面，再 `steam_page.py --descriptions` 推中英文标题和描述，`--assets` 补中文封面和截图。
   改公开由作者在网页上做。
4. **之后的更新**：`release.py <新版本>`，再 `steam_upload.py <版本> --upload --notes-file workshop\changenotes.en.txt --output dist\upload-<版本>.json`；中文更新说明的补法见人物模组发布工程 `AGENTS.md`「发布」第 5 步。
5. **更新说明**：`workshop/changenotes.*.txt` 第一行写版本号，`description.*.txt` 的「更新记录」加一行。

## 发布前还没做

- 2026-11-12 用户定：工坊文案照地块模组的写法，大幅简化，只讲补了哪些对象、各多少（覆盖表图）；兼容铁人和成就照人物模组写；AI 一段照地块模组，不点名模型。
- 2026-11-13 成就实测：游戏 1.4.7，用户播放集（7 个创意工坊模组）主菜单校验码 5b61，加上本模组变 4152，只加一个纯本地化测试模组变 5bd8，说明 EU5 的校验码随本地化改变；但两种情况下选国界面奖杯的成就条件全部打勾（含“未使用任何特殊启动项，例如校验码未修改”），所以“兼容成就”有实测依据。铁人模式本身没单独测。
- 2026-11-13 用户定新文案和封面：文案去掉 h1 和“我的其他 MOD”“更新记录”两节，写明用到的模型，不再提官方 22 条；封面去掉圆圈插画，十个类目（国家、王朝、文化、文化组、宗教、宗教信条、神祇、圣地、语言、语族，名称照游戏 game_concept_*）用彩色粗体字全部列出，不写“更多”。封面由 `tools/cover.py compose`（macOS 上跑，兰亭黑特黑和 Impact）从 `cover-source.en.png`（Codex 原始母版，取英文标题和语言标签）生成两张母版，再 `derive`；加类目改 `CATEGORIES`。构建已接入宗教（replace/ 覆盖官方描述）；文化组、神祇、宗教信条还在研究工程里写，写完要在 `build.py` 的 `KINDS`、`DESC_KINDS` 加上，同步数据，更新覆盖表 `coverage.json`（render.py 已有这四类的名称）并重绘，文案里的总数改成新的合计。文案里的 `{{coverage}}`（覆盖表图片地址，`--host-images` 之后填）是占位符（QQ 群号已按其他模组页面填 518622967），`steam_page.py` 提交描述时遇到占位符会拒绝。
- 2026-11-13 截图已按分段后的文本重拍（190ebf8）。还差：用户确认文案（开头“原版只给其中 22 个”缺总数、版本号 0.0.0/0.1.0/1.0.0 待定），之后建私密条目上传。

- 2026-11-13 晚接入文化组、神祇、宗教信条（协调会话统一处理）：`build.py` 的 `KINDS`、`DESC_KINDS` 已加三类；用户定“原版已有描述的保留原版，我们的接在后面”，研究工程导出的行多一个 `official_raw`（原版原文，含 `$引用$`、`[函数]`），构建时 `<ID>_desc` = 原文 + `\n\n` + 我们的正文，原文只拦引号、反斜杠和换行（测试 `test_official_raw_is_kept_before_our_text`）。数据 6,088 条（宗教 291、文化组 213、神祇 118、信条 172 加原六类）。覆盖表加四类，条形改为绿=本模组撰写或补充、灰=只有原版描述；文案和玩家说明改为 6,088 条，加一句“原版已有描述的保留并补充”；`project.json` 简介改列新类别。已 `--install`。

## 文件

| 路径 | 内容 |
|---|---|
| `project.json` | 模组名（中英）、模组 ID、版本、游戏和工坊编号、`steam_api64.dll` 路径、简介、标签、许可、`only_written`、原版模板目录、核对过的 Steam 构建号 |
| `data/entries.jsonl` | 研究工程导出的介绍，一行一条：`kind`、`id`、`verdict`、`official`（官方已有描述、要替换的语言和圣地）、`en`、`zh`、`sources` |
| `data/vanilla_gui.json` | 三个原版浮窗模板（`in_game/gui/shared/` 下）的 sha256，游戏更新后用来判断要不要重新生成模板 |
| `mod_template/in_game/gui/zz_lde_history_tooltips.gui` | 研究工程生成的浮窗模板；`.metadata` 由 `build.py` 按 `project.json` 生成 |
| `tools/build.py` | 检查、构建、核对、装进游戏，只用标准库 |
| `tools/release.py`、`steam_create.py`、`steam_upload.py`、`steam_page.py`、`cover.py` | 复制自人物模组发布工程，只改了云文件名前缀 |
| `workshop/` | 工坊页面中英文案（BBCode）、更新说明、模组里附带的玩家说明、`page.json` |
| `workshop/assets/` | 英文封面母版 `cover-master.en.png`（Codex 生图，按系列封面风格，提示词 `cover-prompt.en.txt`，风格参考 `style-reference.jpg` 是人物模组封面）；中文母版 `cover-master.zh-CN.png` 由 `tools/cover.py compose-zh` 用英文母版的插画加兰亭黑特黑排的标题合成（生图模型写的粗体汉字笔画粘连，2026-11-12 弃用）；`cover.py derive` 导出 `cover.jpg`、`cover.zh-CN.jpg`、`thumbnail.png` |
| `LICENSE`、`LICENSES/`、`CREDITS.md` | 工具 MIT、正文 CC BY-SA 4.0（同系列其他模组），署名和第三方说明；都会打进模组 |

## 技术要点

- 语言、语族、圣地：原版浮窗已有描述位，写 `<ID>_desc`；官方已有描述的 22 条放进 `replace/` 覆盖（梵蒂冈 2026-11-12 实测，显示的是本模组版本）。
- 国家、文化、王朝：可定制本地化 `lde_country_desc`、`lde_culture_desc`、`lde_dynasty_desc` 按 `c:<代码>`、`culture:<ID>`、`dynasty = dynasty:<ID>` 选文本，各加一个空字符串兜底；浮窗模板用 `StringIsEmpty` 判断，没有介绍的不显示。王朝经 `Dynasty.GetDynastyHead.Custom` 取文本，没有在世领袖的王朝不显示。`对象.GetKey` 是内部序号，不能拼键名。
- 本地化键和原版 32 位哈希相撞时（error.log 报 `Localization key hash collision`）在 `build.py` 的 `KEY_RENAMES` 换名，目前 `lde_ctry_KIM`、`lde_ctry_VEN`。
- 游戏会在中文里的半角 `-` 后强行折行，`build.py` 把汉字之间的 `-` 换成 U+2011（原版中文的写法）。
- 中文正文里夹的外文词（如金雀花王朝的 planta genista）会被游戏单独排成一行，前后都折行；数字在行尾也可能被拆开。是游戏排版对混排的处理，原版风味文本也一样，暂不处理（2026-11-12 截图时发现）。
- 游戏开着时不要直接覆盖模组文件：`build.py --install` 先写临时目录、核对哈希，再整体改名替换。
- 游戏更新改了原版浮窗模板（`--check --game-root` 报 `templates_unchanged` 有 false），要在研究工程更新 `data/vanilla_gui/` 并重新导出。

## 1.0.0 私密上传（2026-11-13）

- [工坊条目 3838927963](https://steamcommunity.com/sharedfiles/filedetails/?id=3838927963)，1.0.0，隐藏。中英文标题、正文和改动说明均已用作者登录的 Chrome 回读。Steam 订阅下载的 15 个文件（11,155,741 字节）与 `dist/release-1.0.0/build_receipt.json` 的文件 SHA-256 全部一致。

- 2026-11-13 晚验收：条目已公开（API visibility=0），播放集“1”用工坊版，21:03 进游戏挂载无报错。但模组目录里的开发副本 `mod\descriptions_expanded` 和工坊版模组 ID 相同，**不在播放集里也被一起挂载**（debug.log 两条 Mounted Data）。当时两份游戏文件逐字节一致，没有影响显示；以后更新时旧开发副本会叠在新工坊版上，所以测完必须 `build.py --uninstall`（游戏开着时目录被锁，删不掉）。
- 画廊的游戏截图裁到浮窗主体，留出标题和正文。画廊依次为中文封面、7 张浮窗特写、英文覆盖表。中文覆盖表通过 Steam 云独立托管，只放在中文版正文。中英文工坊正文都把推荐的两款 MOD 放在第三段，用醒目标题和两项链接列表展示，紧接其后是覆盖表。
- Windows 计划任务用当前用户的交互会话启动 PowerShell，再切到发布目录运行 `steam_create.py`、`steam_page.py`。任务运行完删除。回执留在 `dist/create-1.0.0.json`、`dist/page-1.0.0.json`。

## 1.1.0（2026-11-14）

- 内容：新增 953 条（共 7,057）：1337 开局不在场的国家 865（含西班牙、大不列颠等只在建国规则里定义的可建国家）、宗教组 29、宗教学派 42、勋贵骑士团 17；浮窗修复（国家等介绍区上限 450，11 个原版浮窗说明块可滚动，语言浮窗三个列表限高）。用户 2026-11-14 进游戏测过，总体没问题。
- 封面：Codex（gpt-6.1-terra，high）改 `tools/cover.py` 的 `CATEGORIES` 和行分布（英文 5 行、中文 4 行），新增三色 #008F80、#D53633、#A438A5，在 macOS 上 compose、derive 后拷回。
- 流程：`build.py --uninstall` 删开发副本 → `release.py 1.1.0 --note … --commit`（4653dc9）→ 计划任务里 `steam_upload.py`（result 1，12,233,806 字节）和 `steam_page.py --host-images`（新覆盖表网址写进 `page.json` 和两份描述，fa8ce90）→ 计划任务里 `steam_page.py --descriptions`、`--assets`。中文改动说明用 Chrome 在 `editchangelogentry/3838927963/1794587775/?language=6` 补。
- 回读：API visibility 0、file_size 12233806，主封面哈希等于新 cover.jpg，中英正文和覆盖表图片都是新的，中英改动说明都在。本机订阅版发版时还没更新下来，没有核对下载文件。
- 注意：PowerShell 计划任务里 Python 写 stderr 会记成 NativeCommandError，看 `*_rc=` 和回执判断成败；在 Windows 上改 description 文件要按字节读写，`write_text` 会把换行改成 CRLF。

## 1.1.1（2026-11-14）

- 内容：覆盖率到 100%（7,075 条）。研究工程把 1.1.0 时判 skip 的 18 条（占位国家海盗、雇佣兵、旧德意志王国 OGK，14 个查不到对应的部族或地名政权，宗教学派三颂伽差）用 Codex 重写为 written 4、stub 14。
- 流程同 1.1.0，一个计划任务里依次 `steam_upload.py`（result 1，12,249,370 字节）、`--host-images`、替换正文图片网址、`--descriptions`、`--assets`，全部 rc=0；中文改动说明用 Chrome 补（条目 1794589802）。回读：公开、文件大小一致、中英正文是 7,075 和新覆盖表、中英改动说明都在。
- 注意：经 ssh 在 cmd 里给 `release.py --note` 传 `100%%` 会原样写进 CHANGELOG 和提交说明（cmd 交互模式不折叠 `%%`），这次事后改了 CHANGELOG；提交说明里留着 `%%`。
