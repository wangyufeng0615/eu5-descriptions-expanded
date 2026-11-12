# 描述扩展（Descriptions Expanded: Countries, Cultures, Dynasties & More）：发布工程

这里把研究工程写好的国家、文化、王朝、语言、语族、圣地介绍构建成 EU5 模组，装进本机游戏做实验，也从这里发布到创意工坊。模组 ID `descriptions_expanded`，工坊条目还没建（`project.json` 的 `publishedfileid` 为 null）。正文、对象识别和写作规则都在研究工程，这里不改正文。

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
python -B tools\build.py --output dist\<新目录>
python -B tools\build.py --verify dist\<新目录>
```

只用 Python 标准库（3.10+）。`--check` 校验数据（每条要有中英文正文和资料来源、段数一致、没有段内换行和游戏指令字符）、配置和生成结果，并核对工坊文案里的千位数只能是总数或某一类的条数；带 `--game-root` 时再核对三个原版浮窗模板有没有随游戏更新变化、当前 Steam 构建号。

## 发布

1. **更新数据**：研究工程评审流程跑完后 `tools/sync_workshop.sh`，进游戏看几个国家、文化、王朝、圣地的浮窗（中英文各看）。
2. **准备版本**：`python -B tools\release.py <版本> --note "..." --install --commit`。升版本号、写 `CHANGELOG.md`、跑测试和检查、构建到 `dist\release-<版本>\`、核对、装进游戏并提交；失败会改回去。`project.json` 初始版本是 0.0.0，第一次发布就是 `release.py 0.1.0 --note "First release." --install --commit`。
3. **第一次上传**：作者确认后，在登录了 Steam 的桌面会话里 `python -B tools\steam_create.py 0.1.0 --notes-file workshop\changenotes.en.txt --output dist\create-0.1.0.json`（建私密条目，Steam 返回编号就写进 `project.json`），再 `steam_page.py --descriptions` 补中文标题和描述、`--assets` 补中文封面和截图。都用计划任务放进桌面会话（`schtasks /create ... /ru <用户名> /it` 再 `/run`，跑完删任务）。改公开由作者在网页上做。
4. **之后的更新**：`release.py <新版本>`，再 `steam_upload.py <版本> --upload --notes-file workshop\changenotes.en.txt --output dist\upload-<版本>.json`；中文更新说明的补法见人物模组发布工程 `AGENTS.md`「发布」第 5 步。
5. **更新说明**：`workshop/changenotes.*.txt` 第一行写版本号，`description.*.txt` 的「更新记录」加一行。

## 发布前还没做

- 成就兼容：模组加了 `in_game/common` 下的可定制本地化，和人物模组同一种做法；2026-11-12 测试时主菜单校验码随模组内容变化。人物模组页面写了兼容成就，本模组页面暂未写，等作者确认。
- 作者确认工坊文案（`workshop/description.*.txt`），尤其“关于 AI 的使用”一段要不要像人物模组那样写明用了哪些模型。

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
- 游戏开着时不要直接覆盖模组文件：`build.py --install` 先写临时目录、核对哈希，再整体改名替换。
- 游戏更新改了原版浮窗模板（`--check --game-root` 报 `templates_unchanged` 有 false），要在研究工程更新 `data/vanilla_gui/` 并重新导出。
