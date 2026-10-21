#!/usr/bin/env python3
"""Small CLI for Agnes AI text, image, and video generation APIs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# Self-update guard: import the checker module in the same package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_official_docs as _cod  # noqa: E402

# ── .env fallback: load skill-local .env so the key survives PC switches ──
# shell-exported vars still win (override=False); dotenv missing → silent skip.
try:
    from dotenv import load_dotenv as _load_dotenv
    _skill_root = Path(__file__).resolve().parent.parent
    _env_path = _skill_root / ".env"
    if _env_path.is_file():
        _load_dotenv(_env_path, override=False)
except ImportError:
    pass


BASE_URL = "https://apihub.agnes-ai.com"
# 2026-10-21 sync: video moved to the 2.5 series — agnes-video-v2.0, agnes-2.0-flash
# and agnes-2.5-pro were removed from /v1/models. Video 2.5 uses its own parameter
# schema (mode/seconds/size; num_frames/width/height/fps forbidden). Default video
# model is the limited-time-free 2.5-flash; paid 2.5 bills per output second.
TEXT_MODEL = "agnes-3.0-flash"
IMAGE_MODEL = "agnes-image-2.5-flash"
VIDEO_MODEL = "agnes-video-2.5-flash"
VIDEO_PAID_MODEL = "agnes-video-2.5"
VIDEO_SIZES = ("720P", "1080P", "1K", "2K")
VIDEO_ASPECT_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
VIDEO_SECONDS = tuple(str(n) for n in range(4, 13))  # "4"-"12", string-typed
SIZE_RE = re.compile(r"^[1-9]\d*x[1-9]\d*$")


def _check_docs_if_requested(args: argparse.Namespace) -> None:
    """Non-blocking advisory check. Called when a command includes --check-docs."""
    if not getattr(args, "check_docs", False):
        return
    issues = _cod.run_api_check(force_refresh=getattr(args, "force_refresh_docs", False))
    critical = [i for i in issues if i["severity"] == _cod.CRITICAL]
    if critical:
        print("[DOC-CHECK] CRITICAL issue(s) detected:", file=sys.stderr)
        for i in critical:
            print(f"  [CRITICAL] ({i['section']}) {i['message']}", file=sys.stderr)
    elif issues:
        print(f"[DOC-CHECK] {len(issues)} advisory issue(s). Run `agnes_api.py check` for details.", file=sys.stderr)



def get_api_key() -> str:
    for name in ("AGNES_API_KEY", "AGNES_API_TOKEN", "APIHUB_AGNES_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "Missing API key. Set AGNES_API_KEY, AGNES_API_TOKEN, or APIHUB_AGNES_API_KEY."
    )


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {path}: {exc}") from exc


def request_text(method: str, path: str, payload: dict[str, Any] | None = None) -> str:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {path}: {exc}") from exc


def stream_summary(payload: dict[str, Any]) -> dict[str, Any]:
    raw = request_text("POST", "/v1/chat/completions", payload)
    event_count = 0
    done = False
    content_parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            done = True
        elif data:
            event_count += 1
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            try:
                delta = event["choices"][0].get("delta", {})
            except (KeyError, IndexError, TypeError, AttributeError):
                continue
            content = delta.get("content")
            if isinstance(content, str):
                content_parts.append(content)
    return {
        "type": "text-stream",
        "content": "".join(content_parts) or None,
        "events": event_count,
        "done": done,
        "raw_prefix": raw[:200],
    }


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parse_json_arg(name: str, value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for {name}: {exc.msg} at position {exc.pos}") from exc


def needs_english_translation(prompt: str) -> bool:
    return any(ord(ch) > 127 for ch in prompt)


def translate_prompt_to_english(prompt: str) -> str:
    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Translate the user's image/video generation prompt into fluent English. "
                    "Preserve all concrete visual details, style words, camera motion, lighting, "
                    "composition constraints, and negative instructions. Return only the English prompt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 800,
    }
    data = request_json("POST", "/v1/chat/completions", payload)
    try:
        translated = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Prompt translation failed: {json.dumps(data, ensure_ascii=False)}") from exc
    if not translated:
        raise SystemExit("Prompt translation failed: empty translated prompt")
    return translated


def prepare_generation_prompt(prompt: str, translate: bool = True) -> tuple[str, str | None]:
    if translate and needs_english_translation(prompt):
        translated = translate_prompt_to_english(prompt)
        return translated, translated
    return prompt, None


def extract_text_content(data: dict[str, Any]) -> str | None:
    try:
        content = data["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    return content if isinstance(content, str) else None


def output_result(
    result_type: str,
    raw: dict[str, Any],
    *,
    prompt_used: str | None = None,
    translated_prompt: str | None = None,
    urls: list[str] | None = None,
    status: str | None = None,
    next_steps: list[str] | None = None,
    raw_only: bool = False,
) -> None:
    if raw_only:
        print_json(raw)
        return
    summary: dict[str, Any] = {"type": result_type}
    if status:
        summary["status"] = status
    if urls:
        summary["urls"] = urls
    if prompt_used:
        summary["prompt_used"] = prompt_used
    if translated_prompt:
        summary["translated_prompt"] = translated_prompt
    if next_steps:
        summary["next_steps"] = next_steps
    summary["raw"] = raw
    print_json(summary)


def extract_image_urls(data: dict[str, Any]) -> list[str]:
    urls = []
    if isinstance(data.get("url"), str):
        urls.append(data["url"])
    if isinstance(data.get("image_url"), str):
        urls.append(data["image_url"])
    if isinstance(data.get("data"), list):
        for item in data["data"]:
            if isinstance(item, dict):
                for key in ("url", "image_url"):
                    if isinstance(item.get(key), str):
                        urls.append(item[key])
    return urls


def extract_video_urls(data: dict[str, Any]) -> list[str]:
    urls = []
    for key in ("video_url", "url", "remixed_from_video_id"):
        value = data.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
    # Video 2.5 series puts the completed URL in metadata.url.
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("url")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
    if isinstance(data.get("data"), list):
        for item in data["data"]:
            if isinstance(item, dict):
                urls.extend(extract_video_urls(item))
    return list(dict.fromkeys(urls))


def video_lookup_id(data: dict[str, Any]) -> tuple[str | None, str | None]:
    video_id = data.get("video_id")
    if isinstance(video_id, str) and video_id:
        return video_id, "video_id"
    for key in ("task_id", "id"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value, "task_id"
    return None, None


def retrieve_video(identifier: str, model_name: str | None = VIDEO_MODEL) -> dict[str, Any]:
    if identifier.startswith("video_"):
        query = {"video_id": identifier}
        if model_name:
            query["model_name"] = model_name
        return request_json("GET", "/agnesapi?" + urllib.parse.urlencode(query))
    return request_json("GET", f"/v1/videos/{urllib.parse.quote(identifier, safe='')}")


def validate_size(value: str | None, name: str = "size") -> None:
    if value and not SIZE_RE.match(value):
        raise SystemExit(f"Invalid {name}: {value}. Expected WIDTHxHEIGHT, for example 1024x768.")


def validate_video_args(
    model: str | None,
    seconds: str | None,
    size: str | None,
    aspect_ratio: str | None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    images: list[str] | None = None,
    mode: str | None = None,
) -> str:
    """Validate the Video 2.5 parameter schema and return the resolved mode."""
    model = model or VIDEO_MODEL
    is_flash = "flash" in model
    if seconds is not None and seconds not in VIDEO_SECONDS:
        raise SystemExit(f'Invalid --seconds: {seconds!r}. Expected "4"-"12" (default "5").')
    if size is not None and size not in VIDEO_SIZES:
        raise SystemExit(f"Invalid --size: {size!r}. Expected one of {', '.join(VIDEO_SIZES)}.")
    if is_flash and size not in (None, "720P"):
        raise SystemExit(
            f"{model} only supports size 720P; drop --size or switch to the paid {VIDEO_PAID_MODEL}."
        )
    if aspect_ratio is not None and aspect_ratio not in VIDEO_ASPECT_RATIOS:
        raise SystemExit(f"Invalid --aspect-ratio: {aspect_ratio!r}. Expected one of {', '.join(VIDEO_ASPECT_RATIOS)}.")
    mode = mode or ("keyframe" if (first_frame or last_frame) else ("reference" if images else "text"))
    if mode == "keyframe" and not (first_frame or last_frame):
        raise SystemExit("Keyframe mode requires --first-frame and/or --last-frame.")
    if mode == "reference" and not images:
        raise SystemExit("Reference mode requires at least one --image.")
    if mode == "reference" and images:
        limit = 5 if is_flash else 8
        if len(images) > limit:
            raise SystemExit(f"{model} accepts at most {limit} reference images, got {len(images)}.")
    if mode == "text" and (first_frame or last_frame or images):
        raise SystemExit("Text mode does not accept --image/--first-frame/--last-frame; use keyframe or reference mode.")
    return mode


def cmd_check(args: argparse.Namespace) -> None:
    """Run the official-doc sync check."""
    issues = _cod.run_api_check(force_refresh=args.force_refresh)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "issues": issues,
                    "counts": {
                        "critical": sum(1 for i in issues if i["severity"] == _cod.CRITICAL),
                        "warning": sum(1 for i in issues if i["severity"] == _cod.WARNING),
                        "info": sum(1 for i in issues if i["severity"] == _cod.INFO),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(_cod.format_text(issues))
    if _cod.has_blocking_issue(issues, args.fail_on):
        raise SystemExit(1)


def cmd_text(args: argparse.Namespace) -> None:
    _check_docs_if_requested(args)
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.prompt})
    payload: dict[str, Any] = {
        "model": TEXT_MODEL,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.top_p is not None:
        payload["top_p"] = args.top_p
    if args.stream:
        payload["stream"] = True
    if args.tools_json:
        payload["tools"] = parse_json_arg("--tools-json", args.tools_json)
    if args.tool_choice_json:
        payload["tool_choice"] = parse_json_arg("--tool-choice-json", args.tool_choice_json)
    if args.stream:
        print_json(stream_summary(payload))
    else:
        data = request_json("POST", "/v1/chat/completions", payload)
        content = extract_text_content(data)
        wrapped = {
            "type": "text",
            "content": content,
            "raw": data,
        }
        print_json(data if args.raw else wrapped)


def cmd_image(args: argparse.Namespace) -> None:
    _check_docs_if_requested(args)
    validate_size(args.size)
    prompt, translated_prompt = prepare_generation_prompt(args.prompt, not args.no_translate_prompt)
    payload: dict[str, Any] = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
    }
    if args.size:
        payload["size"] = args.size
    extra: dict[str, Any] = {"response_format": "url"}
    if args.image:
        extra["image"] = args.image
    if extra:
        payload["extra_body"] = extra
    data = request_json("POST", "/v1/images/generations", payload)
    urls = extract_image_urls(data)
    output_result(
        "image-to-image" if args.image else "text-to-image",
        data,
        prompt_used=prompt,
        translated_prompt=translated_prompt,
        urls=urls,
        raw_only=args.raw,
    )


def video_payload(args: argparse.Namespace) -> dict[str, Any]:
    mode = validate_video_args(
        args.model,
        args.seconds,
        args.size,
        args.aspect_ratio,
        first_frame=args.first_frame,
        last_frame=args.last_frame,
        images=args.image,
        mode=args.mode,
    )
    prompt, translated_prompt = prepare_generation_prompt(args.prompt, not args.no_translate_prompt)
    args._prompt_used = prompt
    args._translated_prompt = translated_prompt
    payload: dict[str, Any] = {
        "model": args.model or VIDEO_MODEL,
        "prompt": prompt,
        "mode": mode,
        "size": args.size,
        "seconds": args.seconds,
    }
    if args.aspect_ratio:
        payload["aspect_ratio"] = args.aspect_ratio
    if args.seed is not None:
        payload["seed"] = args.seed
    if mode == "keyframe":
        if args.first_frame:
            payload["first_frame"] = args.first_frame
        if args.last_frame:
            payload["last_frame"] = args.last_frame
    elif mode == "reference":
        payload["images"] = args.image
    return payload


def poll_video(identifier: str, timeout: int, interval: int) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = retrieve_video(identifier)
        if last.get("error"):
            raise SystemExit(f"Video {identifier} returned error: {json.dumps(last, ensure_ascii=False)}")
        status = str(last.get("status", "")).lower()
        progress = last.get("progress")
        if status:
            print(f"video {identifier}: status={status} progress={progress}", file=sys.stderr)
        if status in {"completed", "failed"}:
            return last
        time.sleep(interval)
    raise SystemExit(f"Timed out waiting for video {identifier}. Last response: {json.dumps(last)}")


def cmd_video(args: argparse.Namespace) -> None:
    _check_docs_if_requested(args)
    created = request_json("POST", "/v1/videos", video_payload(args))
    if not args.poll:
        identifier, id_kind = video_lookup_id(created)
        next_steps = []
        if identifier:
            next_steps.append(f"python scripts/agnes_api.py video-get {identifier}")
            next_steps.append(f"python scripts/agnes_api.py video-get {identifier}  # repeat until status is completed")
        output_result(
            "video-task",
            created,
            prompt_used=getattr(args, "_prompt_used", None),
            translated_prompt=getattr(args, "_translated_prompt", None),
            status=str(created.get("status", "")) if created.get("status") is not None else None,
            next_steps=next_steps,
            raw_only=args.raw,
        )
        if id_kind == "task_id":
            print("warning: create response did not include video_id; falling back to legacy task_id lookup", file=sys.stderr)
        return
    identifier, id_kind = video_lookup_id(created)
    if not identifier:
        raise SystemExit(f"Video create response did not include video_id, task_id, or id: {json.dumps(created)}")
    if id_kind == "task_id":
        print("warning: create response did not include video_id; falling back to legacy task_id lookup", file=sys.stderr)
    data = poll_video(identifier, args.timeout, args.interval)
    urls = extract_video_urls(data)
    output_result(
        "video-result",
        data,
        prompt_used=getattr(args, "_prompt_used", None),
        translated_prompt=getattr(args, "_translated_prompt", None),
        urls=urls,
        status=str(data.get("status", "")) if data.get("status") is not None else None,
        raw_only=args.raw,
    )


def cmd_video_get(args: argparse.Namespace) -> None:
    _check_docs_if_requested(args)
    data = retrieve_video(args.identifier, None if args.no_model_name else args.model_name)
    urls = extract_video_urls(data)
    output_result(
        "video-result",
        data,
        urls=urls,
        status=str(data.get("status", "")) if data.get("status") is not None else None,
        next_steps=[] if urls else [f"python scripts/agnes_api.py video-get {args.identifier}"],
        raw_only=args.raw,
    )
    if data.get("error"):
        raise SystemExit(1)


def require_ok(name: str, data: dict[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise SystemExit(f"{name} response missing {missing}: {json.dumps(data)}")
    print(f"{name}: ok")


def require_video_ok(name: str, data: dict[str, Any], completed: bool = False) -> None:
    require_ok(name, data, ("id", "status"))
    if data.get("error"):
        raise SystemExit(f"{name} returned error: {json.dumps(data, ensure_ascii=False)}")
    status = str(data.get("status", "")).lower()
    if status == "failed":
        raise SystemExit(f"{name} failed: {json.dumps(data, ensure_ascii=False)}")
    if completed and status != "completed":
        raise SystemExit(f"{name} did not complete: {json.dumps(data, ensure_ascii=False)}")
    if completed and not extract_video_urls(data):
        raise SystemExit(f"{name} completed without a video URL: {json.dumps(data, ensure_ascii=False)}")


def check_tool_call(name: str, data: dict[str, Any], strict: bool = False) -> None:
    try:
        tool_calls = data["choices"][0]["message"].get("tool_calls")
    except (KeyError, IndexError, TypeError, AttributeError):
        tool_calls = None
    if not tool_calls:
        message = f"{name}: request accepted, but response did not include tool_calls"
        if strict:
            raise SystemExit(f"{message}: {json.dumps(data, ensure_ascii=False)}")
        print(message, file=sys.stderr)
        return
    print(f"{name}: ok")


def extract_image_url(data: dict[str, Any]) -> str:
    candidates = extract_image_urls(data)
    if not candidates:
        raise SystemExit(f"Could not find image URL in response: {json.dumps(data, ensure_ascii=False)}")
    return candidates[0]


def create_video_case(name: str, payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    created = request_json("POST", "/v1/videos", payload)
    require_video_ok(f"{name}-create", created)
    identifier, id_kind = video_lookup_id(created)
    if not identifier:
        raise SystemExit(f"{name}-create response missing video_id/task_id/id: {json.dumps(created, ensure_ascii=False)}")
    if id_kind == "task_id":
        print(f"{name}-create: warning: falling back to legacy task_id lookup", file=sys.stderr)
    retrieved = (
        poll_video(identifier, args.video_timeout, args.video_interval)
        if args.poll_video
        else retrieve_video(identifier)
    )
    require_video_ok(f"{name}-get", retrieved, completed=args.poll_video)
    return {"create": created, "get": retrieved}


VIDEO_CASES = ("text-to-video", "image-to-video", "multi-image", "keyframes")


def cmd_smoke_test(args: argparse.Namespace) -> None:
    _check_docs_if_requested(args)
    validate_size(args.image_size, "image-size")
    validate_video_args(None, args.video_seconds, args.video_size, None)
    text = request_json(
        "POST",
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: Agnes text ok"}],
            "max_tokens": 20,
            "temperature": 0,
        },
    )
    require_ok("text", text, ("choices",))

    text_stream = stream_summary(
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: Agnes stream ok"}],
            "max_tokens": 20,
            "temperature": 0,
            "stream": True,
        }
    )
    if text_stream["events"] < 1 and not text_stream["done"]:
        raise SystemExit(f"text-stream response did not look like SSE: {json.dumps(text_stream)}")
    print("text-stream: ok")

    text_tools = request_json(
        "POST",
        "/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "messages": [{"role": "user", "content": "Use the get_test_value tool."}],
            "max_tokens": 128,
            "temperature": 0,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_test_value",
                        "description": "Return a deterministic smoke test value.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "test label"}
                            },
                            "required": ["label"],
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "get_test_value"}},
        },
    )
    check_tool_call("text-tools", text_tools, strict=args.strict_tools)

    image_text = request_json(
        "POST",
        "/v1/images/generations",
        {
            "model": IMAGE_MODEL,
            "prompt": "A simple red square icon centered on a white background",
            "size": args.image_size,
            "extra_body": {"response_format": "url"},
        },
    )
    require_ok("image-text-to-image", image_text, ("data",))
    generated_image_url = extract_image_url(image_text)

    image_edit = None
    edited_image_url = None
    selected_cases = set(args.video_case or [])
    needs_second_image = bool(selected_cases.intersection({"multi-image", "keyframes"}))
    if args.include_image_edit or needs_second_image:
        image_edit = request_json(
            "POST",
            "/v1/images/generations",
            {
                "model": IMAGE_MODEL,
                "prompt": "Turn this into a clean blue square icon while preserving the centered composition",
                "size": args.image_size,
                "extra_body": {"image": [generated_image_url], "response_format": "url"},
            },
        )
        require_ok("image-to-image", image_edit, ("data",))
        edited_image_url = extract_image_url(image_edit)

    video_common = {
        "model": VIDEO_MODEL,
        "size": args.video_size,
        "seconds": args.video_seconds,
    }
    video_results = {}
    if "text-to-video" in selected_cases:
        video_results["text_to_video"] = create_video_case(
            "video-text-to-video",
            {
                **video_common,
                "mode": "text",
                "prompt": "A simple cinematic shot of a red square gently moving on a white background",
            },
            args,
        )
    if "image-to-video" in selected_cases:
        video_results["image_to_video"] = create_video_case(
            "video-image-to-video",
            {
                **video_common,
                "mode": "reference",
                "prompt": "<Picture 1> Animate the icon with subtle floating motion, stable centered composition",
                "images": [generated_image_url],
            },
            args,
        )
    if "multi-image" in selected_cases:
        if not edited_image_url:
            raise SystemExit("multi-image test requires an edited image URL")
        video_results["multi_image"] = create_video_case(
            "video-multi-image",
            {
                **video_common,
                "mode": "reference",
                "prompt": "<Picture 1> smoothly transforms into <Picture 2>, stable centered composition",
                "images": [generated_image_url, edited_image_url],
            },
            args,
        )
    if "keyframes" in selected_cases:
        if not edited_image_url:
            raise SystemExit("keyframes test requires an edited image URL")
        video_results["keyframes"] = create_video_case(
            "video-keyframes",
            {
                **video_common,
                "mode": "keyframe",
                "prompt": "Create a smooth keyframe transition between the two icons, stable centered composition",
                "first_frame": generated_image_url,
                "last_frame": edited_image_url,
            },
            args,
        )
    print_json(
        {
            "text": text,
            "text_stream": text_stream,
            "text_tools": text_tools,
            "image_text_to_image": image_text,
            "image_to_image": image_edit,
            "video": video_results,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call Agnes AI generation APIs.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run official-doc /v1/models sync check.")
    check.add_argument("--force-refresh", action="store_true", help="Ignore doc cache and re-fetch.")
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--fail-on", choices=("critical", "warning"), default="warning")
    check.set_defaults(func=cmd_check)

    text = sub.add_parser("text", help="Create a chat completion.")
    text.add_argument("--prompt", required=True)
    text.add_argument("--system")
    text.add_argument("--temperature", type=float, default=0.7)
    text.add_argument("--top-p", type=float)
    text.add_argument("--max-tokens", type=int, default=1024)
    text.add_argument("--stream", action="store_true")
    text.add_argument("--tools-json", help="JSON array for OpenAI-compatible tool definitions.")
    text.add_argument("--tool-choice-json", help="JSON object/string for OpenAI-compatible tool_choice.")
    text.add_argument("--raw", action="store_true", help="Print the raw provider response.")
    text.add_argument("--check-docs", action="store_true", help="Run non-blocking official-doc check before request.")
    text.add_argument("--force-refresh-docs", action="store_true", help="Force refresh doc cache for --check-docs.")
    text.set_defaults(func=cmd_text)

    image = sub.add_parser("image", help="Generate or edit an image.")
    image.add_argument("--prompt", required=True)
    image.add_argument("--size", default="1024x768")
    image.add_argument("--image", action="append", help="Input image URL. Repeat for multiple images.")
    image.add_argument(
        "--no-translate-prompt",
        action="store_true",
        help="Do not translate non-English prompts before sending to the image API.",
    )
    image.add_argument("--raw", action="store_true", help="Print the raw provider response.")
    image.add_argument("--check-docs", action="store_true", help="Run non-blocking official-doc check before request.")
    image.add_argument("--force-refresh-docs", action="store_true", help="Force refresh doc cache for --check-docs.")
    image.set_defaults(func=cmd_image)

    video = sub.add_parser("video", help="Create a video task (Video 2.5 schema).")
    video.add_argument("--prompt", required=True)
    video.add_argument(
        "--model",
        help=f"Default {VIDEO_MODEL} (limited-time free). {VIDEO_PAID_MODEL} bills per output second.",
    )
    video.add_argument("--mode", choices=("text", "keyframe", "reference"), help="Default: auto (text, or keyframe/reference when frames/images are given).")
    video.add_argument("--image", action="append", help="Reference image URL for reference mode. Repeat for multiple (flash <=5, paid <=8).")
    video.add_argument("--first-frame", help="First frame image URL for keyframe mode.")
    video.add_argument("--last-frame", help="Last frame image URL for keyframe mode.")
    video.add_argument("--seconds", default="5", help='Output length, "4"-"12" (default "5").')
    video.add_argument("--size", default="720P", choices=VIDEO_SIZES, help="Flash accepts 720P only; higher resolutions bill on the paid model.")
    video.add_argument("--aspect-ratio", choices=VIDEO_ASPECT_RATIOS, help="Default 16:9 (flash 16:9 actually outputs 1280x704).")
    video.add_argument("--seed", type=int)
    video.add_argument(
        "--no-translate-prompt",
        action="store_true",
        help="Do not translate non-English prompts before sending to the video API.",
    )
    video.add_argument("--poll", action="store_true")
    video.add_argument("--timeout", type=int, default=900)
    video.add_argument("--interval", type=int, default=10)
    video.add_argument("--raw", action="store_true", help="Print the raw provider response.")
    video.add_argument("--check-docs", action="store_true", help="Run non-blocking official-doc check before request.")
    video.add_argument("--force-refresh-docs", action="store_true", help="Force refresh doc cache for --check-docs.")
    video.set_defaults(func=cmd_video)

    video_get = sub.add_parser("video-get", help="Retrieve a video result by video_id, or by legacy task_id.")
    video_get.add_argument("identifier", help="Prefer video_id. Legacy task_id is still accepted.")
    video_get.add_argument("--model-name", default=VIDEO_MODEL, help="Model name for video_id result lookup (required for 2.5 keyframe/reference results).")
    video_get.add_argument("--no-model-name", action="store_true", help="Do not pass model_name for video_id lookup.")
    video_get.add_argument("--raw", action="store_true", help="Print the raw provider response.")
    video_get.add_argument("--check-docs", action="store_true", help="Run non-blocking official-doc check before request.")
    video_get.add_argument("--force-refresh-docs", action="store_true", help="Force refresh doc cache for --check-docs.")
    video_get.set_defaults(func=cmd_video_get)

    smoke = sub.add_parser("smoke-test", help="Run live text, image, and video API tests.")
    smoke.add_argument("--image-size", default="1024x768")
    smoke.add_argument("--video-size", default="720P", choices=VIDEO_SIZES)
    smoke.add_argument("--video-seconds", default="5", help='Video length for video cases, "4"-"12".')
    smoke.add_argument("--include-image-edit", action="store_true", help="Also test image-to-image editing.")
    smoke.add_argument("--strict-tools", action="store_true", help="Fail if the tool-calling response has no tool_calls.")
    smoke.add_argument("--poll-video", action="store_true")
    smoke.add_argument("--video-timeout", type=int, default=900)
    smoke.add_argument("--video-interval", type=int, default=10)
    smoke.add_argument(
        "--video-case",
        action="append",
        choices=VIDEO_CASES,
        help="Video case to test. Repeat to test multiple cases. Omit to skip video creation.",
    )
    smoke.add_argument("--check-docs", action="store_true", help="Run non-blocking official-doc check before request.")
    smoke.add_argument("--force-refresh-docs", action="store_true", help="Force refresh doc cache for --check-docs.")
    smoke.set_defaults(func=cmd_smoke_test)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
