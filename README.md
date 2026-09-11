# video-content-pipeline

一套可跨账号、跨内容类型复用的短视频生产 Skill。它把素材接入、视频匹配、字幕与画面辅助分析、飞书附件同步和剪映草稿生成拆成独立模块；不用飞书或剪映时，可以只运行本地流程。

> 安全原则：默认只做 dry-run。飞书上传和剪映草稿生成必须显式传入 `--execute`。

## 你可以用它做什么

- 按创作者名称，把任务记录与本地视频做一对一匹配。
- 找出缺失文件、重复记录、同名视频等不安全情况。
- 辅助检查字幕出现/消失时间、主要画面转场和疑难语音片段。
- 根据不同账号的语气、分类和受众生成字幕、标题、正文与标签。
- 可选地把视频附件上传到已有飞书记录。
- 可选地按已验证的数值化样式生成剪映草稿。

## 1. 安装

### 作为 Codex Skill 安装

仓库当前是私有仓库，需要使用有权限的 GitHub 账号：

```bash
mkdir -p ~/.codex/skills
git clone git@github.com:Naissy/video-content-pipeline.git ~/.codex/skills/video-content-pipeline
```

安装后可在 Codex 中直接说：

```text
使用 $video-content-pipeline，读取当前项目的 project.json，先 dry-run 处理这批视频。
```

也可以不安装为 Skill，直接克隆仓库并运行其中的 Python 脚本。

## 2. 准备一个视频项目

建议让 Skill 仓库和业务项目分开。业务项目保存自己的配置、素材和工作产物：

```text
my-video-project/
├── project.json
├── records.json
├── videos/
│   ├── alice.mp4
│   └── bob.mp4
└── work/
```

复制配置模板：

```bash
cd /path/to/my-video-project
cp ~/.codex/skills/video-content-pipeline/templates/project.template.json project.json
```

首次使用建议只开启本地模块：

```json
{
  "modules": {
    "local_intake": true,
    "feishu": false,
    "content_analysis": true,
    "xiaohongshu_research": false,
    "jianying": false
  }
}
```

然后按项目修改这些内容：

- `account.name`：账号显示名。
- `account.slug`：稳定的英文项目标识。
- `account.tone`：标题、字幕和正文的表达风格。
- `taxonomy`：当前账号允许使用的分类、受众和主题标签。
- `paths.video_root`：视频素材目录。
- `paths.work_root`：manifest、字幕和分析产物目录。
- `feishu.fields`：记录 JSON 或飞书表格中的实际字段名。

完整字段说明见 [`references/config-schema.md`](references/config-schema.md)。真实 `project.json` 已被 `.gitignore` 排除，不要把凭证直接提交到 Git。

## 3. 先做配置 dry-run

所有命令建议从业务项目根目录运行：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/run_pipeline.py \
  --config project.json \
  --dry-run
```

输出会显示启用的模块和计划经过的阶段。这个入口只负责验证和路由，不会代替各阶段的执行脚本。

## 4. 准备任务记录

本地记录可以是 JSON 数组，也可以放在 `records` 字段中。字段名必须与 `project.json` 的 `feishu.fields` 对应。使用默认模板时，最小示例如下：

```json
[
  {
    "id": "record-001",
    "Creator": "@alice",
    "Source URL": "https://example.com/video/001",
    "Video": []
  },
  {
    "id": "record-002",
    "Creator": "bob",
    "Source URL": "https://example.com/video/002",
    "Video": []
  }
]
```

本地文件名应能对应创作者名。匹配时会忽略大小写、开头的 `@`，以及空格、点、下划线和连字符的格式差异，但不会合并不同创作者。

## 5. 匹配记录和视频

先预览匹配结果，不写文件：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/match_videos.py \
  --config project.json \
  --records records.json \
  --video-dir videos \
  --output work/match-manifest.json \
  --dry-run
```

确认后写入本地 manifest：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/match_videos.py \
  --config project.json \
  --records records.json \
  --video-dir videos \
  --output work/match-manifest.json \
  --execute
```

结果包含四组数据：

- `matched`：唯一的一对一匹配，可以进入后续步骤。
- `unmatched_records`：有记录但没有对应视频，或缺少稳定字段。
- `unmatched_files`：有本地视频但没有对应记录。
- `ambiguous`：同一规范化名称对应多条记录或多个文件。

只处理 `matched`。出现 `ambiguous` 时应修正命名或记录，不要手工猜测映射。

## 6. 内容分析与字幕准备

内容生成由 Codex 根据原视频、`account.tone` 和 `taxonomy` 完成。如果要生成更贴合近期小红书语境的标题、正文和 Tag，启用 Creator Buddy 调研模块：

```json
{
  "modules": {
    "content_analysis": true,
    "xiaohongshu_research": true
  },
  "xiaohongshu": {
    "research_skill": "creator-buddy",
    "lookback_days": 30,
    "search_limit": 20,
    "title_count": 10,
    "tag_count": 10,
    "human_review_before_sync": true
  }
}
```

这一阶段采用两步链路：

1. `$creator-buddy` 只读搜索近期热门笔记，输出互动信号、关键词、标题公式、受众痛点和可借鉴结构。
2. `$video-content-pipeline` 再结合原视频和账号配置，生成原创的小红书标题、正文和 Tag。

推荐给 Codex 的完整任务描述：

```text
使用 $video-content-pipeline 分析 work/match-manifest.json 中的 matched 视频。
项目启用了 xiaohongshu_research：先调用 $creator-buddy，以小红书为平台，
根据视频主题搜索最近 30 天的热门笔记，提取关键词、标题公式、受众痛点和内容结构，
并保存带来源链接的 research_context。不要照抄原文，也不要编造不可用的热度数据。
然后结合原视频、account.tone、taxonomy 和 research_context，为每条视频输出：
原字幕、中文化字幕、内容简介、10 个标题候选、1 个推荐标题、正文、最多 10 个 Tag、分类和受众。
分类只能从 project.json 的 taxonomy 中选择；听不清的字幕进入人工校对，不要猜。
先把结果写入新的 work/batch-content.json，等待人工确认，不执行飞书同步或剪映生成。
```

如果 `$creator-buddy` 或小红书搜索后端不可用，必须把 `research_status` 标记为 `unavailable`，并将结果注明为 `content_only_fallback`，不能声称标题经过热点验证。详细数据结构和生成规则见 [`references/xiaohongshu-content.md`](references/xiaohongshu-content.md)。

准备剪映草稿时，每条视频还需要：

```json
{
  "file": "/absolute/path/to/alice.mp4",
  "creator": "alice",
  "source_url": "https://example.com/video/001",
  "duration": 8.5,
  "slug": "study-break",
  "subtitles": [
    {"start": 0.2, "duration": 2.1, "text": "第一句字幕"},
    {"start": 2.5, "duration": 2.8, "text": "第二句字幕"}
  ]
}
```

每段字幕必须满足：`start >= 0`、`duration > 0`，并且结束时间不能超过视频时长。

## 7. 可选：画面与语音辅助工具

这些工具默认只展示计划。真正生成 JSON、图片、音频切片或字幕文件时使用 `--execute`。

### 检测字幕边界

manifest 中需要一条包含 `text_overlays` 的匹配记录：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/detect_caption_changes.py \
  --config project.json \
  --video videos/alice.mp4 \
  --manifest work/overlay-manifest.json \
  --output work/caption-boundaries.json \
  --dry-run
```

执行阶段需要 Python 环境中已有 OpenCV 和 NumPy。

### 查找主要转场

创建 `work/boundaries.json`：

```json
[
  {"name": "intro_to_demo", "approximate_time": 3.2},
  {"name": "demo_to_result", "approximate_time": 8.7}
]
```

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/detect_major_transitions.py \
  --config project.json \
  --video videos/alice.mp4 \
  --boundaries work/boundaries.json \
  --output-dir work/transitions \
  --execute
```

### 生成边界检查图

创建 `work/windows.json`：

```json
[
  {"name": "caption-01", "start": 2.8, "end": 3.6, "step": 0.1}
]
```

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/make_boundary_sheets.py \
  --config project.json \
  --video videos/alice.mp4 \
  --windows work/windows.json \
  --output-dir work/boundary-sheets \
  --execute
```

### 细化疑难语音片段

输入必须是 whisper.cpp 可处理的 WAV 文件。创建 `work/segments.json`：

```json
[
  {
    "name": "unclear-sentence",
    "start": 4.2,
    "end": 7.6,
    "prompt": "Context words that may occur in this segment."
  }
]
```

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/refine_whisper_segments.py \
  --config project.json \
  --audio work/audio-16k.wav \
  --model /path/to/whisper-model.bin \
  --segments work/segments.json \
  --output-dir work/refined-transcript \
  --language auto \
  --execute
```

这个工具要求系统中已有 `whisper-cli`，仓库不会下载或附带模型。

## 8. 可选：同步飞书附件

先在 `project.json` 中启用飞书：

```json
{
  "modules": {
    "feishu": true
  },
  "feishu": {
    "base_token": "${FEISHU_BASE_TOKEN}",
    "table_id": "${FEISHU_TABLE_ID}"
  }
}
```

在终端设置环境变量，不要把真实值写入仓库：

```bash
export FEISHU_BASE_TOKEN="your-base-token"
export FEISHU_TABLE_ID="your-table-id"
```

先检查上传计划：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/sync_feishu.py \
  --config project.json \
  --manifest work/match-manifest.json \
  --dry-run
```

只有以下条件全部满足时才可执行：record ID 存在、创作者存在、来源 URL 完整、本地视频存在、附件列为空。

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/sync_feishu.py \
  --config project.json \
  --manifest work/match-manifest.json \
  --execute
```

执行需要已安装并登录 `lark-cli`。脚本只上传到已有记录，不会因匹配失败自动创建新记录。

## 9. 可选：生成剪映草稿

剪映模块要求：

- 单独安装兼容的 Jianying Skill。
- 本机存在所需文字预设和字体资源。
- 已有经过人工验证的数值化样式档案。
- `draft.style_verified` 为 `true`。
- `draft.overwrite` 必须为 `false`。

环境变量示例：

```bash
export JY_SKILL_ROOT="/path/to/jianying-editor-skill"
export JY_PRESET_ROOT="/path/to/local/text-presets"
export JY_STYLE_PROFILE="/path/to/verified-style-profile.json"
```

在 `project.json` 中设置 `modules.jianying` 为 `true`，然后先 dry-run：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/create_jianying_drafts.py \
  --config project.json \
  --manifest work/batch-content.json \
  --dry-run
```

确认每条视频的项目名、文件路径、字幕时间和依赖后再执行：

```bash
python3 ~/.codex/skills/video-content-pipeline/scripts/create_jianying_drafts.py \
  --config project.json \
  --manifest work/batch-content.json \
  --execute
```

每个视频会生成独立草稿，并包含主视频、字幕和作者署名轨道。加密草稿只能作为样式来源证明，不能作为 `JY_STYLE_PROFILE`，也不会被读取、复制或修改。

## 10. 常见问题

### 为什么匹配结果是 `ambiguous`？

同一创作者对应了多条记录或多个文件。请先让记录和文件恢复唯一映射，再重新运行；不要删除歧义结果后强行继续。

### 为什么本地模式还保留 `feishu.fields`？

匹配器把它作为通用记录字段映射使用。即使不连接飞书，`records.json` 的字段名也需要与这里一致。

### 为什么 dry-run 没有生成文件？

这是预期行为。工具默认把计划打印到终端；需要生成本地 manifest 或分析产物时，明确使用 `--execute`。飞书上传和剪映生成也采用同一安全边界。

### 可以覆盖已有剪映草稿吗？

不可以。这个 Skill 将覆盖视为阻塞错误，避免破坏人工调整或其他账号的项目。

### 会自动下载视频或 Whisper 模型吗？

不会。素材下载、版权确认、模型准备和个人剪映资源均由使用者管理。

## 依赖一览

| 能力 | 依赖 |
|---|---|
| 配置验证、记录匹配 | Python 3.9+ 标准库 |
| 字幕边界、转场、检查图 | OpenCV、NumPy |
| 疑难语音重转写 | `whisper-cli`、本地模型 |
| 飞书附件同步 | 已认证的 `lark-cli` |
| 剪映草稿 | 兼容的 Jianying Skill、本地预设、字体、已验证样式档案 |

## 开发与自检

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_check.py
python3 scripts/run_pipeline.py \
  --config templates/project.template.json \
  --dry-run
```

发布前检查会阻止账号专属值、个人绝对路径和超过 5 MiB 的文件进入仓库。
