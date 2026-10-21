# Agnes AI Generation Skill

[中文](README.md)

Agnes AI Generation Skill is a standard Agent Skills package for calling Agnes AI text, image, and video generation APIs. It can be installed into Codex, Claude Code, OpenClaw, Cursor, Windsurf, and other clients that support Agent Skills. After installation, AI agents can use Agnes models for text generation, text-to-image, image-to-image, text-to-video, reference-image video, and keyframe animation workflows.

Official platform: [https://platform.agnes-ai.com/](https://platform.agnes-ai.com/)

Current version: v1.3.0 (2026-10-21 model catalog sync)

## Features

- Text generation with `agnes-3.0-flash` (free)
- Streaming text responses
- OpenAI-compatible tool-calling request shape
- Text-to-image with `agnes-image-2.5-flash` (free)
- Image-to-image editing with `agnes-image-2.5-flash`
- High-information-density image generation
- Text-to-video with `agnes-video-2.5-flash` (limited-time free, 720P)
- Reference-image video (`reference` mode, up to 5 reference images)
- Keyframe animation (`keyframe` mode with first/last frame)
- Prompt-based motion and scene control
- Cinematic video output
- Asynchronous video task creation
- Polling-based video result retrieval
- Seed-based reproducibility
- Automatic English prompt translation for non-English image/video prompts
- **Self-update guard**: runtime check against `GET /v1/models` to detect model deprecations or new model releases

## Model Cheat Sheet

| Type | Model | Billing | Notes |
| --- | --- | --- | --- |
| Text | `agnes-3.0-flash` | free (promo) | default text model |
| Text | `agnes-2.5-flash` | free (promo) | returns `reasoning_content`; watch `max_tokens` headroom |
| Text | `agnes-2.5-pro-alpha` / `-beta` | paid | requires a Token Plan |
| Image | `agnes-image-2.5-flash` | free (promo) | default image model |
| Image | `agnes-image-2.0-flash` / `2.1-flash` | free (promo) | interchangeable |
| Video | `agnes-video-2.5-flash` | limited-time free | default video model, 720P only, queue may saturate |
| Video | `agnes-video-2.5` | per output second | 720P $0.025/s, 1080P/1K $0.040/s, 2K $0.055/s |

> "Free" means the current promotional price is $0; promotions can end without notice. Removed from `/v1/models` on 2026-10-21: `agnes-2.0-flash`, `agnes-2.5-pro`, `agnes-video-v2.0`.

## Quick Start

### 1. Get an Agnes API Key

1. Open the [Agnes API platform](https://platform.agnes-ai.com/).
2. Sign up or sign in.
3. Create an API Key.
4. Configure it as an environment variable (**never commit it to Git**).

### 2. Install the Skill

```bash
# Install into the current agent
npx skills add techdou/agnes-ai-generation-skill

# Or clone manually into your agent skills directory
git clone https://github.com/techdou/agnes-ai-generation-skill.git ~/.agents/skills/agnes-ai-generation-skill
```

### 3. Configure the API Key

Temporary (current PowerShell session):

```powershell
$env:AGNES_API_KEY="YOUR_API_KEY"
```

Persistent (Windows user level):

```powershell
[Environment]::SetEnvironmentVariable("AGNES_API_KEY", "YOUR_API_KEY", "User")
```

Alternatively, place a `.env` file in the skill directory (already excluded by `.gitignore`); the script loads it automatically, with shell environment variables taking precedence.

The script recognizes these variable names (by priority):

- `AGNES_API_KEY`
- `AGNES_API_TOKEN`
- `APIHUB_AGNES_API_KEY`

### 4. Start Using

Ask your AI agent:

```text
Use Agnes to generate a high-information-density futuristic city image.
```

or:

```text
Use Agnes to turn this image into a cinematic video.
```

## Command Examples

Text generation:

```powershell
python scripts/agnes_api.py text --prompt "Write a concise product tagline for an AI assistant."
```

Text-to-image:

```powershell
python scripts/agnes_api.py image --prompt "A luminous floating city above a misty canyon at sunrise, cinematic realism" --size 1024x768
```

Image-to-image:

```powershell
python scripts/agnes_api.py image --prompt "Turn the scene into a rainy cyberpunk night while preserving composition" --image https://example.com/input.png
```

Text-to-video (defaults to `agnes-video-2.5-flash`, `mode=text` is set automatically):

```powershell
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

Video duration and resolution:

```powershell
python scripts/agnes_api.py video --prompt "..." --seconds "5" --size 720P --aspect-ratio 16:9 --poll
```

Reference-image video (`mode=reference` is set automatically when `--image` is given; `<Picture N>` addresses the Nth image):

```powershell
python scripts/agnes_api.py video --prompt "<Picture 1> Animate subtle camera movement and natural lighting" --image https://example.com/image.png --poll
```

Keyframe video (`mode=keyframe` is set automatically when `--first-frame` / `--last-frame` are given):

```powershell
python scripts/agnes_api.py video --prompt "Create a smooth cinematic transition between the two keyframes" --first-frame https://example.com/a.png --last-frame https://example.com/b.png --poll
```

Paid higher-resolution video (bills per second; confirm with the user first):

```powershell
python scripts/agnes_api.py video --prompt "..." --model agnes-video-2.5 --size 1080P --poll
```

Retrieve a video task (the completed URL lives in `metadata.url`):

```powershell
python scripts/agnes_api.py video-get video_123456
```

Video parameter rules (Video 2.5 schema):

- `mode` is required; the script infers it automatically: `text` by default, `reference` with `--image`, `keyframe` with `--first-frame`/`--last-frame`
- `seconds`: `"4"`–`"12"`, default `"5"`
- `size`: `720P` / `1080P` / `1K` / `2K`; `2.5-flash` accepts `720P` only
- Reference image limits: `2.5-flash` ≤ 5, paid `2.5` ≤ 8
- Legacy v2.0 parameters (`num_frames`, `width`, `height`, `fps`) are removed; the server returns `400 forbidden field` for them

Normalized output summarizes `content`, `urls`, `translated_prompt`, and `next_steps`, while keeping the `raw` response.

For raw output only, add `--raw`:

```powershell
python scripts/agnes_api.py text --prompt "hi" --raw
```

## Self-Update Guard

The official Agnes docs live on `wiki.agnes-ai.com` with an [`llms.txt` index](https://wiki.agnes-ai.com/llms.txt) (full markdown pages, including the [pricing page](https://wiki.agnes-ai.com/en/docs/pricing.md)). This skill uses the OpenAI-compatible **`GET /v1/models`** endpoint as the authoritative source and fetches per-model doc pages (`wiki.agnes-ai.com/en/docs/<model-id-without-dots>.md`) as a secondary signal.

```powershell
# Run the check standalone
python scripts/agnes_api.py check

# Force refresh the cache
python scripts/agnes_api.py check --force-refresh

# JSON output for programmatic use
python scripts/agnes_api.py check --format json

# Non-blocking check attached to any generation command
python scripts/agnes_api.py text --prompt "hi" --check-docs
python scripts/agnes_api.py image --prompt "hello" --check-docs
python scripts/agnes_api.py video --prompt "test" --check-docs
```

`check` reports **CRITICAL** only when a locally known model has disappeared from `/v1/models`, and **INFO** when the provider adds models. It is non-blocking by default. The local baseline snapshot lives in `templates/known_rules.json`; update it when the official catalog changes.

## Running Tests

```powershell
python scripts/agnes_api.py smoke-test
```

By default this covers text, streaming text, the tool-calling request shape, and text-to-image, without creating any video task. Use `--strict-tools` to fail when the tool-calling response has no `tool_calls`:

```powershell
python scripts/agnes_api.py smoke-test --strict-tools
```

```powershell
# Also test image-to-image
python scripts/agnes_api.py smoke-test --include-image-edit

# Test one video capability at a time
python scripts/agnes_api.py smoke-test --video-case text-to-video
```

Video test cases: `text-to-video`, `image-to-video`, `multi-image`, `keyframes`. Note the 2.5-flash free queue can return `video_queue_full` at peak times; simply retry later.

## Prompt Language Policy

English prompts are more stable for Agnes video generation. The skill detects non-English image/video prompts and first translates them with `agnes-3.0-flash` before calling the image or video API, preserving subjects, scene details, style, lighting, composition, camera movement, motion, and constraints.

To skip automatic translation:

```powershell
python scripts/agnes_api.py video --prompt "中文提示词" --no-translate-prompt
```

## Repository Layout

```text
.
├── SKILL.md                  # skill definition (Agent Skills standard)
├── README.md                 # Chinese guide
├── README_EN.md              # English guide
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml           # client interface metadata
├── references/
│   └── api.md                # API reference (endpoints, parameters, errors)
├── scripts/
│   ├── agnes_api.py          # main CLI script
│   └── check_official_docs.py# official-doc sync checker
└── templates/
    └── known_rules.json      # local snapshot of the official model catalog
```

`output/` (runtime cache and generated artifacts), `.env`, and key files are not tracked.

## Security Notes

- Never commit your API Key to Git, README files, screenshots, or public chats.
- `.gitignore` excludes `.env`, `.env.*`, key files, credentials, `output/` artifacts, archive/backup files, and personal development notes.

## License

MIT License. See [LICENSE](LICENSE).
