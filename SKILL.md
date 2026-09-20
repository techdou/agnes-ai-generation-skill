---
name: agnes-ai-generation
version: 1.2.0
description: Call Agnes AI / Sapiens AI generation APIs for text, image, and video. Use when the user asks to use Agnes models, Agnes Image, Agnes Video, Agnes 2.0 Flash, Agnes 3.0 Flash, Agnes 2.5, apihub.agnes-ai.com, or to generate text, images, edit images, create videos, animate images, create keyframe videos, or test Agnes API calls.
---

# Agnes AI Generation

Use this skill to call Agnes text, image, and video generation APIs through `https://apihub.agnes-ai.com`.

## Quick Start

1. Read `references/api.md` when endpoint details, parameters, or response fields are needed.
2. Use `scripts/agnes_api.py` for real API calls instead of rewriting curl by hand.
3. Require an API key in `AGNES_API_KEY`, `AGNES_API_TOKEN`, or `APIHUB_AGNES_API_KEY`. Never print the key.
4. Run `python scripts/agnes_api.py check` to verify local model rules against the official `/v1/models` endpoint.
5. For light live verification, run `smoke-test`; it avoids video creation by default. Add `--include-image-edit` for image-to-image, and add `--video-case <case>` explicitly for video modes. Treat the skill as fully tested only when basic text, text streaming, text tool calling, text-to-image, image-to-image, text-to-video, image-to-video, multi-image video, keyframe video, and video retrieval return successful responses.

## Commands

Text generation:

```bash
python scripts/agnes_api.py text --prompt "Write a concise product tagline for an AI assistant."
```

Streaming text:

```bash
python scripts/agnes_api.py text --prompt "Write a short product intro." --stream
```

Streaming output is normalized and includes aggregated `content`, `events`, `done`, and a short `raw_prefix`.

Image generation:

```bash
python scripts/agnes_api.py image --prompt "A luminous floating city above a misty canyon at sunrise, cinematic realism" --size 1024x768
```

Image-to-image:

```bash
python scripts/agnes_api.py image --prompt "Turn the scene into a rainy cyberpunk night while preserving composition" --image https://example.com/input.png --size 1024x768
```

Text-to-video with polling:

```bash
python scripts/agnes_api.py video --prompt "A cinematic shot of a cat walking on the beach at sunset" --poll
```

Image-to-video:

```bash
python scripts/agnes_api.py video --prompt "Animate subtle camera movement and natural lighting" --image https://example.com/image.png --poll
```

Keyframe / multi-image video:

```bash
python scripts/agnes_api.py video --prompt "Create a smooth cinematic transition between the two keyframes" --image https://example.com/a.png --image https://example.com/b.png --mode keyframes --poll
```

Retrieve a video task:

```bash
python scripts/agnes_api.py video-get video_123456
```

Run the official-doc sync check:

```bash
python scripts/agnes_api.py check
```

Force refresh the cache:

```bash
python scripts/agnes_api.py check --force-refresh
```

Attach a non-blocking check to any generation command:

```bash
python scripts/agnes_api.py text --prompt "hi" --check-docs
python scripts/agnes_api.py image --prompt "hello" --check-docs
python scripts/agnes_api.py video --prompt "test" --check-docs
```

Light live smoke test:

```bash
python scripts/agnes_api.py smoke-test
```

Image edit smoke test:

```bash
python scripts/agnes_api.py smoke-test --include-image-edit
```

Single video smoke test:

```bash
python scripts/agnes_api.py smoke-test --video-case text-to-video
```

## Workflow

- Prefer `agnes-3.0-flash` for text chat/completions (free, live-tested 2026-09-21). `agnes-2.5-flash` is also free; the `2.5-pro*` tier is paid and needs a Token Plan. `agnes-2.0-flash` still works but is now a reasoning model: its `reasoning_content` burns `max_tokens` first, so keep `max_tokens` generous (≥100 short / ≥800 translation) or `content` may come back empty.
- Do not use Agnes Responses API multi-turn function calling for autonomous tool workflows. Live testing showed the provider can return `function_call` with overall `status=completed`, and submitting `function_call_output` with `previous_response_id` may fail. Use this skill's chat completions path for text generation and treat tool-calling as best-effort request-shape compatibility only.
- Prefer `agnes-image-2.5-flash` for text-to-image, image-to-image, and high-information-density image generation (free; officially exceeds 2.1-flash). `2.0-flash` / `2.1-flash` remain free equivalents. High-density generation is prompt-driven; include subject hierarchy, environment, secondary details, lighting, composition, and quality requirements.
- Prefer `agnes-video-v2.0` for text-to-video, image-to-video, multi-image video, keyframe animation, prompt-based motion and scene control, cinematic output, asynchronous task creation, polling-based result retrieval, and seed-based reproducibility. It is free and its queue is stable.
- ⚠ `agnes-video-2.5` (paid per second) and `agnes-video-2.5-flash` (limited-time free) use a **new, incompatible parameter schema** (`mode` required: `text`/`keyframe`/`reference`; `seconds` "4"–"12"; `size` 720P/1080P/1K/2K; `aspect_ratio`; `first_frame`/`last_frame`/`images`; `width`/`height`/`fps`/`num_frames` forbidden). This skill's script does not send that schema — selecting a 2.5-series model with the current `video` command returns `400 forbidden field`. See `references/api.md` § Video — 2.5 if the user explicitly wants the new series, and note the flash queue is often congested (`video_queue_full`).
- For image and video generation, convert any non-English user prompt to a fluent English generation prompt before calling the image/video API. English prompts are more stable for Agnes video generation. Preserve concrete visual details, style, lighting, composition, motion, camera instructions, and constraints during translation.
- For videos, remember the API is asynchronous: create a task first, then poll or retrieve by `video_id` when the create response includes it. The script falls back to legacy `task_id` lookup only when `video_id` is absent.
- The script validates image sizes, video frame counts, frame rates, and dimensions before sending requests. `num_frames` must be `8n + 1` and `<= 441`; `81` or `121` are good short values.
- The video command defaults to `num_frames=121` and `frame_rate=24` for more stable generation. Video smoke tests default to `num_frames=81` and `frame_rate=24`.
- Warn the user before costly or long-running live video generation unless they explicitly asked to test or generate video. Paid models (video 2.5 per-second, text 2.5-pro*) bill real money — never pick them by default.
- Test video capabilities one at a time with `smoke-test --video-case <case>` to avoid creating many tasks at once. Supported cases are `text-to-video`, `image-to-video`, `multi-image`, and `keyframes`.

## Self-Update Guard

This skill checks itself against the official Agnes API state. The check uses two layers:

- **API layer**: `GET /v1/models` on `https://apihub.agnes-ai.com` verifies that the models used by this skill are still available. Catches deprecated or renamed models (CRITICAL).
- **Doc layer**: fetches the per-model markdown doc pages under `https://wiki.agnes-ai.com/en/docs` and `https://wiki.agnes-ai.com/zh-Hans/docs` (slug = model ID without dots, `.md` suffix) as a secondary signal. If a doc page 404s or stops mentioning its model ID, the skill reports WARNING/INFO issues. Expected: `agnes-2.0-flash` has no doc page on the current wiki (superseded by 2.5-flash).

The official docs now expose a full `llms.txt` index at `https://wiki.agnes-ai.com/llms.txt` (all pages as markdown, pricing at `/en/docs/pricing.md`) — consult it first when investigating upstream changes. `/v1/models` remains the authoritative model source. A local snapshot is kept in `templates/known_rules.json` and can be updated when the official model list changes.

The check is non-blocking by default. `agnes_api.py check` exits with a non-zero code only when CRITICAL issues are found (or with `--fail-on warning`). `--check-docs` on any generation command runs the check in advisory mode and prints warnings to stderr without stopping execution.

## Current Validation Notes

- Confirmed locally: skill metadata validation and Python syntax.
- Confirmed by live API (2026-09-21 sync pass): basic text on `agnes-3.0-flash` / `agnes-2.5-flash`, text-to-image on `agnes-image-2.1-flash` / `agnes-image-2.5-flash`, `/v1/models` catalog (12 models), official pricing page free/paid matrix, and 2.5-series parameter validation (schema errors reproduce as documented; queue was too congested to complete a 2.5-flash task end-to-end).
- Confirmed by live API (earlier passes): basic text, streaming text, tool-calling request shape, image-to-image, high-information-density text-to-image, Chinese prompt translation for image/video, completed text-to-video URL retrieval, and completed image-to-video URL retrieval.
- Caveat: Agnes may accept tool-calling request parameters without consistently returning `tool_calls`; use `smoke-test --strict-tools` when strict tool-call validation is required.
- Caveat: Agnes Responses API multi-turn function calling is not reliable for agent tool loops; do not rely on it for Codex/Claude-style automatic tool continuation.
- Supported by the script and smoke-test selector, but not re-run end-to-end in the latest pass: multi-image video and keyframe animation.
- Not yet confirmed end-to-end: completed URL retrieval for every multi-image video and keyframe animation task. A previous text-to-video task returned a provider-side `division by zero` error, so keep video retries visible and report provider errors clearly.

## Output Handling

- Return generated image/video URLs directly by default. Do not download, save, open, or inspect generated media unless the user explicitly asks for a local file or visual inspection.
- For image responses, expect URL-style results when `extra_body.response_format` is `url`.
- For video responses, extract URLs from `video_url`, `url`, or `remixed_from_video_id` when `status` is `completed`.
- For video retrieval, prefer `GET /agnesapi?video_id=...&model_name=agnes-video-v2.0`; legacy `GET /v1/videos/{task_id}` remains a fallback.
- If a request fails, report HTTP status and provider error body without exposing the API key.
