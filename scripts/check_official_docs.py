#!/usr/bin/env python3
"""Check Agnes AI local rules against the official /v1/models endpoint.

The authoritative source is the OpenAI-compatible /v1/models endpoint. The
official docs live on the Mintlify wiki (wiki.agnes-ai.com) with a public
llms.txt index; per-model doc pages (slug = model_id without dots, plus a
.md suffix) under the en/ and zh-Hans/ doc bases are used as a secondary
signal: each known model should have a live doc page that mentions its own
model ID.

Exit codes: 0=no issues, 1=WARNING/CRITICAL, 2=couldn't complete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWN_RULES = SKILL_ROOT / "templates" / "known_rules.json"
DEFAULT_BASE_URL = "https://apihub.agnes-ai.com"
DEFAULT_DOC_BASE_EN = "https://wiki.agnes-ai.com/en/docs"
DEFAULT_DOC_BASE_ZH = "https://wiki.agnes-ai.com/zh-Hans/docs"

CRITICAL = "CRITICAL"
WARNING = "WARNING"
INFO = "INFO"
_SEVERITY_ORDER = {CRITICAL: 0, WARNING: 1, INFO: 2}


def _get_api_key() -> Optional[str]:
    for name in ("AGNES_API_KEY", "AGNES_API_TOKEN", "APIHUB_AGNES_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def fetch_json(url: str, *, api_key: Optional[str] = None, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "agnes-skill-selfcheck/1.0"})
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON: {exc}") from exc


def fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "agnes-skill-selfcheck/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error: {exc}") from exc


class DocCache:
    """Tiny file cache for fetched doc pages."""

    def __init__(self, cache_dir: Path):
        self.dir = cache_dir

    def _path(self, url: str) -> Path:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.dir / f"{h}.txt"

    def get(self, url: str, ttl_hours: float = 24.0) -> Optional[str]:
        p = self._path(url)
        if not p.exists():
            return None
        if time.time() - p.stat().st_mtime > ttl_hours * 3600:
            return None
        return p.read_text(encoding="utf-8")

    def set(self, url: str, content: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path(url).write_text(content, encoding="utf-8")


def check_models(known_rules: Dict[str, Any], api_key: str, base_url: str) -> Tuple[List[Dict[str, str]], List[str]]:
    issues: List[Dict[str, str]] = []
    url = base_url.rstrip("/") + "/v1/models"
    try:
        data = fetch_json(url, api_key=api_key)
    except Exception as exc:
        issues.append({"severity": WARNING, "section": "models", "message": f"Could not fetch {url}: {exc}"})
        return issues, []

    remote_ids = []
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        for item in data["data"]:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                remote_ids.append(item["id"])

    if not remote_ids:
        issues.append({"severity": WARNING, "section": "models", "message": "/v1/models returned empty or unexpected structure."})
        return issues, []

    local_set = set(known_rules.get("models", []))
    remote_set = set(remote_ids)

    for model_id in sorted(local_set - remote_set):
        issues.append({
            "severity": CRITICAL,
            "section": "models",
            "message": f"Model '{model_id}' is in local rules but NOT in /v1/models. It may have been deprecated or renamed.",
        })
    for model_id in sorted(remote_set - local_set):
        issues.append({
            "severity": INFO,
            "section": "models",
            "message": f"Model '{model_id}' appears in /v1/models but is not in local rules. Consider adding it.",
        })

    return issues, remote_ids


def _model_doc_slug(model_id: str) -> str:
    """Agnes per-model doc URLs drop dots from the model ID (.md suffix appended by caller).

    Examples (against https://wiki.agnes-ai.com/en/docs):
      agnes-3.0-flash         -> agnes-30-flash.md
      agnes-image-2.5-flash   -> agnes-image-25-flash.md
      agnes-video-v2.0        -> agnes-video-v20.md
    """
    return model_id.replace(".", "")


def _check_model_doc_page(
    model_id: str,
    lang: str,
    base_url: str,
    cache: DocCache,
    force_refresh: bool,
) -> Optional[Dict[str, str]]:
    """Fetch one per-model doc page; return an issue dict if something is off."""
    slug = _model_doc_slug(model_id)
    # New wiki (Mintlify) serves clean markdown at <base>/<slug>.md; the bare
    # HTML path also exists but the .md form is the stable direct link.
    url = f"{base_url.rstrip('/')}/{slug}.md"
    text = cache.get(url, 24.0) if not force_refresh else None
    if text is None:
        try:
            text = fetch_text(url)
            cache.set(url, text)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {
                    "severity": WARNING,
                    "section": "docs",
                    "message": f"Model '{model_id}' doc page not found ({lang}): {url}",
                }
            return {
                "severity": WARNING,
                "section": "docs",
                "message": f"Could not fetch doc page for '{model_id}' ({lang}): HTTP {exc.code}",
            }
        except Exception as exc:
            return {
                "severity": WARNING,
                "section": "docs",
                "message": f"Could not fetch doc page for '{model_id}' ({lang}): {exc}",
            }
    # A live model page should mention its own model ID somewhere.
    if model_id not in text:
        return {
            "severity": INFO,
            "section": "docs",
            "message": f"Doc page for '{model_id}' ({lang}) loaded but does not contain the model ID; structure may have changed.",
        }
    return None


def check_docs(
    known_rules: Dict[str, Any],
    cache: DocCache,
    force_refresh: bool,
) -> List[Dict[str, str]]:
    """Check per-model doc pages for every model in known_rules."""
    issues: List[Dict[str, str]] = []
    urls = known_rules.get("source_urls", {})
    doc_base_en = urls.get("doc_base_en", DEFAULT_DOC_BASE_EN)
    doc_base_zh = urls.get("doc_base_zh", DEFAULT_DOC_BASE_ZH)

    for model_id in known_rules.get("models", []):
        for lang, base in (("en", doc_base_en), ("zh", doc_base_zh)):
            issue = _check_model_doc_page(model_id, lang, base, cache, force_refresh)
            if issue:
                issues.append(issue)

    return issues


def run_check(known_rules_path: Path, api_key: Optional[str], base_url: str, cache: DocCache, force_refresh: bool) -> List[Dict[str, str]]:
    known_rules = json.loads(known_rules_path.read_text(encoding="utf-8")) if known_rules_path.exists() else {}
    issues: List[Dict[str, str]] = []
    if api_key:
        model_issues, _ = check_models(known_rules, api_key, base_url)
        issues.extend(model_issues)
    else:
        issues.append({"severity": INFO, "section": "auth", "message": "No AGNES_API_KEY available; skipping /v1/models check."})
    issues.extend(check_docs(known_rules, cache, force_refresh))
    return issues


def run_api_check(
    known_rules_path: Path | str = DEFAULT_KNOWN_RULES,
    api_key: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
    cache_dir: Path | str | None = None,
    force_refresh: bool = False,
) -> List[Dict[str, str]]:
    """Public entry point used by agnes_api.py and other callers.

    Returns the issue list. Does not print or exit.
    """
    p = Path(known_rules_path)
    cache = DocCache(Path(cache_dir) if cache_dir else SKILL_ROOT / "output" / ".doc_cache")
    return run_check(p, api_key or _get_api_key(), base_url, cache, force_refresh)


def has_blocking_issue(issues: List[Dict[str, str]], fail_on: str = WARNING) -> bool:
    threshold = _SEVERITY_ORDER.get(fail_on, _SEVERITY_ORDER[WARNING])
    return any(_SEVERITY_ORDER.get(i["severity"], 9) <= threshold for i in issues)


def format_text(issues: List[Dict[str, str]]) -> str:
    if not issues:
        return "[OK] Local rules match official Agnes AI models/docs. No issues found."
    lines = [f"[CHECK] {len(issues)} issue(s):"]
    for issue in sorted(issues, key=lambda i: _SEVERITY_ORDER.get(i["severity"], 9)):
        lines.append(f"  [{issue['severity']}] ({issue['section']}) {issue['message']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Check Agnes AI local rules against official /v1/models")
    p.add_argument("--known-rules", default=str(DEFAULT_KNOWN_RULES))
    p.add_argument("--api-key", default=None, help="Agnes API key (defaults to env)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--force-refresh", action="store_true", help="Ignore doc cache")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--fail-on", choices=("critical", "warning"), default="warning")
    p.add_argument("--cache-dir", default=str(SKILL_ROOT / "output" / ".doc_cache"))
    return p


def main() -> int:
    args = build_parser().parse_args()
    api_key = args.api_key or _get_api_key()
    known_rules_path = Path(args.known_rules)
    cache = DocCache(Path(args.cache_dir))
    issues = run_check(known_rules_path, api_key, args.base_url, cache, args.force_refresh)

    if args.format == "json":
        print(json.dumps({
            "issues": issues,
            "counts": {
                "critical": sum(1 for i in issues if i["severity"] == CRITICAL),
                "warning": sum(1 for i in issues if i["severity"] == WARNING),
                "info": sum(1 for i in issues if i["severity"] == INFO),
            },
        }, ensure_ascii=False, indent=2))
    else:
        print(format_text(issues))

    return 1 if has_blocking_issue(issues, args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
