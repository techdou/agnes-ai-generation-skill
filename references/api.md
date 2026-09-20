# Agnes AI API Reference

Base host: `https://apihub.agnes-ai.com`

Authentication: `Authorization: Bearer YOUR_API_KEY`

Content type: `application/json`

Official doc index (llms.txt, all pages as markdown): `https://wiki.agnes-ai.com/llms.txt` — pricing at `https://wiki.agnes-ai.com/en/docs/pricing.md`, Chinese index at `https://wiki.agnes-ai.com/_llms/zh-hans.md`.

## Model Catalog (snapshot 2026-09-21)

Verified against `GET /v1/models` and the official pricing page. "Free" = current promotional price $0; promotions can end without notice.

| Family | Model | Billing |
| --- | --- | --- |
| Text | `agnes-2.0-flash` | still served; now a reasoning model (see Text notes) |
| Text | `agnes-2.5-flash` | free (promo) |
| Text | `agnes-2.5-pro` / `-alpha` / `-beta` | paid ($0.10–$0.45/M input) |
| Text | `agnes-3.0-flash` | free (promo) |
| Image | `agnes-image-2.0-flash` / `2.1-flash` / `2.5-flash` | free (promo, all resolutions + reference images) |
| Video | `agnes-video-v2.0` | free (promo) |
| Video | `agnes-video-2.5` | paid, per second (720P $0.025/s, 1080P/1K $0.040/s, 2K $0.055/s) |
| Video | `agnes-video-2.5-flash` | free (limited-time promo); queue often congested |

Deprecated: `agnes-1.5-flash` (removed from /v1/models).

Default picks in this skill: text `agnes-3.0-flash`, image `agnes-image-2.5-flash`, video `agnes-video-v2.0`.

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

Reasoning-model note (2026-09-21): `agnes-2.0-flash` and `agnes-2.5-flash` return a `reasoning_content` field and burn reasoning tokens against `max_tokens` first. With a small `max_tokens` the final `content` can come back empty — raise `max_tokens` (e.g. ≥100 for short answers, ≥800 for translations) instead of assuming the model is broken. `content` is still in its usual place.

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

## Video — v2.0 (the schema this skill sends)

Create task endpoint: `POST /v1/videos`

Recommended result endpoint: `GET /agnesapi?video_id={video_id}&model_name=agnes-video-v2.0`

Legacy task endpoint: `GET /v1/videos/{task_id}`

Model: `agnes-video-v2.0` (free)

The video API is asynchronous. Create a task, then retrieve or poll by the returned `video_id` when present. Fall back to `task_id` only for older responses.

Use English prompts for video generation whenever possible. If the user prompt is not English, translate it to English first, preserving subject, action, scene, camera movement, lighting, style, and constraints.

Required:

- `model`: `agnes-video-v2.0`
- `prompt`: text description of the video

Optional:

- `image`: input image URL or image URL array for image-to-video
- `mode`: generation mode such as `ti2vid` or `keyframes`
- `height`: integer, default `768`
- `width`: integer, default `1152`
- `num_frames`: integer, must be `<= 441` and satisfy `8n + 1`
- `num_inference_steps`: integer
- `seed`: integer
- `frame_rate`: number, supported range `1-60`
- `negative_prompt`: string
- `extra_body.image`: array for multi-image video or keyframe mode
- `extra_body.mode`: set to `keyframes` for keyframe animation

Common status values:

- `queued`
- `in_progress`
- `completed`
- `failed`

The create response may include both `task_id` and `video_id`; `video_id` is the recommended lookup identifier for new integrations. The completed response usually includes a video URL. In live responses this may appear as `video_url`, `url`, or `remixed_from_video_id`, plus `size`, `seconds`, and `usage.duration_seconds`.

Recommended video defaults:

- Standard: `width=1152`, `height=768`, `num_frames=121`, `frame_rate=24`
- Short smoke test: `num_frames=81`, `frame_rate=24`
- Reproducibility: set `seed`

## Video — 2.5 / 2.5-flash (new schema, NOT supported by this skill's script yet)

Docs: `https://wiki.agnes-ai.com/en/docs/agnes-video-25.md` and `agnes-video-25-flash.md`.

⚠ Incompatible with the v2.0 schema. Sending v2.0-style parameters (`num_frames`, `width`, `height`, `fps`, `num_inference_steps`, `quality`) returns `400 ... forbidden field`; omitting `mode` returns `400 mode is required`.

Create: `POST /v1/videos` with:

| Parameter | Type | Required | Notes |
| --- | --- | --- | --- |
| `model` | string | yes | `agnes-video-2.5` (paid per second) or `agnes-video-2.5-flash` (limited-time free, 720P only) |
| `prompt` | string | yes | use `<Picture N>` / `<Audio N>` / `<Video N>` placeholders in reference mode |
| `mode` | string | yes | `text`, `keyframe`, or `reference` |
| `seconds` | string | no | `"4"`–`"12"`, default `"5"` |
| `size` | string | no | `"720P"`, `"1080P"`, `"1K"`, `"2K"`; flash only accepts `"720P"` |
| `aspect_ratio` | string | no | `21:9`, `16:9` (default), `4:3`, `1:1`, `3:4`, `9:16`; flash 16:9 actually outputs 1280x704 |
| `seed` | integer | no | reproducibility |
| `first_frame` / `last_frame` | string | keyframe mode | image URL(s), at least one |
| `images` | string[] | reference mode | flash ≤5, paid ≤8; `videos[]`/`audios[]` reference only on paid 2.5 |

Retrieve (all modes; `model_name` required for keyframe/reference): `GET /agnesapi?video_id={video_id}&model_name=agnes-video-2.5(-flash)`. Completed URL lives in `metadata.url`.

2026-09-21 live note: `agnes-video-2.5-flash` returned `video_queue_full` on 12 consecutive retries across 15 minutes — the free promo queue is heavily congested; expect waits and treat it as best-effort.

## Error Codes

- `400`: invalid request — includes `mode is required` / `<field> is a forbidden field` (2.5-series schema mismatch) and `invalid mode`
- `401`: unauthorized; check API key
- `404`: task not found
- `429` / `rate_limit_exceeded`: free-user rate limit; message says "Upgrade to a Token Plan" — wait ~60s and retry
- `video_queue_full`: 2.5-series queue saturated; retry later (non-fatal for other calls)
- `500`: server error
- `503`: service busy; retry later
