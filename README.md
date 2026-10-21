# Agnes AI Generation Skill

[English](README_EN.md)

用于 Agent Skills 的 Agnes AI 生成技能，封装 Agnes 官方文本、图片、视频 API。采用标准 `SKILL.md` 结构，可安装到 Codex、Claude Code、OpenClaw、Cursor、Windsurf 等支持 Agent Skills 的客户端。安装后，AI 可直接调用 Agnes 模型完成文本生成、文生图、图生图、文生视频、参考图视频、关键帧动画等操作。

官网与 API 平台：[https://platform.agnes-ai.com/](https://platform.agnes-ai.com/)

当前版本：v1.3.0（2026-10-21 模型目录同步）

## 功能

- 文本生成：`agnes-3.0-flash`（免费）
- 流式文本响应
- OpenAI 兼容的工具调用请求结构
- 文生图：`agnes-image-2.5-flash`（免费）
- 图生图 / 图片编辑：`agnes-image-2.5-flash`
- 高信息密度图片生成
- 文生视频：`agnes-video-2.5-flash`（限时免费，720P）
- 参考图视频（`reference` 模式，最多 5 张参考图）
- 关键帧动画（`keyframe` 模式，指定首帧 / 尾帧）
- 基于提示词的运动与场景控制
- 电影感视觉输出
- 异步视频任务创建与轮询
- 基于 seed 的可重复生成
- 非英文图片/视频提示词自动翻译为英文
- **官方文档同步校验**：运行时检查 `/v1/models` 模型可用性

## 模型速查

| 类型 | 模型 | 计费 | 说明 |
| --- | --- | --- | --- |
| 文本 | `agnes-3.0-flash` | 免费（促销） | 默认文本模型 |
| 文本 | `agnes-2.5-flash` | 免费（促销） | 会输出 `reasoning_content`，注意 `max_tokens` 余量 |
| 文本 | `agnes-2.5-pro-alpha` / `-beta` | 付费 | 需要 Token Plan |
| 图片 | `agnes-image-2.5-flash` | 免费（促销） | 默认图片模型，官方称优于 2.1-flash |
| 图片 | `agnes-image-2.0-flash` / `2.1-flash` | 免费（促销） | 可互换 |
| 视频 | `agnes-video-2.5-flash` | 限时免费 | 默认视频模型，仅 720P，队列可能拥塞 |
| 视频 | `agnes-video-2.5` | 按秒计费 | 720P $0.025/s、1080P/1K $0.040/s、2K $0.055/s |

> "免费"= 当前促销价 $0，促销随时可能结束。已下线模型（2026-10-21 从 `/v1/models` 移除）：`agnes-2.0-flash`、`agnes-2.5-pro`、`agnes-video-v2.0`。

## 快速开始

### 1. 申请 Agnes API Key

1. 打开 [Agnes API 平台](https://platform.agnes-ai.com/)。
2. 注册或登录账号。
3. 在平台中创建 API Key。
4. 将 Key 配置为环境变量（**不要写入 Git 仓库**）。

### 2. 安装本 Skill

```bash
# 安装到当前 Agent
npx skills add techdou/agnes-ai-generation-skill

# 或手动 clone 到 Agent skills 目录
git clone https://github.com/techdou/agnes-ai-generation-skill.git ~/.agents/skills/agnes-ai-generation-skill
```

### 3. 配置 API Key

临时配置（当前 PowerShell 会话）：

```powershell
$env:AGNES_API_KEY="YOUR_API_KEY"
```

Windows 用户级持久配置：

```powershell
[Environment]::SetEnvironmentVariable("AGNES_API_KEY", "YOUR_API_KEY", "User")
```

也可以在 skill 目录下放一个 `.env` 文件（已被 `.gitignore` 排除），脚本会自动加载；shell 环境变量优先级更高。

脚本会识别以下变量名（按优先级）：

- `AGNES_API_KEY`
- `AGNES_API_TOKEN`
- `APIHUB_AGNES_API_KEY`

### 4. 开始使用

你可以直接对 AI 说：

```text
使用 Agnes 帮我生成一张高信息密度的未来城市图片。
```

或：

```text
使用 Agnes 把这张图片生成一段电影感视频。
```

## 命令示例

文本生成：

```powershell
python scripts/agnes_api.py text --prompt "Write a concise product tagline for an AI assistant."
```

文生图：

```powershell
python scripts/agnes_api.py image --prompt "A luminous floating city above a misty canyon at sunrise, cinematic realism" --size 1024x768
```

中文提示词文生图（脚本会自动翻译为英文）：

```powershell
python scripts/agnes_api.py image --prompt "一座高信息密度的未来城市集市，拥挤人群，飞行汽车，全息招牌，电影感写实风格"
```

图生图：

```powershell
python scripts/agnes_api.py image --prompt "Turn the scene into a rainy cyberpunk night while preserving composition" --image https://example.com/input.png
```

文生视频（默认 `agnes-video-2.5-flash`，`mode=text` 自动设定）：

```powershell
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

视频时长与分辨率：

```powershell
python scripts/agnes_api.py video --prompt "..." --seconds "5" --size 720P --aspect-ratio 16:9 --poll
```

参考图视频（带 `--image` 时 `mode=reference` 自动设定，`<Picture N>` 占位符引用第 N 张图）：

```powershell
python scripts/agnes_api.py video --prompt "<Picture 1> Animate subtle camera movement and natural lighting" --image https://example.com/image.png --poll
```

关键帧视频（带 `--first-frame` / `--last-frame` 时 `mode=keyframe` 自动设定）：

```powershell
python scripts/agnes_api.py video --prompt "Create a smooth cinematic transition between the two keyframes" --first-frame https://example.com/a.png --last-frame https://example.com/b.png --poll
```

付费高分辨率视频（按秒计费，需用户明确同意）：

```powershell
python scripts/agnes_api.py video --prompt "..." --model agnes-video-2.5 --size 1080P --poll
```

查询视频任务（完成的任务 URL 在返回的 `metadata.url`）：

```powershell
python scripts/agnes_api.py video-get video_123456
```

视频参数规则（Video 2.5 schema）：

- `mode` 必填，脚本自动推断：默认 `text`；带 `--image` 为 `reference`；带 `--first-frame`/`--last-frame` 为 `keyframe`
- `seconds`：`"4"`–`"12"`，默认 `"5"`
- `size`：`720P` / `1080P` / `1K` / `2K`；`2.5-flash` 仅支持 `720P`
- 参考图数量：`2.5-flash` ≤ 5 张，付费 `2.5` ≤ 8 张
- 旧版 v2.0 参数（`num_frames`、`width`、`height`、`fps`）已废弃，服务端会返回 `400 forbidden field`

默认输出会整理出 `content`、`urls`、`translated_prompt`、`next_steps`，同时保留 `raw` 原始响应。

若只想看原始响应，加 `--raw`：

```powershell
python scripts/agnes_api.py text --prompt "hi" --raw
```

## 官方文档同步校验（Self-Update Guard）

Agnes 官方文档在 `wiki.agnes-ai.com` 提供 [`llms.txt` 索引](https://wiki.agnes-ai.com/llms.txt)（全量 markdown 页面，含[定价页](https://wiki.agnes-ai.com/en/docs/pricing.md)），本 skill 使用 OpenAI 兼容的 **`GET /v1/models`** 作为权威校验源，并抓取 per-model 文档页（`wiki.agnes-ai.com/en/docs/<模型ID去点>.md`）作为辅助信号。

```powershell
# 独立运行校验
python scripts/agnes_api.py check

# 强制刷新缓存
python scripts/agnes_api.py check --force-refresh

# 以 JSON 输出，便于程序处理
python scripts/agnes_api.py check --format json

# 在任何生成命令前加 --check-docs，做非阻塞检查
python scripts/agnes_api.py text --prompt "hi" --check-docs
python scripts/agnes_api.py image --prompt "hello" --check-docs
python scripts/agnes_api.py video --prompt "test" --check-docs
```

`check` 默认只报告 **CRITICAL**（本地模型已不在官方 `/v1/models` 中）或 **INFO**（官方新增模型）。默认非阻塞；只有在模型下线时才会标记为 CRITICAL。本地基线快照在 `templates/known_rules.json`，官方目录变化时同步更新。

## 运行测试

```powershell
python scripts/agnes_api.py smoke-test
```

默认测试覆盖文本、流式文本、工具调用请求结构和文生图，不会创建视频任务。

```powershell
# 测试图生图
python scripts/agnes_api.py smoke-test --include-image-edit

# 单独测试某个视频能力
python scripts/agnes_api.py smoke-test --video-case text-to-video
```

可选的视频测试项：`text-to-video`、`image-to-video`、`multi-image`、`keyframes`。注意 2.5-flash 免费队列高峰期可能返回 `video_queue_full`，稍后重试即可。

## 提示词语言策略

Agnes 视频生成使用英文提示词更稳定。本 skill 默认会检测图片/视频提示词中的非英文字符，并先调用 `agnes-3.0-flash` 翻译成英文生成提示词，再调用图片或视频 API。

如需跳过自动翻译：

```powershell
python scripts/agnes_api.py video --prompt "中文提示词" --no-translate-prompt
```

## 仓库结构

```text
.
├── SKILL.md                  # skill 定义（Agent Skills 标准）
├── README.md                 # 中文说明
├── README_EN.md              # 英文说明
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml           # 客户端接口元数据
├── references/
│   └── api.md                # API 参考（端点、参数、错误码）
├── scripts/
│   ├── agnes_api.py          # CLI 主脚本
│   └── check_official_docs.py# 官方文档同步校验
└── templates/
    └── known_rules.json      # 官方模型目录本地快照
```

`output/`（运行缓存与生成产物）不入库；`.env` 及密钥文件不入库。

## 安全提醒

- 不要把 API Key 写入 Git 仓库、README、截图或公开聊天记录。
- `.gitignore` 已排除 `.env`、`.env.*`、密钥文件、敏感凭据、`output/` 运行产物、归档备份与个人开发笔记。

## 许可证

MIT License. See [LICENSE](LICENSE).
