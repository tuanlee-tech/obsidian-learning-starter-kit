#!/usr/bin/env python3
"""Cross-platform helper for the NotebookLM Study Antigravity plugin.

Uses Python 3 standard library only (Windows / macOS / Linux compatible).
Supports all 4 official NotebookLM MCP `source_add` source types:
  - url   (Web pages & YouTube URLs)
  - file  (43 official local extensions: PDF, DOCX, PPTX, MD, TXT, CSV, EPUB, images, audio/video)
  - drive (Google Docs / Slides / Sheets / Drive PDF links or `drive:<type>:<id>`)
  - text  (inline pasted text sources via `#### 📝 Nguồn Text: <Title>` or `text:<Title> | <Content>`)

Subcommands:
  check-prompt
  parse-day <schedule_path> <day_number> [--include-merged]
  compose-prompt <schedule_path> <day_number> [--out <output_path>]
  check-sources [--file <schedule_path> [--day <day_number>]] [--skip-urls]
  check-urls [--file <schedule_path> [--day <day_number>]] [url ...]
  check-week <schedule_path> [--skip-urls]
  check-env [--live]
  state-get
  state-set --notebook-id ID --title TITLE [--conversation-id CID]
            [--schedule PATH] [--day N] [--raw-file PATH] [--url URL]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure UTF-8 stdout/stderr on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nlm_connect  # noqa: E402

PLUGIN_DIR = SCRIPT_DIR.parent
VAULT_ROOT = PLUGIN_DIR.parent.parent.parent
PROMPT_FILE = VAULT_ROOT / "docs" / "notebooklm-system-prompt.md"
CLAUDE_FILE = VAULT_ROOT / "CLAUDE.md"
SOURCES_DIR = VAULT_ROOT / "sources"
STATE_FILE = PLUGIN_DIR / ".state" / "active-notebook.json"

MAX_BASE_PROMPT_CHARS = 8350
MAX_SCOPE_CHARS = 1400
MAX_MERGED_CHARS = 10000
MERGE_HEADER = "\n\n---\n\n## THIẾT LẬP BUỔI HỌC HÔM NAY\n\n"
SYSTEM_MARKER = "# SYSTEM INSTRUCTION"
MIN_NLM_VERSION = "0.16.5"

# Exact 43 official extensions accepted by `notebooklm-mcp-cli` `source_add(source_type="file")`
OFFICIAL_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf", ".txt", ".md", ".docx", ".csv", ".pptx", ".epub",
        ".avif", ".bmp", ".gif", ".heic", ".heif", ".ico", ".jp2", ".jpe",
        ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
        ".3g2", ".3gp", ".aac", ".aif", ".aifc", ".aiff", ".amr", ".au",
        ".avi", ".cda", ".m4a", ".mid", ".mp3", ".mp4", ".mpeg", ".ogg",
        ".opus", ".ra", ".ram", ".snd", ".wav", ".wma",
    }
)

VALID_DRIVE_DOC_TYPES: frozenset[str] = frozenset({"doc", "slides", "sheets", "pdf"})

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)


def read_text_normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def load_base_prompt(prompt_path: Path = PROMPT_FILE) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found: {prompt_path}")
    text = read_text_normalized(prompt_path)
    idx = text.find(SYSTEM_MARKER)
    if idx == -1:
        raise ValueError(f"Marker '{SYSTEM_MARKER}' not found in {prompt_path}")
    return text[idx:].strip()


def slugify_vi(text: str, max_len: int = 64) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.lower()
    ascii_only = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    if len(ascii_only) > max_len:
        ascii_only = ascii_only[:max_len].rstrip("-")
    return ascii_only or "lesson"


def resolve_vault_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    candidate = VAULT_ROOT / p
    return candidate if candidate.exists() else (VAULT_ROOT / p)


def extract_day_sections(text: str) -> list[dict[str, Any]]:
    """Support both Core Trunk (## Ngày N) and Track 1-6 (### 📆 NGÀY N) formats."""
    lines = text.split("\n")
    matches: list[tuple[int, int, int, str]] = []

    core_re = re.compile(r"^(#{2})\s+(?:✅\s*)?Ngày\s+(\d+)\b(.*)$", re.IGNORECASE)
    track_re = re.compile(r"^(#{3})\s+(?:📆\s*|✅\s*)?NGÀY\s+(\d+)\b(.*)$", re.IGNORECASE)

    for idx, line in enumerate(lines):
        m = track_re.match(line) or core_re.match(line)
        if m:
            level = len(m.group(1))
            day_num = int(m.group(2))
            matches.append((idx, level, day_num, line.strip()))

    sections: list[dict[str, Any]] = []
    for start_idx, level, day_num, heading in matches:
        end_idx = len(lines)
        for j in range(start_idx + 1, len(lines)):
            heading_m = re.match(r"^(#{1,6})\s+", lines[j])
            if heading_m and len(heading_m.group(1)) <= level:
                end_idx = j
                break
        body = "\n".join(lines[start_idx:end_idx]).strip()
        sections.append(
            {
                "day": day_num,
                "heading": heading,
                "format": "track" if level == 3 else "core-trunk",
                "body": body,
            }
        )
    return sections


def derive_prefix_from_filename(schedule_path: Path, day_num: int) -> str:
    stem = schedule_path.stem.lower()
    m_track = re.search(r"track-(\d+)-tuan-(\d+)", stem)
    if m_track:
        return f"Track {m_track.group(1)} - W{m_track.group(2)}D{day_num}"
    m_week = re.search(r"tuan-(\d+)", stem)
    if m_week:
        return f"W{m_week.group(1)}D{day_num}"
    return f"Day{day_num}"


def derive_raw_prefix(schedule_path: Path, day_num: int) -> str:
    stem = schedule_path.stem.lower()
    m_track = re.search(r"track-(\d+)-tuan-(\d+)", stem)
    if m_track:
        return f"track{m_track.group(1)}-w{m_track.group(2)}d{day_num}"
    m_week = re.search(r"tuan-(\d+)", stem)
    if m_week:
        return f"w{m_week.group(1)}d{day_num}"
    return f"day{day_num}"


def parse_drive_url(url: str) -> dict[str, Any] | None:
    """Detect Google Docs / Slides / Sheets / Drive file links and extract document_id."""
    patterns = [
        (r"https?://docs\.google\.com/document/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)", "doc"),
        (r"https?://docs\.google\.com/presentation/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)", "slides"),
        (r"https?://docs\.google\.com/spreadsheets/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)", "sheets"),
        (r"https?://drive\.google\.com/file/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)", "pdf"),
        (r"https?://drive\.google\.com/open\?[^#\s]*\bid=([a-zA-Z0-9_-]+)", "pdf"),
    ]
    for pat, doc_type in patterns:
        m = re.search(pat, url)
        if m:
            return {
                "type": "drive",
                "document_id": m.group(1),
                "doc_type": doc_type,
                "url": url,
            }
    return None


def _looks_like_local_file(token: str) -> bool:
    if not token or token.startswith(("http://", "https://", "drive:", "text:")):
        return False
    ext = Path(token).suffix.lower()
    return ext in OFFICIAL_FILE_EXTENSIONS


def extract_sources(body: str) -> list[dict[str, Any]]:
    """Extract all 4 official NotebookLM source types from a day section."""
    # Locate the Sources subsection (supports IT & Universal Starter-Kit headings)
    src_sec_re = re.compile(
        r"(?:^|\n)(#{3,4})\s+(?:🔗\s*)?(?:Tài liệu official|Nguồn tài liệu|Nguồn nạp vào NotebookLM)[^\n]*\n(.*?)(?=\n#{2,4}\s+(?!📝\s*Nguồn Text)|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    m_sec = src_sec_re.search(body)
    src_block = m_sec.group(2) if m_sec else body

    sources: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    def add_source(item: dict[str, Any], dedup_key: str) -> None:
        k = (item["type"], dedup_key)
        if k not in seen_keys:
            seen_keys.add(k)
            sources.append(item)

    # 1. Inline text sources via `#### 📝 Nguồn Text: <Title>` + fenced block
    text_block_re = re.compile(
        r"#{4,5}\s*📝?\s*Nguồn\s+Text\s*:\s*([^\n]+)\n```[^\n]*\n(.*?)\n```",
        re.DOTALL | re.IGNORECASE,
    )
    for m in text_block_re.finditer(src_block):
        title = m.group(1).strip()
        content = m.group(2).strip()
        if title and content:
            add_source({"type": "text", "title": title, "text": content}, f"text:{title}")

    # Remove captured inline text fenced blocks before scanning list lines
    scan_text = text_block_re.sub("", src_block)

    # 2. Inline single-line `text:<Title> | <Content>` entries
    for m in re.finditer(r"^\s*[-*\d.]+\s*`?text:([^|\n]+)\|([^\n`]+)`?", scan_text, re.MULTILINE):
        title = m.group(1).strip()
        content = m.group(2).strip()
        if title and content:
            add_source({"type": "text", "title": title, "text": content}, f"text:{title}")

    # 3. Explicit `drive:<doc|slides|sheets|pdf>:<document_id>` entries
    for m in re.finditer(r"\bdrive:(doc|slides|sheets|pdf):([a-zA-Z0-9_-]{8,})\b", scan_text, re.IGNORECASE):
        doc_type = m.group(1).lower()
        doc_id = m.group(2)
        add_source({"type": "drive", "document_id": doc_id, "doc_type": doc_type}, doc_id)

    # 4. Explicit `file:<path>` entries
    for m in re.finditer(r"(?:^|[\s(`])file:([^\s`)\]>\"']+)", scan_text, re.IGNORECASE):
        raw_p = m.group(1).strip()
        abs_p = resolve_vault_path(raw_p)
        ext = abs_p.suffix.lower()
        add_source(
            {
                "type": "file",
                "raw_path": raw_p,
                "file_path": str(abs_p),
                "extension": ext,
                "ext_valid": ext in OFFICIAL_FILE_EXTENSIONS,
                "exists": abs_p.exists() and abs_p.is_file(),
            },
            str(abs_p).lower(),
        )

    # 5. URLs (classify Google Drive URLs as `drive`, others as `url`)
    for raw_url in re.findall(r"https?://[^\s`)\]>\"']+", scan_text):
        cleaned = raw_url.rstrip(".,;:")
        drive_info = parse_drive_url(cleaned)
        if drive_info:
            add_source(drive_info, drive_info["document_id"])
        else:
            is_yt = ("youtube.com" in cleaned.lower()) or ("youtu.be" in cleaned.lower())
            add_source({"type": "url", "url": cleaned, "is_youtube": is_yt}, cleaned)

    # 6. Local file paths in Markdown links `[label](sources/foo.pdf)` or backticks `` `sources/foo.pdf` ``
    md_link_paths = re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", scan_text)
    backtick_paths = re.findall(r"`([^`\n]+)`", scan_text)
    for candidate in [*md_link_paths, *backtick_paths]:
        token = candidate.strip()
        if _looks_like_local_file(token):
            abs_p = resolve_vault_path(token)
            ext = abs_p.suffix.lower()
            add_source(
                {
                    "type": "file",
                    "raw_path": token,
                    "file_path": str(abs_p),
                    "extension": ext,
                    "ext_valid": ext in OFFICIAL_FILE_EXTENSIONS,
                    "exists": abs_p.exists() and abs_p.is_file(),
                },
                str(abs_p).lower(),
            )

    return sources


def parse_day_section(schedule_path: Path, section: dict[str, Any]) -> dict[str, Any]:
    body = section["body"]
    heading = section["heading"]
    day_num = section["day"]

    completed = ("✅" in heading) or ("Đã hoàn thành" in heading)

    topic = re.sub(
        r"^#{2,3}\s+(?:✅\s*|📆\s*)?Ngày\s+\d+\s*[—:\-–]?\s*",
        "",
        heading,
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\*\(Đã hoàn thành.*?\)\*", "", topic).strip()
    topic_plain = topic.replace("`", "").strip()

    nb_title_match = re.search(r"\*\*Tên NotebookLM gợi ý:\*\*\s*`([^`]+)`", body)
    if nb_title_match:
        notebook_title = nb_title_match.group(1).strip()
    else:
        prefix = derive_prefix_from_filename(schedule_path, day_num)
        notebook_title = f"{prefix} — {topic_plain}" if topic_plain else prefix

    raw_match = re.search(r"\*\*File lưu sau khi\s*`/export`:\*\*\s*`([^`]+)`", body)
    if raw_match:
        raw_file = raw_match.group(1).strip()
    else:
        raw_prefix = derive_raw_prefix(schedule_path, day_num)
        raw_file = f"raw/{raw_prefix}-{slugify_vi(topic_plain, max_len=48)}.md"

    # Extract Lesson Scope / Customize notebook fenced code block
    scope_sec = re.search(
        r"#{3,4}\s+(?:📋\s*)?(?:Khối\s+`?Customize notebook`?|Customize notebook|Lesson Scope)[^\n]*\n```(?:text|txt|markdown|md)?\n(.*?)\n```",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if scope_sec:
        scope_block = scope_sec.group(1).strip()
    else:
        fallback_fence = re.search(r"```(?:text|txt)?\n(.*?)\n```", body, re.DOTALL)
        scope_block = fallback_fence.group(1).strip() if fallback_fence else ""

    sources = [] if completed else extract_sources(body)
    urls = [s["url"] for s in sources if s["type"] == "url"]

    base_prompt = load_base_prompt()
    merged_prompt = (
        f"{base_prompt}{MERGE_HEADER}{scope_block}" if scope_block else base_prompt
    )

    return {
        "schedule_file": str(schedule_path.relative_to(VAULT_ROOT)).replace("\\", "/")
        if schedule_path.is_relative_to(VAULT_ROOT)
        else str(schedule_path),
        "day": day_num,
        "format": section["format"],
        "completed": completed,
        "heading": heading,
        "topic": topic_plain,
        "notebook_title": notebook_title,
        "raw_file": raw_file,
        "sources": sources,
        "urls": urls,
        "scope_block": scope_block,
        "counts": {
            "base_prompt_chars": len(base_prompt),
            "base_prompt_max": MAX_BASE_PROMPT_CHARS,
            "base_prompt_ok": len(base_prompt) <= MAX_BASE_PROMPT_CHARS,
            "scope_chars": len(scope_block),
            "scope_max": MAX_SCOPE_CHARS,
            "scope_ok": 0 < len(scope_block) <= MAX_SCOPE_CHARS if not completed else True,
            "merged_chars": len(merged_prompt),
            "merged_max": MAX_MERGED_CHARS,
            "merged_ok": len(merged_prompt) <= MAX_MERGED_CHARS,
        },
        "merged_prompt": merged_prompt,
    }


def check_single_url(url: str, timeout: float = 15.0) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    last_error = ""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                status = getattr(resp, "status", resp.getcode())
                if status == 200:
                    return {
                        "type": "url",
                        "url": url,
                        "status": status,
                        "final_url": resp.geturl(),
                        "method": method,
                        "ok": True,
                    }
                last_error = f"HTTP {status}"
                if method == "HEAD":
                    continue
                return {
                    "type": "url",
                    "url": url,
                    "status": status,
                    "final_url": resp.geturl(),
                    "method": method,
                    "ok": False,
                }
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if method == "HEAD" and exc.code in (400, 403, 405, 501):
                continue
            return {
                "type": "url",
                "url": url,
                "status": exc.code,
                "error": last_error,
                "method": method,
                "ok": False,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if method == "HEAD":
                continue
            return {
                "type": "url",
                "url": url,
                "status": None,
                "error": last_error,
                "method": method,
                "ok": False,
            }

    return {"type": "url", "url": url, "status": None, "error": last_error, "ok": False}


def validate_sources(sources: list[dict[str, Any]], skip_urls: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for src in sources:
        stype = src["type"]
        if stype == "url":
            if skip_urls:
                results.append({"type": "url", "url": src["url"], "skipped": True, "ok": True})
            else:
                results.append(check_single_url(src["url"]))
        elif stype == "file":
            ok = bool(src.get("exists") and src.get("ext_valid"))
            entry = {
                "type": "file",
                "file_path": src["file_path"],
                "extension": src["extension"],
                "exists": src["exists"],
                "ext_valid": src["ext_valid"],
                "ok": ok,
            }
            if not src["exists"]:
                entry["error"] = f"Local file not found: {src['file_path']}"
            elif not src["ext_valid"]:
                entry["error"] = f"Unsupported extension: {src['extension']}"
            results.append(entry)
        elif stype == "drive":
            ok = bool(src.get("document_id") and src.get("doc_type") in VALID_DRIVE_DOC_TYPES)
            results.append(
                {
                    "type": "drive",
                    "document_id": src.get("document_id"),
                    "doc_type": src.get("doc_type"),
                    "ok": ok,
                }
            )
        elif stype == "text":
            ok = bool(src.get("title") and src.get("text"))
            results.append(
                {
                    "type": "text",
                    "title": src.get("title"),
                    "chars": len(src.get("text", "")),
                    "ok": ok,
                }
            )
    return results


def _get_day_data(schedule_arg: str, day_num: int) -> dict[str, Any]:
    path = resolve_vault_path(schedule_arg)
    if not path.exists():
        raise FileNotFoundError(f"Schedule file not found: {path}")
    text = read_text_normalized(path)
    sections = extract_day_sections(text)
    for sec in sections:
        if sec["day"] == day_num:
            return parse_day_section(path, sec)
    available = [s["day"] for s in sections]
    raise ValueError(f"Day {day_num} not found in {path} (available days: {available})")


def cmd_check_prompt(_args: argparse.Namespace) -> int:
    prompt = load_base_prompt()
    length = len(prompt)
    ok = length <= MAX_BASE_PROMPT_CHARS
    print(
        json.dumps(
            {
                "path": str(PROMPT_FILE),
                "chars": length,
                "max_chars": MAX_BASE_PROMPT_CHARS,
                "headroom_for_scope": MAX_MERGED_CHARS - length - len(MERGE_HEADER),
                "ok": ok,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


def cmd_parse_day(args: argparse.Namespace) -> int:
    data = _get_day_data(args.schedule, args.day)
    if not args.include_merged:
        data = {k: v for k, v in data.items() if k != "merged_prompt"}
    print(json.dumps(data, ensure_ascii=False, indent=2))
    counts = data["counts"]
    ok = counts["base_prompt_ok"] and counts["scope_ok"] and counts["merged_ok"]
    return 0 if ok else 1


def cmd_compose_prompt(args: argparse.Namespace) -> int:
    data = _get_day_data(args.schedule, args.day)
    counts = data["counts"]
    if not counts["merged_ok"]:
        print(
            json.dumps(
                {
                    "error": "Merged prompt exceeds 10,000 char NotebookLM limit",
                    "counts": counts,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    merged = data["merged_prompt"]
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(merged, encoding="utf-8")
        print(json.dumps({"written": str(out_path), "counts": counts}, ensure_ascii=False, indent=2))
    else:
        print(merged)
    return 0


def cmd_check_sources(args: argparse.Namespace) -> int:
    path = resolve_vault_path(args.file)
    text = read_text_normalized(path)
    sections = extract_day_sections(text)
    if args.day is not None:
        sections = [s for s in sections if s["day"] == args.day]

    all_sources: list[dict[str, Any]] = []
    for sec in sections:
        parsed = parse_day_section(path, sec)
        all_sources.extend(parsed["sources"])

    if not all_sources:
        print(json.dumps({"total": 0, "all_ok": False, "error": "No sources found"}, ensure_ascii=False))
        return 1

    results = validate_sources(all_sources, skip_urls=args.skip_urls)
    all_ok = all(r["ok"] for r in results)
    print(
        json.dumps(
            {"total": len(results), "all_ok": all_ok, "results": results},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all_ok else 1


def cmd_check_urls(args: argparse.Namespace) -> int:
    urls: list[str] = list(args.urls)
    if args.file:
        path = resolve_vault_path(args.file)
        text = read_text_normalized(path)
        sections = extract_day_sections(text)
        if args.day is not None:
            sections = [s for s in sections if s["day"] == args.day]
        for sec in sections:
            parsed = parse_day_section(path, sec)
            for u in parsed["urls"]:
                if u not in urls:
                    urls.append(u)

    if not urls:
        print(json.dumps({"error": "No URLs provided or found"}, ensure_ascii=False))
        return 1

    results = [check_single_url(u) for u in urls]
    all_ok = all(r["ok"] for r in results)
    print(
        json.dumps(
            {"total": len(results), "all_ok": all_ok, "results": results},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all_ok else 1


def cmd_check_week(args: argparse.Namespace) -> int:
    path = resolve_vault_path(args.schedule)
    text = read_text_normalized(path)
    sections = extract_day_sections(text)
    days_report = []
    all_ok = True

    for sec in sections:
        parsed = parse_day_section(path, sec)
        src_results = (
            []
            if parsed["completed"]
            else validate_sources(parsed["sources"], skip_urls=args.skip_urls)
        )
        sources_ok = all(r["ok"] for r in src_results) if src_results else True
        c = parsed["counts"]
        day_ok = c["base_prompt_ok"] and c["scope_ok"] and c["merged_ok"] and sources_ok
        if not day_ok:
            all_ok = False
        by_type: dict[str, int] = {}
        for s in parsed["sources"]:
            by_type[s["type"]] = by_type.get(s["type"], 0) + 1
        days_report.append(
            {
                "day": parsed["day"],
                "completed": parsed["completed"],
                "notebook_title": parsed["notebook_title"],
                "raw_file": parsed["raw_file"],
                "source_count": len(parsed["sources"]),
                "source_types": by_type,
                "counts": c,
                "sources_ok": sources_ok,
                "failed_sources": [r for r in src_results if not r["ok"]],
                "ok": day_ok,
            }
        )

    print(
        json.dumps(
            {
                "schedule_file": str(path),
                "day_count": len(days_report),
                "all_ok": all_ok,
                "days": days_report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all_ok else 1


def _run_live_doctor(uvx_path: str) -> dict[str, Any]:
    cmd = [uvx_path, "--from", f"notebooklm-mcp-cli>={MIN_NLM_VERSION}", "nlm", "doctor"]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=env,
        )
        out = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        ver_m = re.search(r"notebooklm-mcp-cli:\s*([0-9.]+)", out)
        acc_m = re.search(r"Account:\s*([^\r\n]+)", out)
        cookies_m = re.search(r"Cookies:\s*present\s*\((\d+)", out, re.IGNORECASE)
        csrf_ok = bool(re.search(r"CSRF token:\s*yes", out, re.IGNORECASE))
        headless_ok = bool(re.search(r"Headless auth:\s*available", out, re.IGNORECASE))
        return {
            "checked": True,
            "exit_code": proc.returncode,
            "version": ver_m.group(1) if ver_m else None,
            "account": acc_m.group(1).strip() if acc_m else None,
            "cookies_count": int(cookies_m.group(1)) if cookies_m else 0,
            "csrf_ok": csrf_ok,
            "headless_auth": headless_ok,
            "ok": bool(ver_m and cookies_m and csrf_ok),
        }
    except Exception as exc:  # noqa: BLE001
        return {"checked": True, "ok": False, "error": str(exc)}


def _build_pc_check_env(
    args: argparse.Namespace,
    system: str,
    prompt_check: dict[str, Any],
) -> dict[str, Any]:
    uv_path = shutil.which("uv")
    uvx_path = shutil.which("uvx")
    auth_dir = Path.home() / ".notebooklm-mcp-cli"
    profiles_dir = auth_dir / "profiles"
    has_auth = auth_dir.exists() and (
        (profiles_dir.exists() and any(profiles_dir.iterdir()))
        or (auth_dir / "auth.json").exists()
    )

    doctor: dict[str, Any] | None = None
    if args.live and uvx_path:
        doctor = _run_live_doctor(uvx_path)

    if system == "Windows":
        install_uv = 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    else:
        install_uv = "curl -LsSf https://astral.sh/uv/install.sh | sh"

    login_cmd = f'uvx --from "notebooklm-mcp-cli>={MIN_NLM_VERSION}" nlm login'
    doctor_cmd = f'uvx --from "notebooklm-mcp-cli>={MIN_NLM_VERSION}" nlm doctor'

    auth_ok = doctor["ok"] if doctor is not None else has_auth
    ready = bool(uv_path and uvx_path and auth_ok and prompt_check.get("ok"))

    next_steps: list[str] = []
    if not (uv_path and uvx_path):
        next_steps.append(f"Install uv: {install_uv}")
    if not auth_ok:
        next_steps.append(f"Login NotebookLM: {login_cmd}")
    if not prompt_check.get("ok"):
        next_steps.append(
            f"Fix docs/notebooklm-system-prompt.md (must exist and be <= {MAX_BASE_PROMPT_CHARS} chars from '# SYSTEM INSTRUCTION')"
        )
    if not args.live:
        next_steps.append(f"Verify auth health: {doctor_cmd}")

    return {
        "uv": uv_path,
        "uvx": uvx_path,
        "auth_dir": str(auth_dir),
        "has_auth_profile": has_auth,
        "doctor": doctor,
        "ready": ready,
        "next_steps": next_steps,
        "android_mode": None,
        "android_status": None,
    }


def _build_android_check_env(
    args: argparse.Namespace,
    prompt_check: dict[str, Any],
) -> dict[str, Any]:
    android_status = nlm_connect.detect_environment()
    android_mode = android_status["mode"]
    auth_dir = Path(android_status["auth_dir"])
    has_auth = bool(android_status.get("has_auth_profile"))
    uv_path = android_status.get("uv")
    uvx_path = android_status.get("uvx")

    doctor: dict[str, Any] | None = None
    if args.live:
        if android_mode == "remote":
            doctor = nlm_connect.remote_endpoint_health(nlm_connect.load_android_mode(auth_dir))
        else:
            doctor = nlm_connect.live_cookie_health(auth_dir=auth_dir, update_metadata=True)

    next_steps = list(android_status.get("next_steps") or [])
    if android_mode == "remote":
        live_ok = bool(doctor["ok"]) if doctor is not None else True
        ready = bool(
            android_status.get("runtime_shim_ok")
            and android_status.get("remote_configured")
            and live_ok
            and prompt_check.get("ok")
        )
        if doctor is not None and not live_ok:
            next_steps.append(
                "Verify remote MCP endpoint (run /notebooklm-connect): python .agents/plugins/notebooklm-study/scripts/nlm_connect.py health --mode remote"
            )
    else:
        auth_ok = bool(doctor["ok"]) if doctor is not None else bool(android_status.get("auth_ok"))
        ready = bool(
            android_status.get("debian_installed")
            and android_status.get("debian_nlm_installed")
            and android_status.get("runtime_shim_ok")
            and auth_ok
            and prompt_check.get("ok")
        )
        if doctor is not None and not doctor.get("ok") and not any("import-cookies" in s for s in next_steps):
            next_steps.append(
                'Refresh cookies via /notebooklm-connect: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py import-cookies --file "/storage/emulated/0/Documents/cookies.txt" --delete-source'
            )

    if not prompt_check.get("ok"):
        next_steps.append(
            f"Fix docs/notebooklm-system-prompt.md (must exist and be <= {MAX_BASE_PROMPT_CHARS} chars from '# SYSTEM INSTRUCTION')"
        )
    if not args.live:
        next_steps.append(
            "Verify live health: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py health"
        )
    if next_steps:
        next_steps.append("Or run `/notebooklm-connect` for guided Android setup")

    return {
        "uv": uv_path,
        "uvx": uvx_path,
        "auth_dir": str(auth_dir),
        "has_auth_profile": has_auth,
        "doctor": doctor,
        "ready": ready,
        "next_steps": next_steps,
        "android_mode": android_mode,
        "android_status": android_status,
    }


def cmd_check_env(args: argparse.Namespace) -> int:
    system = platform.system()
    plat = nlm_connect.detect_platform()
    is_android = plat == "android-agy"

    # Check system prompt budget
    prompt_check: dict[str, Any]
    try:
        prompt_text = load_base_prompt()
        prompt_check = {
            "exists": True,
            "chars": len(prompt_text),
            "max_chars": MAX_BASE_PROMPT_CHARS,
            "ok": len(prompt_text) <= MAX_BASE_PROMPT_CHARS,
        }
    except Exception as exc:  # noqa: BLE001
        prompt_check = {"exists": False, "ok": False, "error": str(exc)}

    # Check clean-slate vault state in CLAUDE.md
    clean_slate = False
    if CLAUDE_FILE.exists():
        claude_text = read_text_normalized(CLAUDE_FILE)
        clean_slate = "CHƯA KHỞI TẠO (CLEAN SLATE)" in claude_text

    env_details = (
        _build_android_check_env(args, prompt_check)
        if is_android
        else _build_pc_check_env(args, system, prompt_check)
    )
    ready = bool(env_details["ready"])

    print(
        json.dumps(
            {
                "os": system,
                "platform": plat,
                "is_android": is_android,
                "python": platform.python_version(),
                "vault_root": str(VAULT_ROOT),
                "clean_slate": clean_slate,
                "sources_dir_exists": SOURCES_DIR.exists(),
                "active_session": STATE_FILE.exists(),
                "uv": env_details["uv"],
                "uvx": env_details["uvx"],
                "auth_dir": env_details["auth_dir"],
                "has_auth_profile": env_details["has_auth_profile"],
                "android_mode": env_details["android_mode"],
                "android_status": env_details["android_status"],
                "prompt_check": prompt_check,
                "doctor": env_details["doctor"],
                "ready": ready,
                "next_steps": env_details["next_steps"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ready else 1


def cmd_state_get(_args: argparse.Namespace) -> int:
    if not STATE_FILE.exists():
        print(json.dumps({"active": False, "state_file": str(STATE_FILE)}, ensure_ascii=False, indent=2))
        return 0
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    print(json.dumps({"active": True, **data}, ensure_ascii=False, indent=2))
    return 0


def cmd_state_set(args: argparse.Namespace) -> int:
    existing: dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    payload = {
        **existing,
        "notebook_id": args.notebook_id,
        "title": args.title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.conversation_id is not None:
        payload["conversation_id"] = args.conversation_id
    if args.schedule is not None:
        payload["schedule_file"] = args.schedule
    if args.day is not None:
        payload["day"] = args.day
    if args.raw_file is not None:
        payload["raw_file"] = args.raw_file
    if args.url is not None:
        payload["notebook_url"] = args.url
    elif args.notebook_id:
        payload["notebook_url"] = f"https://notebook.google.com/notebook/{args.notebook_id}"

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(STATE_FILE), **payload}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NotebookLM Study Plugin cross-platform helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_cp = sub.add_parser("check-prompt", help="Check docs/notebooklm-system-prompt.md char budget")
    s_cp.set_defaults(func=cmd_check_prompt)

    s_pd = sub.add_parser("parse-day", help="Parse one day (multi-source) from a weekly schedule file")
    s_pd.add_argument("schedule", help="Path to docs/lich-hoc-*.md")
    s_pd.add_argument("day", type=int, help="Day number (e.g. 1..5)")
    s_pd.add_argument("--include-merged", action="store_true", help="Include full merged prompt in JSON")
    s_pd.set_defaults(func=cmd_parse_day)

    s_comp = sub.add_parser("compose-prompt", help="Output merged Configure Chat prompt for a day")
    s_comp.add_argument("schedule", help="Path to docs/lich-hoc-*.md")
    s_comp.add_argument("day", type=int, help="Day number (e.g. 1..5)")
    s_comp.add_argument("--out", help="Optional output file path")
    s_comp.set_defaults(func=cmd_compose_prompt)

    s_cs = sub.add_parser("check-sources", help="Validate all 4 source types (url/file/drive/text) in a schedule")
    s_cs.add_argument("--file", required=True, help="Schedule file path")
    s_cs.add_argument("--day", type=int, help="Optional day number")
    s_cs.add_argument("--skip-urls", action="store_true", help="Skip live HTTP URL checks")
    s_cs.set_defaults(func=cmd_check_sources)

    s_cu = sub.add_parser("check-urls", help="Verify URLs return HTTP 200 OK")
    s_cu.add_argument("--file", help="Schedule file to extract URLs from")
    s_cu.add_argument("--day", type=int, help="Optional day number when using --file")
    s_cu.add_argument("urls", nargs="*", help="Direct URLs to check")
    s_cu.set_defaults(func=cmd_check_urls)

    s_cw = sub.add_parser("check-week", help="Audit all days, budgets, and multi-source entries in a schedule")
    s_cw.add_argument("schedule", help="Path to docs/lich-hoc-*.md")
    s_cw.add_argument("--skip-urls", action="store_true", help="Skip live HTTP checks")
    s_cw.set_defaults(func=cmd_check_week)

    s_ce = sub.add_parser("check-env", help="Run cross-platform health check for uv, auth, prompt, and vault")
    s_ce.add_argument("--live", action="store_true", help="Also run `uvx nlm doctor` for live auth/version verification")
    s_ce.set_defaults(func=cmd_check_env)

    s_sg = sub.add_parser("state-get", help="Read active notebook state")
    s_sg.set_defaults(func=cmd_state_get)

    s_ss = sub.add_parser("state-set", help="Save active notebook state")
    s_ss.add_argument("--notebook-id", required=True)
    s_ss.add_argument("--title", required=True)
    s_ss.add_argument("--conversation-id")
    s_ss.add_argument("--schedule")
    s_ss.add_argument("--day", type=int)
    s_ss.add_argument("--raw-file")
    s_ss.add_argument("--url")
    s_ss.set_defaults(func=cmd_state_set)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
