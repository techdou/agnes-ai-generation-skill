# Agnes AI API Reference

Base host: `https://apihub.agnes-ai.com`

Authentication: `Authorization: Bearer YOUR_API_KEY`

Content type: `application/json`

Official doc index (llms.txt, all pages as markdown): `https://wiki.agnes-ai.com/llms.txt` — pricing at `https://wiki.agnes-ai.com/en/docs/pricing.md`, Chinese index at `https://wiki.agnes-ai.com/_llms/zh-hans.md`.

## Model Catalog (snapshot 2026-10-21)

Verified against `GET /v1/models` and the official pricing page. "Free" = current promotional price $0; promotions can end without notice.

| Family | Model | Billing |
| --- | --- | --- |
| Text | `agnes-2.5-flash` | free (promo) |
| Text | `agnes-2.5-pro-alpha` / `-beta` | paid ($0.10–$0.45/M input) |
| Text | `agnes-3.0-flash` | free (promo) |
| Image | `agnes-image-2.0-flash` / `2.1-flash` / `2.5-flash` | free (promo, all resolutions + reference images) |
| Video | `agnes-video-2.5` | paid, per output second (720P $0.025/s, 1080P/1K $0.040/s, 2K $0.055/s) |
| Video | `agnes-video-2.5-flash` | free (limited-time promo), 720P only; queue often congested |

Removed from `/v1/models` on 2026-10-21: `agnes-2.0-flash`, `agnes-2.5-pro`, `agnes-video-v2.0` (historical Deprecated doc pages remain). `agnes-3.0-pro` (paid) flickered into `/v1/models` and out the same day; pricing marks it "Coming soon" — re-add when it lands.

Deprecated earlier: `agnes-1.5-flash`.

Default picks in this skill: text `agnes-3.0-flash`, image `agnes-image-2.5-flash`, video `agnes-video-2.5-flash`.

## Text

Endpoint: `POST /v1/chat/completions`

Model: primary `agnes-3.0-flash`; `agnes-2.5-flash` also free. Avoid the paid `2.5-pro*` unless the user has a Token Plan.

Required:

- `model`
- `messages`: OpenAI-compatible chat messages

Optional:

- `temperature`: number
- `top_p`: number
- `max_tokens`: number
- `stream`: boolean
- `tools`: array
- `tool_choice`: string or object

Response is OpenAI-compatible and includes `choices[].message.content` and `usage`.

Reasoning-model note: `agnes-2.5-flash` returns a `reasoning_content` field and burns reasoning tokens against `max_tokens` first. With a small `max_tokens` the final `content` can come back empty — raise `max_tokens` (e.g. ≥100 for short answers, ≥800 for translations) instead of assuming the model is broken. `content` is still in its usual place.

## Image

Endpoint: `POST /v1/images/generations`

Model: primary `agnes-image-2.5-flash` (officially "comprehensively exceeds 2.1-flash"); `2.0-flash` / `2.1-flash` remain free and interchangeable.

Required:

- `model`
- `prompt`: text instruction for image generation or editing

Optional:

- `size`: output size such as `1024x768`
- `extra_body.image`: array of input image URLs for image-to-image
- `extra_body.response_format`: use `url` for image URLs

Prompt structure:

`[Subject] + [Scene / Environment] + [Style] + [Lighting] + [Composition] + [Quality Requirements]`

For image-to-image, state what should change and what must remain unchanged.

For non-English user prompts, translate to English before sending the request. Preserve visual specifics and constraints.

Response quirk: `data[].b64_json` may be an empty-string placeholder alongside `url` — filter out empty `b64_json` values before using them.

## Video — 2.5 / 2.5-flash (the schema this skill sends)

Create task endpoint: `POST /v1/videos`

Recommended result endpoint: `GET /agnesapi?video_id={video_id}&model_name=agnes-video-2.5(-flash)` — `model_name` is required for keyframe/reference results.

Legacy task endpoint: `GET /v1/videos/{task_id}`

Models: `agnes-video-2.5-flash` (limited-time free, 720P only) or `agnes-video-2.5` (paid per output second). The old `agnes-video-v2.0` and its schema were removed on 2026-10-21.

Docs: `https://wiki.agnes-ai.com/en/docs/agnes-video-25.md` and `agnes-video-25-flash.md`.

The video API is asynchronous. Create a task, then retrieve or poll by the returned `video_id` when present. Fall back to `task_id` only for older responses.

Use English prompts for video generation whenever possible. If the user prompt is not English, translate it to English first, preserving subject, action, scene, camera movement, lighting, style, and constraints.

Required:

- `model`: `agnes-video-2.5-flash` or `agnes-video-2.5`
- `prompt`: text description; use `<Picture N>` / `<Audio N>` / `<Video N>` placeholders in reference mode (`videos[]`/`audios[]` reference only on paid 2.5)
- `mode`: `text`, `keyframe`, or `reference` — omitting it returns `400 mode is required`

Optional:

- `seconds`: string `"4"`–`"12"`, default `"5"`
- `size`: `"720P"`, `"1080P"`, `"1K"`, `"2K"`; flash only accepts `"720P"`
- `aspect_ratio`: `21:9`, `16:9` (default), `4:3`, `1:1`, `3:4`, `9:16`; flash 16:9 actually outputs 1280x704
- `seed`: integer, reproducibility
- `first_frame` / `last_frame`: image URL(s) in keyframe mode, at least one
- `images`: image URL array in reference mode, flash ≤5, paid ≤8

Forbidden v2.0-era fields (`width`, `height`, `fps`, `num_frames`, `num_inference_steps`, `quality`) return `400 ... forbidden field`.

Completed URL lives in `metadata.url` of the retrieved task.

Common status values:

- `queued`
- `in_progress`
- `completed`
- `failed`

Recommended video defaults:

- Standard: `mode=text` (or `reference`/`keyframe` when images are involved), `seconds="5"`, `size="720P"`
- Reproducibility: set `seed`

2026-09-21 live note: `agnes-video-2.5-flash` returned `video_queue_full` on 12 consecutive retries across 15 minutes — the free promo queue is heavily congested; expect waits and treat it as best-effort.

Billing rule (paid 2.5): `Total video cost = output seconds × resolution unit price + input video seconds × resolution unit price + max(0, image count - 5) × $0.005`.

## Video — v2.0 (removed)

`agnes-video-v2.0` and its schema (`num_frames`, `width`, `height`, `frame_rate`, `mode: ti2vid|keyframes`, `extra_body.image`) were removed from `/v1/models` on 2026-10-21. Requests to it now fail; do not use this section's parameters. Historical reference only.

## Error Codes

- `400`: invalid request — includes `mode is required` / `<field> is a forbidden field` (2.5-series schema mismatch) and `invalid mode`
- `401`: unauthorized; check API key
- `404`: task not found
- `429` / `rate_limit_exceeded`: free-user rate limit; message says "Upgrade to a Token Plan" — wait ~60s and retry
- `video_queue_full`: 2.5-series queue saturated; retry later (non-fatal for other calls)
- `500`: server error
- `503`: service busy; retry later
