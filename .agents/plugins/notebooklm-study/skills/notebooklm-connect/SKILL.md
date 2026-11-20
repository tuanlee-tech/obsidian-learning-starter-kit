---
name: notebooklm-connect
description: >-
  Cross-platform NotebookLM MCP installer, diagnostics, cookie/auth manager,
  and Android fast-path bridge (Windows / macOS / Linux / Antigravity for Android).
  Use whenever the user runs `/notebooklm-connect`, asks to install or fix the
  NotebookLM MCP connection ("kết nối notebooklm", "cài mcp", "cập nhật cookie",
  "đăng nhập notebooklm", "chuyển remote mcp", "fix mcp android"), or when
  `study-init` / `study-day-init` / `study-session-and-sync` detects missing
  MCP tools, missing `uv`/Debian proot shim, or expired auth cookies.
---

# NotebookLM MCP Connector & Cross-Platform Fast-Path

Configure, diagnose, and repair the `notebooklm` MCP stack across **Windows, macOS, Linux, and Antigravity for Android (AGY)** while keeping `.agents/plugins/notebooklm-study/mcp_config.json` untouched in Git and preserving **all 10 NotebookLM MCP tools** (`server_info`, `notebook_list`, `notebook_create`, `source_add` across `url`/`file`/`drive`/`text`, `notebook_get`, `chat_configure`, `chat_get`, `notebook_query_start`, `notebook_query_status`, `refresh_auth`).

---

## Hard-Earned Android Fast-Path Cache (DO NOT Repeat Dead-Ends `T1`–`T10`)

On **Antigravity for Android (`android-agy`, ARM64 / Bionic libc)**, follow these strict rules:
- **NEVER `T1`:** Run native `uvx --from notebooklm-mcp-cli ...` directly on Android Bionic before installing the AGY smart `uvx` shim (`pydantic-core` & `watchfiles` fail in `maturin`/`rustup`).
- **NEVER `T2`:** Run `pkg install python-cryptography` / `python-rpds-py` expecting `uvx` to reuse them (`uvx` creates isolated venvs without `--system-site-packages`).
- **NEVER `T3`:** Run `uv python install ...` (`python-build-standalone` has no Android builds).
- **NEVER `T4`:** Install `tur-repo` expecting AGY's `pkg` to read `sources.list.d/` (`pkg` only reads `$PREFIX/etc/pkg/repo.conf`).
- **NEVER `T5`:** Use `python-pip` unpatched if pip is ever needed (Termux's `pip/_vendor/certifi/cacert.pem` symlink points to `/data/data/com.termux/...` and throws `PermissionError` until relinked to `$PREFIX/etc/tls/cert.pem`).
- **NEVER `T6`:** Extract `manylinux` wheels onto Bionic libc (`dlopen` fails at `libpthread.so.0 not found`).
- **NEVER `T7`:** Run `pkg install rust` to compile `pydantic-core` on device (~350–500 MB toolchain + OOM risk on ~1.2 GB available RAM).
- **NEVER `T8`:** Run `pkg install nodejs-lts` on AGY (`nodejs` 26 conflicts with `nodejs-lts`).
- **ALWAYS `T9`:** Validate all 5 Google SSO cookies (`SID`, `HSID`, `SSID`, `APISID`, `SAPISID`) before saving. Host-only exports from `notebook.google.com` extensions omit `.google.com` SSO cookies and fail auth.
- **ALWAYS `T10`:** If `pkg install` fails mid-download (`curl: (56) Recv failure`), retry 1–2 times before aborting.
- **ALWAYS Respect `noexec`:** `/storage/emulated/0` is mounted `noexec`; invoke all scripts explicitly via `python` or `bash`.
- **ZERO Git Leaks & ZERO Git Drift:** NEVER edit `.agents/plugins/notebooklm-study/mcp_config.json`, NEVER store raw cookies/tokens inside Git-tracked files or `mcp_config.json`, NEVER print raw cookie/token strings in output, and ALWAYS pass `--delete-source` / `--delete-token-file` when importing temporary credential files.

---

## Step 0: Universal Environment & Health Probe (Always Run First)

Run the zero-dependency probe (`python` on Windows/Android, `python3` on macOS/Linux):

```bash
python .agents/plugins/notebooklm-study/scripts/nlm_connect.py detect
python .agents/plugins/notebooklm-study/scripts/nlm_connect.py health
```

*(Non-zero exit simply reports not-ready; inspect the JSON output rather than treating it as a crash.)*

Present a concise **Connection Status Table**:

| Thành phần | Trạng thái | Chi tiết |
|---|---|---|
| Nền tảng / Chế độ | `windows` / `macos` / `linux` / `android-agy (proot | remote)` | — |
| Runtime (`uv`/`uvx` hoặc `proot-distro` + Debian + shim) | ✅ / ❌ | Đường dẫn & lớp đã cài sẵn |
| Xác thực / Endpoint (`auth.json` hoặc Remote URL) | ✅ / ❌ | Số cookies (`>= 5` SSO keys) + CSRF / HTTP probe |
| Kết nối MCP sống (`server_info` + `notebook_list`) | ✅ / ❌ | Nếu MCP tools đã nạp trong phiên |

**Routing:**
- If `platform != "android-agy"` ➔ follow **Flow A (PC)**.
- If `platform == "android-agy"`:
  - If user asked to update cookies / auth expired ➔ jump to **Flow D**.
  - If user asked to switch mode (`proot` ↔ `remote`) ➔ follow **Flow E** (or **Flow C** if configuring remote URL for the first time).
  - If Android setup is incomplete (`ready == false`) ➔ use `ask_question` ONCE to choose runtime profile (skip if user already chose):
    1. `(Recommended) Local proot-distro Debian (~350–500 MB disk, giữ đủ 100% 10 MCP tools & upload file cục bộ sources/)` ➔ **Flow B**
    2. `Remote MCP Server (kết nối tới PC/VPS qua Tailscale / Streamable-HTTP, 0 tải nặng cho điện thoại)` ➔ **Flow C**

---

## Flow A: PC Setup & Login (Windows / macOS / Linux)

1. **Install `uv` if missing (`uv == null` or `uvx == null`):**
   - **Windows (PowerShell):**
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - **macOS / Linux:**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
2. **Login to NotebookLM (Chrome CDP browser flow):**
   ```bash
   uvx --from "notebooklm-mcp-cli>=0.16.5" nlm login
   ```
   *(Recommend logging in with a dedicated secondary Google study account.)*
3. **Verify:**
   ```bash
   python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live
   ```
   Then run `server_info()` and `notebook_list()` if MCP tools are active (or ask the user to start a fresh Antigravity chat if `uvx` was just installed).

---

## Flow B: Android Default Setup (`proot-distro` Debian + Smart `uvx` Shim)

Execute only the missing layers reported by `detect` (do NOT reinstall existing layers):

1. **Install `proot-distro` (skip if `proot_distro_installed == true`; never pass `-y` to `pkg`; retry 1–2x on `T10`):**
   ```bash
   pkg update && pkg install proot-distro
   ```
2. **Install Debian rootfs (skip if `debian_installed == true`):**
   ```bash
   proot-distro install debian
   ```
3. **Install `uv` + `notebooklm-mcp-cli>=0.16.5` inside Debian (skip if `debian_nlm_installed == true`):**
   Debian provides glibc + `libpthread.so.0`, so `uv` downloads prebuilt `manylinux` wheels in seconds with **zero compilation**:
   ```bash
   proot-distro login debian --shared-tmp -- bash -lc 'set -e; export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y --no-install-recommends curl ca-certificates; [ -x "$HOME/.local/bin/uv" ] || curl -LsSf https://astral.sh/uv/install.sh | sh; "$HOME/.local/bin/uv" tool install --upgrade "notebooklm-mcp-cli>=0.16.5"'
   ```
4. **Install the non-invasive smart `uvx` shim (`proot` mode, zero edits to Git `mcp_config.json`):**
   ```bash
   python .agents/plugins/notebooklm-study/scripts/nlm_connect.py install-shim --mode proot --distro debian
   ```
   This installs `# AGY_NLM_SHIM v1` into `$HOME/runtime/bin/uvx` and `$PREFIX/bin/uvx` (preserving `uvx.real` for non-NotebookLM packages), bind-mounting `$HOME/.notebooklm-mcp-cli` ➔ `/root/.notebooklm-mcp-cli` and `/storage/emulated/0` ➔ `/storage/emulated/0` (so local `sources/*.pdf` paths work 1:1).
5. **Auth check:** If `auth_ok == false` (or `health` fails), execute **Flow D** right now.
6. **Verify through the exact MCP entry point & reload:**
   ```bash
   uvx --from "notebooklm-mcp-cli>=0.16.5" nlm doctor
   python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live
   ```
   Ask the user to **open a fresh Antigravity chat** (so `mcp_config.json` spawns the newly shimmed `uvx`), then verify `server_info()` and `notebook_list()`.

---

## Flow C: Android Remote MCP Setup (PC / VPS via Tailscale or Streamable-HTTP)

> **Security Warning:** Run the remote server **ONLY** over a private Tailscale/WireGuard IP, SSH tunnel, or HTTPS reverse proxy protected by a Bearer token. **NEVER** expose an unauthenticated MCP port (`--host 0.0.0.0`) directly to the public internet.

1. **On your PC / VPS:** Ensure `nlm login` is done, then launch Streamable-HTTP transport bound to your Tailscale IP (passing your `NOTEBOOKLM_DISABLED_GROUPS` setting):
   ```bash
   NOTEBOOKLM_QUERY_TIMEOUT=180 NOTEBOOKLM_DISABLED_GROUPS="studio,sharing,research,organization,automation,query_multi,usage" \
     uvx --from "notebooklm-mcp-cli>=0.16.5" notebooklm-mcp --transport http --host <TAILSCALE_IP> --port 8000
   ```
   *(Typical URL: `http://<TAILSCALE_IP>:8000/mcp` — confirm exact endpoint path reported on startup.)*
2. **Collect Remote Endpoint Details on Android:** Ask for the URL (and if using a Bearer-protected reverse proxy, ask the user to put the token in a temporary file like `/storage/emulated/0/Documents/remote-token.txt` rather than pasting long-lived secrets in chat).
3. **Install / switch shim to `remote` mode (runs pure-stdlib `nlm_connect.py remote-proxy`):**
   ```bash
   python .agents/plugins/notebooklm-study/scripts/nlm_connect.py install-shim \
     --mode remote --remote-url "http://<TAILSCALE_IP>:8000/mcp"
   ```
   *(If using Bearer auth from a temporary file, append `--bearer-token-file "/storage/emulated/0/Documents/remote-token.txt" --delete-token-file`.)*
4. **Verify live endpoint:**
   ```bash
   python .agents/plugins/notebooklm-study/scripts/nlm_connect.py health --mode remote
   python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live
   ```
   Ask the user to open a fresh Antigravity chat to load MCP tools (`server_info()`, `notebook_list()`).
   *(Note: in `remote` mode, `source_add(source_type="file")` reads files from the remote server host unless synced; use Drive/URL/Text or sync `sources/` to the PC/VPS.)*

---

## Flow D: Safe Cookie Import & Refresh on Android (Every 1–3 Weeks)

> **Account Recommendation:** Strongly advise using a **secondary Google account** dedicated to NotebookLM study instead of your primary personal/banking Google account.

Use `ask_question` to let the user pick how to supply cookies:

- **Method A — Sync from PC (Easiest & Zero DevTools):**
  1. On a PC where Chrome is installed, run `uvx --from "notebooklm-mcp-cli>=0.16.5" nlm login`.
  2. Copy `~/.notebooklm-mcp-cli/auth.json` (or the whole `~/.notebooklm-mcp-cli` directory) to `/storage/emulated/0/Documents/auth.json` (via Syncthing, Google Drive, or USB).
  3. Import & securely wipe the copy in shared storage:
     ```bash
     python .agents/plugins/notebooklm-study/scripts/nlm_connect.py import-cookies \
       --file "/storage/emulated/0/Documents/auth.json" --delete-source
     ```
     *(Use `--pc-dir "/storage/emulated/0/Documents/nlm-sync"` if a whole folder was copied.)*

- **Method B — Direct Browser `Cookie:` Header (Avoids Extension Trap `T9`):**
  1. Tell the user clearly: **DO NOT** use simple "export cookies on `notebook.google.com`" browser extensions alone (Trap `T9` drops `.google.com` SSO cookies).
  2. Guide the user: Open `https://notebook.google.com` (logged in) ➔ Browser DevTools (or desktop remote DevTools / Kiwi/Edge DevTools) ➔ **Network** tab ➔ filter `batchexecute` ➔ click any `batchexecute` request ➔ **Request Headers** ➔ copy the full **`Cookie:`** header value and save it into a temporary file `/storage/emulated/0/Documents/cookies.txt`.
  3. Import, verify live against `https://notebook.google.com`, save (`0700`/`0600`) to `~/.notebooklm-mcp-cli/`, and **securely zero-fill + delete** the temporary file in one command:
     ```bash
     python .agents/plugins/notebooklm-study/scripts/nlm_connect.py import-cookies \
       --file "/storage/emulated/0/Documents/cookies.txt" --delete-source
     ```

If `import-cookies` rejects missing `SID/HSID/SSID/APISID/SAPISID` or login redirect `302`, report which SSO keys were missing (Trap `T9`) without printing any cookie values, and ask them to re-copy from `batchexecute`.

---

## Flow E: Mode Switching & Context Window Hygiene

1. **Instant `proot` ↔ `remote` Toggle (Zero Git Changes):**
   - Switch to local Debian `proot`:
     ```bash
     python .agents/plugins/notebooklm-study/scripts/nlm_connect.py set-mode --mode proot
     ```
   - Switch to Remote MCP:
     ```bash
     python .agents/plugins/notebooklm-study/scripts/nlm_connect.py set-mode --mode remote --remote-url "http://<TAILSCALE_IP>:8000/mcp"
     ```
   Then start a fresh chat for MCP server respawn.
2. **Context Window Savings:**
   - Verify `.agents/plugins/notebooklm-study/mcp_config.json` keeps `"NOTEBOOKLM_DISABLED_GROUPS": "studio,sharing,research,organization,automation,query_multi,usage"` so only core study/source/chat/query/auth tools load (~10 tools instead of ~35).
   - Remind the user that when doing coding/other tasks unrelated to NotebookLM, they can temporarily toggle **`notebooklm-study`** off in **Plugins Manager** (`[notebooklm-study](customization://notebooklm-study)`) so zero MCP tool schemas consume context, then re-enable it before starting `/init` or `/teach`.
