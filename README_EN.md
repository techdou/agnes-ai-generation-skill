# Agnes AI Generation Skill

[中文](README.md)

Agnes AI Generation Skill is a standard Agent Skills package for calling Agnes AI text, image, and video generation APIs. It can be installed into Codex, Claude Code, OpenClaw, Cursor, Windsurf, and other clients that support Agent Skills. After installation, AI agents can use Agnes models for text generation, text-to-image, image-to-image, text-to-video, image-to-video, multi-image video, and keyframe animation workflows.

Official platform: [https://platform.agnes-ai.com/](https://platform.agnes-ai.com/)

## Features

- Text generation with `agnes-2.0-flash`
- Streaming text responses
- OpenAI-compatible tool-calling request shape
- Text-to-image with `agnes-image-2.1-flash`
- Image-to-image editing with `agnes-image-2.1-flash`
- High-information-density image generation
- Text-to-video with `agnes-video-v2.0`
- Image-to-video with `agnes-video-v2.0`
- Multi-image video generation
- Keyframe animation
- Prompt-based motion and scene control
- Cinematic video output
- Asynchronous video task creation
- Polling-based video result retrieval
- Seed-based reproducibility
- Automatic English prompt translation for non-English image/video prompts
- **Self-update guard**: runtime check against `GET /v1/models` to detect model deprecations or new model releases

## Quick Start

### 1. Apply for an Agnes API Key

1. Open [https://platform.agnes-ai.com/](https://platform.agnes-ai.com/).
2. Register or sign in.
3. Create an API key from the platform.
4. Set the key as an environment variable (**do not commit it to Git**).

### 2. Install This Skill

```bash
# Install into the current agent
npx skills add techdou/agnes-ai-generation-skill

# Or clone manually into your agent skills directory
git clone https://github.com/techdou/agnes-ai-generation-skill.git ~/.agents/skills/agnes-ai-generation-skill
```

### 3. Configure the API Key

For the current PowerShell session:

```powershell
$env:AGNES_API_KEY="YOUR_API_KEY"
```

For persistent Windows user-level configuration:

```powershell
[Environment]::SetEnvironmentVariable("AGNES_API_KEY", "YOUR_API_KEY", "User")
```

The script also accepts:

- `AGNES_API_KEY`
- `AGNES_API_TOKEN`
- `APIHUB_AGNES_API_KEY`

### 4. Use the Skill

Ask your AI agent:

```text
Use Agnes to generate a high-information-density futuristic city image.
```

Or:

```text
Use Agnes to turn this image into a cinematic video.
```

## Usage Examples

Text:

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

Text-to-video:

```powershell
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

Video commands default to `--num-frames 121 --frame-rate 24` and validate that `num_frames` satisfies `8n + 1` and is no more than `441`.

Image-to-video:

```powershell
python scripts/agnes_api.py video --prompt "Animate subtle camera movement and natural lighting" --image https://example.com/image.png --poll
```

Multi-image / keyframe video:

```powershell
python scripts/agnes_api.py video --prompt "Create a smooth cinematic transition between the two keyframes" --image https://example.com/a.png --image https://example.com/b.png --mode keyframes --poll
```

Retrieve a video task:

```powershell
python scripts/agnes_api.py video-get video_123456
```

By default, output is normalized with common fields such as `content`, `urls`, `translated_prompt`, and `next_steps`, while preserving the provider response under `raw`.

By default, return generated image or video `urls` directly. Do not download, save, or inspect media locally unless the user explicitly asks for a local file or visual inspection.

Add `--raw` to print only the original Agnes response.

## Self-Update Guard

Agnes does not provide a public `llms.txt` index, so this skill uses the OpenAI-compatible **`GET /v1/models`** endpoint as the authoritative source and fetches public doc pages as a secondary signal.

```powershell
# Standalone check
python scripts/agnes_api.py check

# Force refresh cache
python scripts/agnes_api.py check --force-refresh

# JSON output for programmatic use
python scripts/agnes_api.py check --format json

# Non-blocking pre-flight check on any generation command
python scripts/agnes_api.py text --prompt "hi" --check-docs
python scripts/agnes_api.py image --prompt "hello" --check-docs
python scripts/agnes_api.py video --prompt "test" --check-docs
```

`check` reports **CRITICAL** when a local model is no longer in the official `/v1/models` list, and **INFO** when a new model appears on the server. By default it is non-blocking.

## Smoke Tests

Light smoke test. By default, this checks text, streaming text, tool-calling request shape, and text-to-image only. It does not create video tasks:

```powershell
python scripts/agnes_api.py smoke-test
```

The tool-calling request can be accepted by Agnes without returning `tool_calls` consistently. By default this is reported as a warning. Use strict mode to fail in that case:

```powershell
python scripts/agnes_api.py smoke-test --strict-tools
```

Image-to-image smoke test:

```powershell
python scripts/agnes_api.py smoke-test --include-image-edit
```

Single video case test:

```powershell
python scripts/agnes_api.py smoke-test --video-case text-to-video
```

## Prompt Language

English prompts are more stable for Agnes video generation. For image and video calls, this skill automatically translates non-English prompts to English before sending them to the Agnes image/video APIs. It preserves subjects, scene details, style, lighting, composition, camera movement, motion, and constraints.

To disable automatic translation:

```powershell
python scripts/agnes_api.py video --prompt "non-English prompt" --no-translate-prompt
```

## Repository Structure

```text
.
├── SKILL.md
├── README.md
├── README_EN.md
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml
├── references/
│   └── api.md
├── scripts/
│   ├── agnes_api.py
│   └── check_official_docs.py
└── templates/
    └── known_rules.json
```

## Security

- Do not commit API keys to Git, README files, screenshots, or public chat logs.
- `.gitignore` already excludes `.env`, `.env.*`, key files, credentials, and the `output/` generation directory.

## License

MIT License. See [LICENSE](LICENSE).
