#!/usr/bin/env python3
"""Cross-platform NotebookLM MCP connection & Android fast-path helper.

Uses Python 3 standard library only (Windows / macOS / Linux / Android AGY).
Never prints raw cookies, CSRF tokens, or Bearer tokens to stdout/stderr.

Subcommands:
  detect         Inspect OS platform, uv/uvx, proot-distro Debian, shims & auth
  health         Verify NotebookLM Cookie/CSRF (or Remote MCP endpoint)
  import-cookies Validate, verify, and store auth profile (optionally wipe temp source)
  install-shim   Install Android smart uvx shim (proot or remote mode) without touching Git
  set-mode       Switch Android runtime mode between `proot` and `remote`
  remote-proxy   Run stdio <-> Streamable-HTTP MCP bridge for Android remote mode
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import platform
import re
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MIN_NLM_VERSION = "0.16.5"
DEFAULT_BASE_URL = "https://notebook.google.com"
DEFAULT_DISTRO = "debian"
REQUIRED_COOKIES: tuple[str, ...] = ("SID", "HSID", "SSID", "APISID", "SAPISID")
SHIM_MARKER = "# AGY_NLM_SHIM v1"
DEFAULT_QUERY_TIMEOUT = "180"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

DEFAULT_AUTH_DIR = Path.home() / ".notebooklm-mcp-cli"


class _LoginRedirectError(Exception):
    """Raised when Google redirects a cookie probe back to accounts login."""

    def __init__(self, location: str) -> None:
        super().__init__(location)
        self.location = location


class _LoginStopRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow benign NotebookLM redirects; abort immediately on Google login redirects."""

    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        parsed = urllib.parse.urlparse(newurl)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        full_lower = newurl.lower()
        if (
            "accounts.google.com" in host
            or "servicelogin" in full_lower
            or "/signin" in path
        ):
            raise _LoginRedirectError(newurl)

        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        cookie = req.get_header("Cookie")
        if cookie and (host == "google.com" or host.endswith(".google.com")):
            redirected.add_unredirected_header("Cookie", cookie)
        ua = req.get_header("User-Agent")
        if ua:
            redirected.add_unredirected_header("User-Agent", ua)
        return redirected


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chmod_if_posix(path: Path, mode: int) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def write_json_secure(path: Path, data: Any, private: bool = True) -> None:
    """Atomically write UTF-8 JSON and lock permissions to 0700/0600 on POSIX."""
    dir_mode = 0o700 if private else 0o755
    file_mode = 0o600 if private else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(path.parent, dir_mode)

    tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        _chmod_if_posix(tmp_path, file_mode)
        os.replace(tmp_path, path)
        _chmod_if_posix(path, file_mode)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _read_json_safe(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def detect_platform(
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> str:
    """Classify runtime OS as android-agy, windows, macos, or linux."""
    env_map = env if env is not None else os.environ
    home_dir = home if home is not None else Path.home()
    home_str = str(home_dir)
    prefix_str = env_map.get("PREFIX", "")

    if (
        env_map.get("ANDROID_ROOT")
        or env_map.get("ANDROID_DATA")
        or env_map.get("AGY_APPLICATION_ID")
    ):
        return "android-agy"

    if platform.system() == "Linux" and (
        prefix_str.rstrip("/").endswith("/files/usr")
        or "/com.agy/" in home_str
        or "/com.agy.dev/" in home_str
    ):
        return "android-agy"

    sys_name = platform.system()
    if sys_name == "Windows":
        return "windows"
    if sys_name == "Darwin":
        return "macos"
    return "linux"


def resolve_android_paths(
    home: Path | None = None,
    prefix: Path | None = None,
    runtime_bin: Path | None = None,
    auth_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Path]:
    """Resolve Android AGY paths cleanly from args, env vars, or HOME defaults."""
    env_map = env if env is not None else os.environ
    home_path = home or Path(env_map.get("HOME") or Path.home())
    prefix_env = env_map.get("PREFIX")
    prefix_path = prefix or (Path(prefix_env) if prefix_env else (home_path / "usr"))
    runtime_bin_path = runtime_bin or (home_path / "runtime" / "bin")
    auth_path = auth_dir or (home_path / ".notebooklm-mcp-cli")
    return {
        "home": home_path,
        "prefix": prefix_path,
        "runtime_bin": runtime_bin_path,
        "auth_dir": auth_path,
    }


def load_android_mode(auth_dir: Path = DEFAULT_AUTH_DIR) -> dict[str, Any]:
    """Load local Android runtime mode config (defaults to proot debian)."""
    cfg_path = auth_dir / "android-mode.json"
    raw = _read_json_safe(cfg_path)
    cfg: dict[str, Any] = raw if isinstance(raw, dict) else {}
    mode = str(cfg.get("mode") or "proot").strip().lower()
    if mode not in ("proot", "remote"):
        mode = "proot"
    distro = str(cfg.get("distro") or DEFAULT_DISTRO).strip() or DEFAULT_DISTRO
    headers = cfg.get("headers") if isinstance(cfg.get("headers"), dict) else {}
    return {
        "mode": mode,
        "distro": distro,
        "url": str(cfg.get("url") or "").strip(),
        "bearer_token": str(cfg.get("bearer_token") or "").strip(),
        "headers": {str(k): str(v) for k, v in headers.items() if k and v is not None},
        "updated_at": str(cfg.get("updated_at") or ""),
    }


def sanitize_mode(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Return non-secret summary of Android mode configuration."""
    headers = cfg.get("headers") if isinstance(cfg.get("headers"), Mapping) else {}
    return {
        "mode": str(cfg.get("mode") or "proot"),
        "distro": str(cfg.get("distro") or DEFAULT_DISTRO),
        "url": str(cfg.get("url") or ""),
        "has_bearer_token": bool(cfg.get("bearer_token")),
        "custom_header_names": sorted(str(k) for k in headers.keys()),
    }


def _normalize_cookie_container(obj: Any) -> dict[str, str]:
    cookies: dict[str, str] = {}
    if isinstance(obj, dict):
        if "cookies" in obj and isinstance(obj["cookies"], (dict, list)):
            return _normalize_cookie_container(obj["cookies"])
        for k, v in obj.items():
            if k and v is not None and isinstance(v, (str, int, float)):
                cookies[str(k).strip()] = str(v)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                val = item.get("value")
                if name and val is not None:
                    cookies[name] = str(val)
    return cookies


def load_saved_cookies(auth_dir: Path = DEFAULT_AUTH_DIR) -> dict[str, str]:
    """Load stored cookies from profiles/default/cookies.json or root auth.json."""
    profile_cookies = _read_json_safe(auth_dir / "profiles" / "default" / "cookies.json")
    parsed = _normalize_cookie_container(profile_cookies)
    if parsed:
        return parsed
    root_auth = _read_json_safe(auth_dir / "auth.json")
    return _normalize_cookie_container(root_auth)


def parse_cookies_input(raw_text: str) -> dict[str, str]:
    """Parse JSON (auth.json/dict/list), Netscape cookies.txt, or raw Cookie header."""
    text = raw_text.lstrip("\ufeff")
    stripped = text.lstrip()

    # 1. JSON formats
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
            parsed = _normalize_cookie_container(data)
            if parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    # 2. Netscape cookies.txt (7 tab-separated fields, optional #HttpOnly_ prefix)
    netscape_cookies: dict[str, str] = {}
    for line in text.splitlines():
        candidate = line.strip("\r\n")
        if not candidate.strip():
            continue
        if candidate.startswith("#HttpOnly_"):
            candidate = candidate[len("#HttpOnly_") :]
        elif candidate.lstrip().startswith("#"):
            continue
        cols = candidate.split("\t")
        if len(cols) >= 7:
            name = cols[5].strip()
            val = cols[6].strip()
            if name:
                netscape_cookies[name] = val
    if netscape_cookies:
        return netscape_cookies

    # 3. Raw Cookie: request header (single-line or pasted inside header lines)
    header_line = ""
    for line in text.splitlines():
        m = re.match(r"^\s*cookie\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if m:
            header_line = m.group(1).strip()
            break

    if not header_line:
        joined = " ".join(
            ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
        ).strip()
        joined = re.sub(r"^\s*cookie\s*:\s*", "", joined, flags=re.IGNORECASE).strip()
        header_line = joined

    if len(header_line) >= 2 and header_line[0] == header_line[-1] and header_line[0] in ("'", '"'):
        header_line = header_line[1:-1].strip()

    header_cookies: dict[str, str] = {}
    for part in header_line.split(";"):
        seg = part.strip()
        if "=" not in seg:
            continue
        name, val = seg.split("=", 1)
        name = name.strip()
        val = val.strip()
        if name:
            header_cookies[name] = val
    return header_cookies


def validate_required_cookies(cookies: Mapping[str, str]) -> dict[str, Any]:
    """Check presence of all 5 required Google SSO cookies for NotebookLM."""
    present = [k for k in REQUIRED_COOKIES if str(cookies.get(k) or "").strip()]
    missing = [k for k in REQUIRED_COOKIES if k not in present]
    return {
        "count": len(cookies),
        "present": present,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def write_auth_profile(
    cookies: dict[str, str],
    csrf_token: str = "",
    session_id: str = "",
    build_label: str = "",
    base_host: str = DEFAULT_BASE_URL,
    email: str = "",
    auth_dir: Path = DEFAULT_AUTH_DIR,
) -> list[str]:
    """Write complete notebooklm-mcp-cli file-mode profile with 0700/0600 permissions."""
    now = _now_iso()
    profile_dir = auth_dir / "profiles" / "default"
    files_to_write: list[tuple[Path, Any]] = [
        (
            auth_dir / "config.json",
            {"auth": {"default_profile": "default", "storage": "file"}},
        ),
        (
            auth_dir / "auth.json",
            {
                "cookies": dict(cookies),
                "csrf_token": csrf_token,
                "session_id": session_id,
                "build_label": build_label,
                "base_host": base_host,
                "extracted_at": now,
            },
        ),
        (
            profile_dir / "storage-mode.json",
            {"mode": "file"},
        ),
        (
            profile_dir / "cookies.json",
            dict(cookies),
        ),
        (
            profile_dir / "metadata.json",
            {
                "csrf_token": csrf_token,
                "session_id": session_id,
                "email": email,
                "build_label": build_label,
                "base_host": base_host,
                "browser_backend": "manual-android",
                "last_validated": now,
            },
        ),
    ]
    written: list[str] = []
    auth_dir.mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(auth_dir, 0o700)
    (auth_dir / "profiles").mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(auth_dir / "profiles", 0o700)
    for target, data in files_to_write:
        write_json_secure(target, data, private=True)
        written.append(str(target))
    return written


def _wipe_single_file(file_path: Path) -> None:
    try:
        size = file_path.stat().st_size
        if size > 0:
            with file_path.open("r+b") as fh:
                fh.write(b"\x00" * size)
                fh.flush()
    except OSError:
        pass
    file_path.unlink(missing_ok=True)


def secure_delete_path(target: Path, auth_dir: Path = DEFAULT_AUTH_DIR) -> bool:
    """Zero-fill and remove temporary credential files/dirs; never delete protected dirs."""
    resolved = target.resolve()
    resolved_auth = auth_dir.resolve()
    parts_lower = {p.lower() for p in resolved.parts}
    if ".git" in parts_lower or ".agents" in parts_lower:
        raise ValueError(f"Refusing to delete protected repository path: {target}")
    try:
        resolved.relative_to(resolved_auth)
        raise ValueError(f"Refusing to delete active auth directory path: {target}")
    except ValueError as exc:
        if "Refusing to delete" in str(exc):
            raise

    if not target.exists():
        return False
    if target.is_file() or target.is_symlink():
        if target.is_symlink():
            target.unlink(missing_ok=True)
        else:
            _wipe_single_file(target)
        return True
    if target.is_dir():
        for root_str, _, filenames in os.walk(target, topdown=False):
            root_path = Path(root_str)
            for fname in filenames:
                fpath = root_path / fname
                if fpath.is_symlink():
                    fpath.unlink(missing_ok=True)
                else:
                    _wipe_single_file(fpath)
        shutil.rmtree(target)
        return True
    return False


def _build_ssl_context(env: Mapping[str, str] | None = None) -> ssl.SSLContext:
    env_map = env if env is not None else os.environ
    prefix_str = env_map.get("PREFIX", "")
    ca_candidates = [
        env_map.get("SSL_CERT_FILE", ""),
        env_map.get("CURL_CA_BUNDLE", ""),
        str(Path(prefix_str) / "etc" / "tls" / "cert.pem") if prefix_str else "",
    ]
    for candidate in ca_candidates:
        if candidate and Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def _probe_cookies_internal(
    cookies: Mapping[str, str],
    base_url: str | None = None,
    timeout: int = 15,
    env: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    env_map = env if env is not None else os.environ
    target_base = (base_url or env_map.get("NOTEBOOKLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    validation = validate_required_cookies(cookies)
    cookie_count = len(cookies)

    if cookie_count == 0:
        return (
            {
                "checked": True,
                "mode": "cookie",
                "ok": False,
                "reason": "no_cookies",
                "http_status": None,
                "redirected_to_login": False,
                "cookies_count": 0,
                "missing_required_cookies": list(REQUIRED_COOKIES),
                "csrf_ok": False,
                "session_id_ok": False,
                "build_label": "",
                "base_host": target_base,
                "elapsed_ms": 0,
            },
            {},
        )

    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = urllib.request.Request(
        target_base + "/",
        headers={
            "Cookie": cookie_header,
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(
        _LoginStopRedirectHandler(),
        urllib.request.HTTPSHandler(context=_build_ssl_context(env_map)),
    )

    started = time.monotonic()
    http_status: int | None = None
    redirected_to_login = False
    error_msg: str | None = None
    html = ""
    final_url = target_base + "/"

    try:
        with opener.open(req, timeout=timeout) as resp:
            http_status = int(resp.status)
            final_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="replace")
    except _LoginRedirectError as exc:
        redirected_to_login = True
        final_url = exc.location
        error_msg = "Redirected to Google Sign-In (cookies expired or incomplete)"
    except urllib.error.HTTPError as exc:
        http_status = int(exc.code)
        error_msg = f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    csrf_m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    sid_m = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html)
    build_m = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)

    csrf_token = csrf_m.group(1) if csrf_m else ""
    session_id = sid_m.group(1) if sid_m else ""
    build_label = build_m.group(1) if build_m else ""

    csrf_ok = bool(csrf_token or session_id)
    ok = (
        http_status == 200
        and not redirected_to_login
        and csrf_ok
        and validation["ok"]
    )
    parsed_final = urllib.parse.urlparse(final_url)
    resolved_base = f"{parsed_final.scheme}://{parsed_final.netloc}" if parsed_final.netloc else target_base

    summary: dict[str, Any] = {
        "checked": True,
        "mode": "cookie",
        "ok": ok,
        "http_status": http_status,
        "redirected_to_login": redirected_to_login,
        "cookies_count": cookie_count,
        "missing_required_cookies": validation["missing"],
        "csrf_ok": csrf_ok,
        "session_id_ok": bool(session_id),
        "build_label": build_label,
        "base_host": resolved_base,
        "elapsed_ms": elapsed_ms,
    }
    if error_msg:
        summary["error"] = error_msg
    elif not ok and not validation["ok"]:
        summary["error"] = "Missing required SSO cookies: " + ", ".join(validation["missing"])
    elif not ok and not csrf_ok:
        summary["error"] = "Could not extract NotebookLM CSRF/session token from response"

    tokens = {
        "csrf_token": csrf_token,
        "session_id": session_id,
        "build_label": build_label,
        "base_host": resolved_base,
    }
    return summary, tokens


def _refresh_stored_metadata(auth_dir: Path, tokens: Mapping[str, str]) -> None:
    now = _now_iso()
    meta_path = auth_dir / "profiles" / "default" / "metadata.json"
    meta = _read_json_safe(meta_path)
    if isinstance(meta, dict):
        if tokens.get("csrf_token"):
            meta["csrf_token"] = tokens["csrf_token"]
        if tokens.get("session_id"):
            meta["session_id"] = tokens["session_id"]
        if tokens.get("build_label"):
            meta["build_label"] = tokens["build_label"]
        if tokens.get("base_host"):
            meta["base_host"] = tokens["base_host"]
        meta["last_validated"] = now
        write_json_secure(meta_path, meta, private=True)

    auth_path = auth_dir / "auth.json"
    root_auth = _read_json_safe(auth_path)
    if isinstance(root_auth, dict):
        if tokens.get("csrf_token"):
            root_auth["csrf_token"] = tokens["csrf_token"]
        if tokens.get("session_id"):
            root_auth["session_id"] = tokens["session_id"]
        if tokens.get("build_label"):
            root_auth["build_label"] = tokens["build_label"]
        if tokens.get("base_host"):
            root_auth["base_host"] = tokens["base_host"]
        root_auth["extracted_at"] = now
        write_json_secure(auth_path, root_auth, private=True)


def live_cookie_health(
    auth_dir: Path = DEFAULT_AUTH_DIR,
    base_url: str | None = None,
    timeout: int = 15,
    update_metadata: bool = False,
    cookies_override: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run zero-dependency HTTP health check on stored or supplied NotebookLM cookies."""
    cookies = dict(cookies_override) if cookies_override is not None else load_saved_cookies(auth_dir)
    summary, tokens = _probe_cookies_internal(
        cookies=cookies,
        base_url=base_url,
        timeout=timeout,
        env=env,
    )
    if summary.get("ok") and update_metadata and cookies_override is None:
        _refresh_stored_metadata(auth_dir, tokens)
    return summary


def _extract_first_sse_json(raw_sse: str) -> dict[str, Any] | None:
    buf: list[str] = []
    for raw_line in raw_sse.splitlines():
        line = raw_line.rstrip("\r")
        if line == "":
            if buf:
                payload = "\n".join(buf).strip()
                buf.clear()
                if payload:
                    try:
                        parsed = json.loads(payload)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            continue
        if line.startswith("data:"):
            val = line[5:]
            if val.startswith(" "):
                val = val[1:]
            buf.append(val)
    if buf:
        payload = "\n".join(buf).strip()
        if payload:
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return None


def remote_endpoint_health(
    mode_cfg: Mapping[str, Any],
    timeout: int = 15,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Probe a Streamable-HTTP remote MCP endpoint using MCP initialize JSON-RPC."""
    url = str(mode_cfg.get("url") or "").strip()
    if not url:
        return {
            "checked": True,
            "mode": "remote",
            "ok": False,
            "url": "",
            "http_status": None,
            "error": "Remote MCP URL is not configured",
            "elapsed_ms": 0,
        }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    custom_headers = mode_cfg.get("headers")
    if isinstance(custom_headers, Mapping):
        for k, v in custom_headers.items():
            if k and v is not None:
                headers[str(k)] = str(v)
    token = str(mode_cfg.get("bearer_token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    init_payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agy-nlm-health", "version": "1.0.0"},
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=init_payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=_build_ssl_context(env))
    )

    started = time.monotonic()
    http_status: int | None = None
    body_text = ""
    content_type = ""
    error_msg: str | None = None

    try:
        with opener.open(req, timeout=timeout) as resp:
            http_status = int(resp.status)
            content_type = (resp.headers.get("Content-Type") or "").lower()
            body_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        http_status = int(exc.code)
        error_msg = f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    rpc_obj: dict[str, Any] | None = None
    if body_text:
        if "text/event-stream" in content_type:
            rpc_obj = _extract_first_sse_json(body_text)
        else:
            try:
                parsed = json.loads(body_text)
                if isinstance(parsed, dict):
                    rpc_obj = parsed
            except json.JSONDecodeError:
                pass

    server_info = None
    if isinstance(rpc_obj, dict) and isinstance(rpc_obj.get("result"), dict):
        server_info = rpc_obj["result"].get("serverInfo")

    ok = (
        http_status is not None
        and 200 <= http_status < 300
        and isinstance(rpc_obj, dict)
        and "result" in rpc_obj
        and "error" not in rpc_obj
    )
    out: dict[str, Any] = {
        "checked": True,
        "mode": "remote",
        "ok": ok,
        "url": url,
        "http_status": http_status,
        "server_info": server_info,
        "elapsed_ms": elapsed_ms,
    }
    if error_msg:
        out["error"] = error_msg
    elif not ok:
        out["error"] = "Remote endpoint did not return a valid MCP initialize result"
    return out


def _file_has_marker(path: Path, marker: str = SHIM_MARKER) -> bool:
    if not path.is_file():
        return False
    try:
        return marker in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _permissions_private_ok(path: Path) -> bool | None:
    if os.name == "nt" or not path.exists():
        return None
    try:
        mode = path.stat().st_mode & 0o777
        return (mode & 0o077) == 0
    except OSError:
        return None


def detect_environment(
    home: Path | None = None,
    prefix: Path | None = None,
    runtime_bin: Path | None = None,
    auth_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect PC or Android AGY readiness, shims, Debian rootfs, and auth state."""
    env_map = env if env is not None else os.environ
    paths = resolve_android_paths(
        home=home,
        prefix=prefix,
        runtime_bin=runtime_bin,
        auth_dir=auth_dir,
        env=env_map,
    )
    resolved_home = paths["home"]
    resolved_prefix = paths["prefix"]
    resolved_runtime_bin = paths["runtime_bin"]
    resolved_auth_dir = paths["auth_dir"]

    plat = detect_platform(env=env_map, home=resolved_home)
    is_android = plat == "android-agy"

    path_env = env_map.get("PATH")
    uv_path = shutil.which("uv", path=path_env) if env is not None else shutil.which("uv")
    uvx_path = shutil.which("uvx", path=path_env) if env is not None else shutil.which("uvx")

    cookies = load_saved_cookies(resolved_auth_dir)
    cookie_check = validate_required_cookies(cookies)
    has_auth_profile = (resolved_auth_dir / "auth.json").is_file() or (
        resolved_auth_dir / "profiles" / "default" / "cookies.json"
    ).is_file()
    auth_ok = bool(has_auth_profile and cookie_check["ok"])

    if not is_android:
        install_uv = (
            'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
            if plat == "windows"
            else "curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
        next_steps: list[str] = []
        if not (uv_path and uvx_path):
            next_steps.append(f"Install uv: {install_uv}")
        if not auth_ok:
            next_steps.append(f'Login NotebookLM: uvx --from "notebooklm-mcp-cli>={MIN_NLM_VERSION}" nlm login')
        return {
            "platform": plat,
            "os": platform.system(),
            "python": platform.python_version(),
            "is_android": False,
            "mode": "native",
            "uv": uv_path,
            "uvx": uvx_path,
            "auth_dir": str(resolved_auth_dir),
            "has_auth_profile": has_auth_profile,
            "cookies_count": cookie_check["count"],
            "missing_required_cookies": cookie_check["missing"],
            "auth_ok": auth_ok,
            "ready": bool(uv_path and uvx_path and auth_ok),
            "next_steps": next_steps,
        }

    mode_cfg = load_android_mode(resolved_auth_dir)
    mode = mode_cfg["mode"]
    distro = mode_cfg["distro"]
    remote_configured = bool(mode_cfg["url"])

    pkg_bin = resolved_prefix / "bin" / "pkg"
    proot_distro_bin = resolved_prefix / "bin" / "proot-distro"
    pkg_installed = pkg_bin.is_file() or bool(shutil.which("pkg", path=path_env))
    proot_distro_installed = proot_distro_bin.is_file() or bool(
        shutil.which("proot-distro", path=path_env)
    )

    rootfs_dir = resolved_prefix / "var" / "lib" / "proot-distro" / "installed-rootfs" / distro
    debian_installed = rootfs_dir.is_dir()
    debian_uvx = rootfs_dir / "root" / ".local" / "bin" / "uvx"
    debian_mcp = rootfs_dir / "root" / ".local" / "bin" / "notebooklm-mcp"
    debian_nlm = rootfs_dir / "root" / ".local" / "bin" / "nlm"
    debian_uvx_installed = debian_uvx.is_file()
    debian_nlm_installed = debian_mcp.is_file() or debian_nlm.is_file()

    runtime_uvx = resolved_runtime_bin / "uvx"
    prefix_uvx = resolved_prefix / "bin" / "uvx"
    prefix_uvx_real = resolved_prefix / "bin" / "uvx.real"
    helper_copy = resolved_home / ".local" / "share" / "agy-nlm" / "nlm_connect.py"

    runtime_shim_ok = _file_has_marker(runtime_uvx)
    prefix_shim_ok = _file_has_marker(prefix_uvx)
    mode_file = resolved_auth_dir / "android-mode.json"

    android_steps: list[str] = []
    if mode == "remote":
        if not runtime_shim_ok:
            android_steps.append(
                'Install remote shim: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py install-shim --mode remote --remote-url "<url>"'
            )
        if not remote_configured:
            android_steps.append(
                'Configure remote URL: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py set-mode --mode remote --remote-url "<url>"'
            )
        ready = bool(runtime_shim_ok and remote_configured and helper_copy.is_file())
    else:
        if not proot_distro_installed:
            android_steps.append("Install proot-distro: pkg update && pkg install proot-distro")
        if not debian_installed:
            android_steps.append(f"Install Debian rootfs: proot-distro install {distro}")
        if not debian_nlm_installed:
            android_steps.append(
                f"Install uv + notebooklm-mcp-cli inside {distro} via /notebooklm-connect"
            )
        if not runtime_shim_ok:
            android_steps.append(
                f"Install uvx shim: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py install-shim --mode proot --distro {distro}"
            )
        if not auth_ok:
            android_steps.append(
                'Import cookies: python .agents/plugins/notebooklm-study/scripts/nlm_connect.py import-cookies --file "/storage/emulated/0/Documents/cookies.txt" --delete-source'
            )
        ready = bool(
            proot_distro_installed
            and debian_installed
            and debian_nlm_installed
            and runtime_shim_ok
            and auth_ok
        )

    return {
        "platform": plat,
        "os": platform.system(),
        "python": platform.python_version(),
        "is_android": True,
        "mode": mode,
        "mode_details": sanitize_mode(mode_cfg),
        "remote_configured": remote_configured,
        "home": str(resolved_home),
        "prefix": str(resolved_prefix),
        "runtime_bin": str(resolved_runtime_bin),
        "uv": uv_path,
        "uvx": uvx_path or (str(runtime_uvx) if runtime_uvx.exists() else None),
        "pkg_installed": pkg_installed,
        "proot_distro_installed": proot_distro_installed,
        "distro": distro,
        "debian_rootfs": str(rootfs_dir),
        "debian_installed": debian_installed,
        "debian_uvx_installed": debian_uvx_installed,
        "debian_nlm_installed": debian_nlm_installed,
        "runtime_shim_ok": runtime_shim_ok,
        "prefix_shim_ok": prefix_shim_ok,
        "uvx_real_exists": prefix_uvx_real.is_file(),
        "helper_copy_ok": helper_copy.is_file(),
        "auth_dir": str(resolved_auth_dir),
        "has_auth_profile": has_auth_profile,
        "cookies_count": cookie_check["count"],
        "missing_required_cookies": cookie_check["missing"],
        "auth_ok": auth_ok,
        "auth_file_private_ok": _permissions_private_ok(resolved_auth_dir / "auth.json"),
        "mode_file_private_ok": _permissions_private_ok(mode_file),
        "ready": ready,
        "next_steps": android_steps,
    }


def build_uvx_shim_script(is_runtime_bridge: bool = True) -> str:
    """Build POSIX /system/bin/sh smart uvx shim (never prints to stdout)."""
    if is_runtime_bridge:
        path_init = (
            'if [ -z "${HOME:-}" ]; then HOME="$(cd -- "$(dirname -- "$0")/../.." 2>/dev/null && pwd)"; export HOME; fi\n'
            'if [ -z "${PREFIX:-}" ]; then PREFIX="$HOME/usr"; export PREFIX; fi\n'
        )
    else:
        path_init = (
            'if [ -z "${PREFIX:-}" ]; then PREFIX="$(cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd)"; export PREFIX; fi\n'
            'if [ -z "${HOME:-}" ]; then HOME="$(cd -- "$PREFIX/.." 2>/dev/null && pwd)"; export HOME; fi\n'
        )

    return (
        "#!/system/bin/sh\n"
        f"{SHIM_MARKER}\n"
        f"{path_init}"
        'AUTH_DIR="$HOME/.notebooklm-mcp-cli"\n'
        'MODE_FILE="$AUTH_DIR/android-mode.json"\n'
        'HELPER_SCRIPT="$HOME/.local/share/agy-nlm/nlm_connect.py"\n'
        "\n"
        "IS_NLM=0\n"
        'for _arg in "$@"; do\n'
        '    case "$_arg" in\n'
        "        *notebooklm-mcp-cli*)\n"
        "            IS_NLM=1\n"
        "            break\n"
        "            ;;\n"
        "    esac\n"
        "done\n"
        "\n"
        'if [ "$IS_NLM" -eq 0 ]; then\n'
        '    export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
        '    if [ -f "$PREFIX/lib/libtermux-exec.so" ]; then\n'
        '        export LD_PRELOAD="$PREFIX/lib/libtermux-exec.so"\n'
        "    else\n"
        "        unset LD_PRELOAD 2>/dev/null || true\n"
        "    fi\n"
        '    export PATH="$PREFIX/bin:/system/bin"\n'
        '    export OPENSSL_CONF="$PREFIX/etc/tls/openssl.cnf"\n'
        '    export SSL_CERT_FILE="$PREFIX/etc/tls/cert.pem"\n'
        '    export CURL_CA_BUNDLE="$PREFIX/etc/tls/cert.pem"\n'
        '    export GODEBUG="netdns=cgo"\n'
        '    if [ -x "$PREFIX/bin/uvx.real" ]; then\n'
        '        exec "$PREFIX/bin/uvx.real" "$@"\n'
        "    fi\n"
        "    printf 'agy-uvx-shim: missing %s/bin/uvx.real (run: pkg install uv)\\n' \"$PREFIX\" >&2\n"
        "    exit 127\n"
        "fi\n"
        "\n"
        "find_nlm_subcmd() {\n"
        "    _skip_next=0\n"
        '    for _a in "$@"; do\n'
        '        if [ "$_skip_next" -eq 1 ]; then\n'
        "            _skip_next=0\n"
        "            continue\n"
        "        fi\n"
        '        case "$_a" in\n'
        "            --from|--with|--python|-p|--index-url|-i|--extra-index-url|--find-links|-f|--cache-dir|--python-preference|--constraint|-c|--override|--exclude-newer)\n"
        "                _skip_next=1\n"
        "                ;;\n"
        "            --*|-*)\n"
        "                ;;\n"
        "            *)\n"
        '                printf \'%s\\n\' "$_a"\n'
        "                return 0\n"
        "                ;;\n"
        "        esac\n"
        "    done\n"
        "    return 1\n"
        "}\n"
        "\n"
        'MODE="proot"\n'
        'DISTRO="debian"\n'
        'if [ -f "$MODE_FILE" ]; then\n'
        '    _m="$(sed -n \'s/.*"mode"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p\' "$MODE_FILE" 2>/dev/null | head -n 1)"\n'
        '    [ -n "$_m" ] && MODE="$_m"\n'
        '    _d="$(sed -n \'s/.*"distro"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p\' "$MODE_FILE" 2>/dev/null | head -n 1)"\n'
        '    [ -n "$_d" ] && DISTRO="$_d"\n'
        "fi\n"
        "\n"
        'SUBCMD="$(find_nlm_subcmd "$@")" || SUBCMD=""\n'
        "\n"
        'if [ "$MODE" = "remote" ] && { [ "$SUBCMD" = "notebooklm-mcp" ] || [ -z "$SUBCMD" ]; }; then\n'
        "    unset LD_PRELOAD 2>/dev/null || true\n"
        "    export PREFIX HOME\n"
        '    export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
        '    export PATH="$PREFIX/bin:/system/bin"\n'
        '    export SSL_CERT_FILE="$PREFIX/etc/tls/cert.pem"\n'
        '    export CURL_CA_BUNDLE="$PREFIX/etc/tls/cert.pem"\n'
        "    export PYTHONUTF8=1\n"
        '    if [ ! -f "$HELPER_SCRIPT" ]; then\n'
        "        printf 'agy-uvx-shim: missing remote proxy helper %s\\n' \"$HELPER_SCRIPT\" >&2\n"
        "        exit 127\n"
        "    fi\n"
        '    PY_BIN="$PREFIX/bin/python3"\n'
        '    [ -x "$PY_BIN" ] || PY_BIN="$(command -v python3 2>/dev/null || true)"\n'
        '    if [ -z "$PY_BIN" ]; then\n'
        "        printf 'agy-uvx-shim: python3 not found for remote-proxy\\n' >&2\n"
        "        exit 127\n"
        "    fi\n"
        '    exec "$PY_BIN" "$HELPER_SCRIPT" remote-proxy\n'
        "fi\n"
        "\n"
        "unset LD_PRELOAD 2>/dev/null || true\n"
        "export PREFIX HOME\n"
        'export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
        'export PATH="$PREFIX/bin:/system/bin"\n'
        'export SSL_CERT_FILE="$PREFIX/etc/tls/cert.pem"\n'
        'export CURL_CA_BUNDLE="$PREFIX/etc/tls/cert.pem"\n'
        "\n"
        'PROOT_DISTRO="$PREFIX/bin/proot-distro"\n'
        'if [ ! -x "$PROOT_DISTRO" ]; then\n'
        '    PROOT_DISTRO="$(command -v proot-distro 2>/dev/null || true)"\n'
        "fi\n"
        'if [ -z "$PROOT_DISTRO" ] || [ ! -x "$PROOT_DISTRO" ]; then\n'
        "    printf 'agy-uvx-shim: proot-distro not found. Run /notebooklm-connect setup first.\\n' >&2\n"
        "    exit 127\n"
        "fi\n"
        "\n"
        'mkdir -p "$AUTH_DIR" 2>/dev/null || true\n'
        'ROOTFS="$PREFIX/var/lib/proot-distro/installed-rootfs/$DISTRO"\n'
        "\n"
        'if [ -n "$SUBCMD" ] && [ -x "$ROOTFS/root/.local/bin/$SUBCMD" ]; then\n'
        "    _skip_next=0\n"
        '    while [ "$#" -gt 0 ]; do\n'
        '        if [ "$_skip_next" -eq 1 ]; then\n'
        "            _skip_next=0\n"
        "            shift\n"
        "            continue\n"
        "        fi\n"
        '        case "$1" in\n'
        "            --from|--with|--python|-p|--index-url|-i|--extra-index-url|--find-links|-f|--cache-dir|--python-preference|--constraint|-c|--override|--exclude-newer)\n"
        "                _skip_next=1\n"
        "                shift\n"
        "                ;;\n"
        "            --*|-*)\n"
        "                shift\n"
        "                ;;\n"
        "            *)\n"
        "                shift\n"
        "                break\n"
        "                ;;\n"
        "        esac\n"
        "    done\n"
        '    if [ -d /storage/emulated/0 ]; then\n'
        '        exec "$PROOT_DISTRO" login "$DISTRO" --shared-tmp \\\n'
        '            --bind "$AUTH_DIR:/root/.notebooklm-mcp-cli" \\\n'
        '            --bind "/storage/emulated/0:/storage/emulated/0" \\\n'
        "            -- env -u LD_PRELOAD -u LD_LIBRARY_PATH \\\n"
        "            HOME=/root PYTHONUTF8=1 \\\n"
        "            PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\\n"
        f'            "NOTEBOOKLM_QUERY_TIMEOUT=${{NOTEBOOKLM_QUERY_TIMEOUT:-{DEFAULT_QUERY_TIMEOUT}}}" \\\n'
        '            ${NOTEBOOKLM_DISABLED_GROUPS:+"NOTEBOOKLM_DISABLED_GROUPS=$NOTEBOOKLM_DISABLED_GROUPS"} \\\n'
        '            ${NOTEBOOKLM_BASE_URL:+"NOTEBOOKLM_BASE_URL=$NOTEBOOKLM_BASE_URL"} \\\n'
        '            "/root/.local/bin/$SUBCMD" "$@"\n'
        "    else\n"
        '        exec "$PROOT_DISTRO" login "$DISTRO" --shared-tmp \\\n'
        '            --bind "$AUTH_DIR:/root/.notebooklm-mcp-cli" \\\n'
        "            -- env -u LD_PRELOAD -u LD_LIBRARY_PATH \\\n"
        "            HOME=/root PYTHONUTF8=1 \\\n"
        "            PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\\n"
        f'            "NOTEBOOKLM_QUERY_TIMEOUT=${{NOTEBOOKLM_QUERY_TIMEOUT:-{DEFAULT_QUERY_TIMEOUT}}}" \\\n'
        '            ${NOTEBOOKLM_DISABLED_GROUPS:+"NOTEBOOKLM_DISABLED_GROUPS=$NOTEBOOKLM_DISABLED_GROUPS"} \\\n'
        '            ${NOTEBOOKLM_BASE_URL:+"NOTEBOOKLM_BASE_URL=$NOTEBOOKLM_BASE_URL"} \\\n'
        '            "/root/.local/bin/$SUBCMD" "$@"\n'
        "    fi\n"
        "fi\n"
        "\n"
        'if [ -x "$ROOTFS/root/.local/bin/uvx" ]; then\n'
        '    if [ -d /storage/emulated/0 ]; then\n'
        '        exec "$PROOT_DISTRO" login "$DISTRO" --shared-tmp \\\n'
        '            --bind "$AUTH_DIR:/root/.notebooklm-mcp-cli" \\\n'
        '            --bind "/storage/emulated/0:/storage/emulated/0" \\\n'
        "            -- env -u LD_PRELOAD -u LD_LIBRARY_PATH \\\n"
        "            HOME=/root PYTHONUTF8=1 \\\n"
        "            PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\\n"
        f'            "NOTEBOOKLM_QUERY_TIMEOUT=${{NOTEBOOKLM_QUERY_TIMEOUT:-{DEFAULT_QUERY_TIMEOUT}}}" \\\n'
        '            ${NOTEBOOKLM_DISABLED_GROUPS:+"NOTEBOOKLM_DISABLED_GROUPS=$NOTEBOOKLM_DISABLED_GROUPS"} \\\n'
        '            ${NOTEBOOKLM_BASE_URL:+"NOTEBOOKLM_BASE_URL=$NOTEBOOKLM_BASE_URL"} \\\n'
        '            /root/.local/bin/uvx "$@"\n'
        "    else\n"
        '        exec "$PROOT_DISTRO" login "$DISTRO" --shared-tmp \\\n'
        '            --bind "$AUTH_DIR:/root/.notebooklm-mcp-cli" \\\n'
        "            -- env -u LD_PRELOAD -u LD_LIBRARY_PATH \\\n"
        "            HOME=/root PYTHONUTF8=1 \\\n"
        "            PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\\n"
        f'            "NOTEBOOKLM_QUERY_TIMEOUT=${{NOTEBOOKLM_QUERY_TIMEOUT:-{DEFAULT_QUERY_TIMEOUT}}}" \\\n'
        '            ${NOTEBOOKLM_DISABLED_GROUPS:+"NOTEBOOKLM_DISABLED_GROUPS=$NOTEBOOKLM_DISABLED_GROUPS"} \\\n'
        '            ${NOTEBOOKLM_BASE_URL:+"NOTEBOOKLM_BASE_URL=$NOTEBOOKLM_BASE_URL"} \\\n'
        '            /root/.local/bin/uvx "$@"\n'
        "    fi\n"
        "fi\n"
        "\n"
        "printf 'agy-uvx-shim: missing %s/root/.local/bin/%s (run /notebooklm-connect)\\n' \"$ROOTFS\" \"${SUBCMD:-notebooklm-mcp}\" >&2\n"
        "exit 127\n"
    )


def _write_mode_config(
    auth_dir: Path,
    mode: str,
    distro: str = DEFAULT_DISTRO,
    remote_url: str = "",
    bearer_token: str = "",
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    existing = load_android_mode(auth_dir)
    if mode not in ("proot", "remote"):
        raise ValueError(f"Unsupported mode: {mode}")

    final_url = remote_url.strip() if remote_url.strip() else existing.get("url", "")
    final_token = bearer_token.strip() if bearer_token.strip() else existing.get("bearer_token", "")
    final_headers = dict(existing.get("headers") or {})
    if headers:
        final_headers.update(headers)

    if mode == "remote" and not final_url:
        raise ValueError("--remote-url is required when setting remote mode")

    data = {
        "mode": mode,
        "distro": distro.strip() or existing.get("distro") or DEFAULT_DISTRO,
        "url": final_url,
        "bearer_token": final_token,
        "headers": final_headers,
        "updated_at": _now_iso(),
    }
    write_json_secure(auth_dir / "android-mode.json", data, private=True)
    return data


def _write_lf_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        tmp_path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
        _chmod_if_posix(tmp_path, 0o755)
        os.replace(tmp_path, path)
        _chmod_if_posix(path, 0o755)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def install_shim(
    mode: str = "proot",
    distro: str = DEFAULT_DISTRO,
    remote_url: str = "",
    bearer_token: str = "",
    bearer_token_file: Path | None = None,
    delete_token_file: bool = False,
    headers: dict[str, str] | None = None,
    home: Path | None = None,
    prefix: Path | None = None,
    runtime_bin: Path | None = None,
    auth_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Install idempotent Android smart uvx shims + helper copy + android-mode.json."""
    paths = resolve_android_paths(
        home=home,
        prefix=prefix,
        runtime_bin=runtime_bin,
        auth_dir=auth_dir,
        env=env,
    )
    resolved_home = paths["home"]
    resolved_prefix = paths["prefix"]
    resolved_runtime_bin = paths["runtime_bin"]
    resolved_auth_dir = paths["auth_dir"]

    token_value = bearer_token.strip()
    if bearer_token_file is not None:
        token_value = bearer_token_file.read_text(encoding="utf-8").strip()

    saved_mode = _write_mode_config(
        auth_dir=resolved_auth_dir,
        mode=mode,
        distro=distro,
        remote_url=remote_url,
        bearer_token=token_value,
        headers=headers,
    )

    if delete_token_file and bearer_token_file is not None:
        secure_delete_path(bearer_token_file, auth_dir=resolved_auth_dir)

    # Copy helper into internal home dir so runtime/bin shim works across any workspace.
    helper_dest = resolved_home / ".local" / "share" / "agy-nlm" / "nlm_connect.py"
    helper_src = Path(__file__).resolve()
    helper_dest.parent.mkdir(parents=True, exist_ok=True)
    helper_bytes = helper_src.read_bytes().replace(b"\r\n", b"\n")
    helper_dest.write_bytes(helper_bytes)
    _chmod_if_posix(helper_dest, 0o755)

    # Idempotently preserve original $PREFIX/bin/uvx -> uvx.real before writing shim.
    prefix_bin = resolved_prefix / "bin"
    prefix_uvx = prefix_bin / "uvx"
    prefix_uvx_real = prefix_bin / "uvx.real"
    backed_up_real = False
    if prefix_uvx.exists() and not _file_has_marker(prefix_uvx):
        if prefix_uvx.is_symlink():
            target = prefix_uvx.resolve()
            prefix_uvx.unlink()
            shutil.copy2(target, prefix_uvx_real)
        else:
            os.replace(prefix_uvx, prefix_uvx_real)
        _chmod_if_posix(prefix_uvx_real, 0o755)
        backed_up_real = True

    _write_lf_executable(prefix_uvx, build_uvx_shim_script(is_runtime_bridge=False))

    runtime_uvx = resolved_runtime_bin / "uvx"
    _write_lf_executable(runtime_uvx, build_uvx_shim_script(is_runtime_bridge=True))

    return {
        "installed": True,
        "mode": sanitize_mode(saved_mode),
        "mode_file": str(resolved_auth_dir / "android-mode.json"),
        "helper_copy": str(helper_dest),
        "runtime_shim": str(runtime_uvx),
        "prefix_shim": str(prefix_uvx),
        "uvx_real_exists": prefix_uvx_real.is_file(),
        "backed_up_uvx_real": backed_up_real,
        "token_file_deleted": bool(delete_token_file and bearer_token_file is not None),
    }


def _emit_json_line(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _emit_rpc_error(req_id: Any, code: int, message: str) -> None:
    _emit_json_line(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
    )


def _forward_sse_stream(resp: Any) -> None:
    buf: list[str] = []
    while True:
        raw_line = resp.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if line == "":
            if buf:
                payload = "\n".join(buf).strip()
                buf.clear()
                if payload:
                    try:
                        _emit_json_line(json.loads(payload))
                    except json.JSONDecodeError as exc:
                        sys.stderr.write(f"remote-proxy: invalid SSE JSON payload: {exc}\n")
            continue
        if line.startswith("data:"):
            val = line[5:]
            if val.startswith(" "):
                val = val[1:]
            buf.append(val)
    if buf:
        payload = "\n".join(buf).strip()
        if payload:
            try:
                _emit_json_line(json.loads(payload))
            except json.JSONDecodeError as exc:
                sys.stderr.write(f"remote-proxy: invalid trailing SSE JSON payload: {exc}\n")


def run_remote_proxy(
    mode_cfg: Mapping[str, Any] | None = None,
    auth_dir: Path = DEFAULT_AUTH_DIR,
    timeout: int = 180,
) -> int:
    """Zero-dependency MCP stdio <-> Streamable-HTTP proxy (stdout stays JSON-RPC pure)."""
    cfg = dict(mode_cfg) if mode_cfg is not None else load_android_mode(auth_dir)
    url = str(cfg.get("url") or "").strip()
    if not url:
        sys.stderr.write("remote-proxy: remote URL missing in android-mode.json\n")
        return 1

    base_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    custom_headers = cfg.get("headers")
    if isinstance(custom_headers, Mapping):
        for k, v in custom_headers.items():
            if k and v is not None:
                base_headers[str(k)] = str(v)
    token = str(cfg.get("bearer_token") or "").strip()
    if token:
        base_headers["Authorization"] = f"Bearer {token}"

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=_build_ssl_context())
    )
    session_id = ""

    while True:
        raw_line = sys.stdin.readline()
        if not raw_line:
            break
        line = raw_line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"remote-proxy: malformed JSON on stdin: {exc}\n")
            continue

        has_id = isinstance(msg, dict) and ("id" in msg)
        req_id = msg.get("id") if has_id else None

        headers = dict(base_headers)
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        req = urllib.request.Request(
            url,
            data=line.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with opener.open(req, timeout=timeout) as resp:
                new_sid = resp.headers.get("Mcp-Session-Id")
                if new_sid:
                    session_id = new_sid.strip()

                status = int(resp.status)
                if status == 202:
                    continue

                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "text/event-stream" in ctype:
                    _forward_sse_stream(resp)
                else:
                    body = resp.read().decode("utf-8", errors="replace").strip()
                    if body:
                        _emit_json_line(json.loads(body))
        except urllib.error.HTTPError as exc:
            new_sid = exc.headers.get("Mcp-Session-Id") if exc.headers else None
            if new_sid:
                session_id = new_sid.strip()
            err_msg = f"HTTP {exc.code} from remote MCP endpoint: {exc.reason}"
            sys.stderr.write(f"remote-proxy: {err_msg}\n")
            if has_id:
                _emit_rpc_error(req_id, -32000, err_msg)
        except Exception as exc:  # noqa: BLE001
            err_msg = f"Remote MCP request failed: {exc}"
            sys.stderr.write(f"remote-proxy: {err_msg}\n")
            if has_id:
                _emit_rpc_error(req_id, -32000, err_msg)

    return 0


def _cmd_detect(args: argparse.Namespace) -> int:
    info = detect_environment(
        home=Path(args.home) if args.home else None,
        prefix=Path(args.prefix) if args.prefix else None,
        runtime_bin=Path(args.runtime_bin) if args.runtime_bin else None,
        auth_dir=Path(args.auth_dir) if args.auth_dir else None,
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info.get("ready") else 1


def _cmd_health(args: argparse.Namespace) -> int:
    auth_dir = Path(args.auth_dir) if args.auth_dir else DEFAULT_AUTH_DIR
    mode_cfg = load_android_mode(auth_dir)
    target_mode = args.mode or (
        mode_cfg["mode"] if detect_platform() == "android-agy" else "cookie"
    )
    if target_mode == "remote":
        result = remote_endpoint_health(mode_cfg, timeout=args.timeout)
    else:
        result = live_cookie_health(
            auth_dir=auth_dir,
            base_url=args.base_url,
            timeout=args.timeout,
            update_metadata=True,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def _load_cookies_from_pc_dir(pc_dir: Path) -> tuple[dict[str, str], str]:
    email = ""
    meta = _read_json_safe(pc_dir / "profiles" / "default" / "metadata.json")
    if isinstance(meta, dict):
        email = str(meta.get("email") or "")

    profile_cookies = _read_json_safe(pc_dir / "profiles" / "default" / "cookies.json")
    cookies = _normalize_cookie_container(profile_cookies)
    if cookies:
        return cookies, email

    root_auth = _read_json_safe(pc_dir / "auth.json")
    cookies = _normalize_cookie_container(root_auth)
    return cookies, email


def _cmd_import_cookies(args: argparse.Namespace) -> int:
    auth_dir = Path(args.auth_dir) if args.auth_dir else DEFAULT_AUTH_DIR
    source_path: Path | None = None
    email = args.email or ""

    if args.pc_dir:
        source_path = Path(args.pc_dir)
        if not source_path.is_dir():
            raise FileNotFoundError(f"PC auth directory not found: {source_path}")
        cookies, found_email = _load_cookies_from_pc_dir(source_path)
        if not email:
            email = found_email
    elif args.file:
        source_path = Path(args.file)
        if not source_path.is_file():
            raise FileNotFoundError(f"Cookie file not found: {source_path}")
        cookies = parse_cookies_input(source_path.read_text(encoding="utf-8", errors="replace"))
    elif args.stdin:
        cookies = parse_cookies_input(sys.stdin.read())
    else:
        raise ValueError("Provide one of --file, --pc-dir, or --stdin")

    validation = validate_required_cookies(cookies)
    if not validation["ok"]:
        err_payload = {
            "imported": False,
            "error": "Missing required Google SSO cookies (trap T9: copy full Cookie: header from a batchexecute request or sync auth.json from PC).",
            "cookies_count": validation["count"],
            "present_required_cookies": validation["present"],
            "missing_required_cookies": validation["missing"],
        }
        print(json.dumps(err_payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    csrf_token = ""
    session_id = ""
    build_label = ""
    base_host = (args.base_url or DEFAULT_BASE_URL).rstrip("/")
    health_summary: dict[str, Any] = {"checked": False, "ok": None}

    if not args.no_verify:
        health_summary, tokens = _probe_cookies_internal(
            cookies=cookies,
            base_url=base_host,
            timeout=args.timeout,
        )
        if not health_summary.get("ok"):
            print(
                json.dumps(
                    {
                        "imported": False,
                        "error": health_summary.get("error") or "Live cookie verification failed",
                        "health": health_summary,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 1
        csrf_token = tokens.get("csrf_token", "")
        session_id = tokens.get("session_id", "")
        build_label = tokens.get("build_label", "")
        base_host = tokens.get("base_host", base_host)

    written = write_auth_profile(
        cookies=cookies,
        csrf_token=csrf_token,
        session_id=session_id,
        build_label=build_label,
        base_host=base_host,
        email=email,
        auth_dir=auth_dir,
    )

    deleted_source = False
    if args.delete_source and source_path is not None:
        deleted_source = secure_delete_path(source_path, auth_dir=auth_dir)

    print(
        json.dumps(
            {
                "imported": True,
                "cookies_count": len(cookies),
                "verified": not args.no_verify,
                "csrf_ok": bool(csrf_token or session_id),
                "session_id_ok": bool(session_id),
                "base_host": base_host,
                "auth_dir": str(auth_dir),
                "files_written": written,
                "deleted_source": deleted_source,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parse_kv_headers(items: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in items or []:
        if "=" not in raw:
            raise ValueError(f"Invalid --header format (expected Key=Value): {raw}")
        k, v = raw.split("=", 1)
        if k.strip():
            parsed[k.strip()] = v.strip()
    return parsed


def _cmd_install_shim(args: argparse.Namespace) -> int:
    result = install_shim(
        mode=args.mode,
        distro=args.distro,
        remote_url=args.remote_url or "",
        bearer_token=args.bearer_token or "",
        bearer_token_file=Path(args.bearer_token_file) if args.bearer_token_file else None,
        delete_token_file=args.delete_token_file,
        headers=_parse_kv_headers(args.header),
        home=Path(args.home) if args.home else None,
        prefix=Path(args.prefix) if args.prefix else None,
        runtime_bin=Path(args.runtime_bin) if args.runtime_bin else None,
        auth_dir=Path(args.auth_dir) if args.auth_dir else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_set_mode(args: argparse.Namespace) -> int:
    auth_dir = Path(args.auth_dir) if args.auth_dir else DEFAULT_AUTH_DIR
    token_file = Path(args.bearer_token_file) if args.bearer_token_file else None
    token_val = token_file.read_text(encoding="utf-8").strip() if token_file else (args.bearer_token or "")
    saved = _write_mode_config(
        auth_dir=auth_dir,
        mode=args.mode,
        distro=args.distro,
        remote_url=args.remote_url or "",
        bearer_token=token_val,
        headers=_parse_kv_headers(args.header),
    )
    deleted = False
    if args.delete_token_file and token_file is not None:
        deleted = secure_delete_path(token_file, auth_dir=auth_dir)
    print(
        json.dumps(
            {
                "updated": True,
                "mode": sanitize_mode(saved),
                "mode_file": str(auth_dir / "android-mode.json"),
                "token_file_deleted": deleted,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_remote_proxy(args: argparse.Namespace) -> int:
    auth_dir = Path(args.auth_dir) if args.auth_dir else DEFAULT_AUTH_DIR
    return run_remote_proxy(auth_dir=auth_dir, timeout=args.timeout)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NotebookLM MCP cross-platform connector")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_det = sub.add_parser("detect", help="Detect platform, Android shims, Debian proot & auth")
    s_det.add_argument("--home")
    s_det.add_argument("--prefix")
    s_det.add_argument("--runtime-bin")
    s_det.add_argument("--auth-dir")
    s_det.set_defaults(func=_cmd_detect)

    s_hlth = sub.add_parser("health", help="Verify NotebookLM cookies/CSRF or remote MCP endpoint")
    s_hlth.add_argument("--auth-dir")
    s_hlth.add_argument("--mode", choices=["cookie", "remote"])
    s_hlth.add_argument("--base-url", default=DEFAULT_BASE_URL)
    s_hlth.add_argument("--timeout", type=int, default=15)
    s_hlth.set_defaults(func=_cmd_health)

    s_imp = sub.add_parser("import-cookies", help="Validate and store NotebookLM auth profile")
    s_imp.add_argument("--file", help="Path to auth.json, Netscape cookies.txt, or Cookie header text")
    s_imp.add_argument("--pc-dir", help="Path to synced .notebooklm-mcp-cli directory from PC")
    s_imp.add_argument("--stdin", action="store_true", help="Read cookies input from stdin")
    s_imp.add_argument("--email", default="", help="Optional account email metadata")
    s_imp.add_argument("--base-url", default=DEFAULT_BASE_URL)
    s_imp.add_argument("--timeout", type=int, default=15)
    s_imp.add_argument("--no-verify", action="store_true", help="Skip live HTTP verification")
    s_imp.add_argument("--delete-source", action="store_true", help="Securely wipe temp file/dir after success")
    s_imp.add_argument("--auth-dir")
    s_imp.set_defaults(func=_cmd_import_cookies)

    s_shim = sub.add_parser("install-shim", help="Install Android smart uvx shim (no Git edits)")
    s_shim.add_argument("--mode", choices=["proot", "remote"], default="proot")
    s_shim.add_argument("--distro", default=DEFAULT_DISTRO)
    s_shim.add_argument("--remote-url", default="")
    s_shim.add_argument("--bearer-token", default="")
    s_shim.add_argument("--bearer-token-file")
    s_shim.add_argument("--delete-token-file", action="store_true")
    s_shim.add_argument("--header", action="append", help="Extra remote header as Key=Value")
    s_shim.add_argument("--home")
    s_shim.add_argument("--prefix")
    s_shim.add_argument("--runtime-bin")
    s_shim.add_argument("--auth-dir")
    s_shim.set_defaults(func=_cmd_install_shim)

    s_mode = sub.add_parser("set-mode", help="Switch Android mode between proot and remote")
    s_mode.add_argument("--mode", choices=["proot", "remote"], required=True)
    s_mode.add_argument("--distro", default=DEFAULT_DISTRO)
    s_mode.add_argument("--remote-url", default="")
    s_mode.add_argument("--bearer-token", default="")
    s_mode.add_argument("--bearer-token-file")
    s_mode.add_argument("--delete-token-file", action="store_true")
    s_mode.add_argument("--header", action="append", help="Extra remote header as Key=Value")
    s_mode.add_argument("--auth-dir")
    s_mode.set_defaults(func=_cmd_set_mode)

    s_prx = sub.add_parser("remote-proxy", help="Run MCP stdio <-> Streamable-HTTP proxy")
    s_prx.add_argument("--auth-dir")
    s_prx.add_argument("--timeout", type=int, default=180)
    s_prx.set_defaults(func=_cmd_remote_proxy)

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
