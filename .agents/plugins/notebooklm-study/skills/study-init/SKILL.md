---
name: study-init
description: >-
  Use this skill when the user runs `/init`, asks to initialize a new learning
  vault/domain, sets up a freshly cloned vault on a new machine, or asks to run
  a health check on the NotebookLM MCP connection, `uv`/`uvx`, auth cookies, and
  prompt configuration ("khởi tạo", "kiểm tra kết nối", "health check", "cài mcp").
---

# Vault Init & NotebookLM MCP Health Check

Run a full cross-platform health check of the NotebookLM MCP stack (Windows / macOS / Linux), auto-heal or guide any missing prerequisite in 1 step, and — if the vault is Clean Slate — execute the 4-question domain onboarding flow from `CLAUDE.md` §0.

## Phase 1: Full Environment & Live MCP Health Check (Always Run First)

1. **Local Environment, Auth Profile & Prompt Budget Check:**
   Run the cross-platform helper (`python` on Windows or `python3` on macOS/Linux):
   ```bash
   python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live
   ```
   Inspect:
   - `uv` & `uvx` installed on `PATH`
   - `doctor.version >= 0.16.5`, `doctor.cookies_count > 0`, `doctor.csrf_ok == true`, `doctor.account`
   - `prompt_check.ok == true` (`docs/notebooklm-system-prompt.md <= 8,350` chars from `# SYSTEM INSTRUCTION`)
   - `sources_dir_exists == true`
   - `clean_slate`: `true` if `CLAUDE.md` still has `CHƯA KHỞI TẠO (CLEAN SLATE)`

2. **Live MCP Connectivity Ping:**
   If the `notebooklm` MCP server tools are loaded in this Antigravity session:
   - Call `server_info()` to verify the MCP server process responds cleanly.
   - Call `notebook_list()` to verify live authenticated access to Google NotebookLM and count existing notebooks.
   If MCP tools are NOT yet loaded:
   - Direct the user to verify/enable `[notebooklm-study](customization://notebooklm-study)` (or open a fresh Antigravity chat after installing `uv`).

3. **Present a Crisp Health Check Table:**

| Thành phần | Trạng thái | Chi tiết |
|---|---|---|
| `uv` / `uvx` (đa nền tảng) | ✅ / ❌ | Đường dẫn hoặc lệnh cài 1 bước theo OS |
| `notebooklm-mcp-cli` | ✅ / ❌ | Phiên bản (`>= 0.16.5`) |
| Đăng nhập NotebookLM (`nlm doctor`) | ✅ / ❌ | Tài khoản, số cookies, CSRF token |
| Kết nối MCP sống (`server_info` + `notebook_list`) | ✅ / ❌ | Số notebook đang kết nối được |
| Prompt mẫu (`docs/notebooklm-system-prompt.md`) | ✅ / ❌ | `X / 8.350` ký tự |
| Trạng thái Vault (`CLAUDE.md`) | ✅ Đã khởi tạo / ⏳ Clean Slate | Sẵn sàng học hoặc tiếp tục Phase 2 `/init` |

4. **Auto-Remediation (If Anything is `❌`):**
   - Missing `uv`: print/run the exact OS command returned in `next_steps` (`irm https://astral.sh/uv/install.ps1 | iex` on Windows; `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux).
   - Expired or missing NotebookLM cookies: try MCP `refresh_auth()` first; if headless refresh fails, run:
     ```bash
     uvx --from "notebooklm-mcp-cli>=0.16.5" nlm login
     ```
   - Re-verify until all checks are `✅`.

---

## Phase 2: Clean-Slate Domain Onboarding (Run Automatically When `clean_slate == true`)

If `CLAUDE.md` is still in `CHƯA KHỞI TẠO (CLEAN SLATE)` state (e.g., fresh clone of `obsidian-learning-starter-kit`):

1. Read [CLAUDE.md](../../../../../CLAUDE.md) §0 and interview the user with the **4 concise questions** (domain & goal, current level & weekly hours, existing sources vs Agent-curated sources, 3-tier depth labels & practical example style).
2. Immediately after receiving answers, execute the complete setup:
   - Update `CLAUDE.md` §2 (domain, goal, 3 depth tiers, practical example format, mark `ĐÃ KHỞI TẠO`).
   - Personalize `docs/notebooklm-system-prompt.md` (role, 3 depth labels, example format) and **verify `<= 8,350` chars** via `study_helper.py check-prompt`.
   - Design `docs/roadmap.md` (`🌱 CORE-TRUNK` + `🚀 TRACK-DEEP-DIVE`).
   - Initialize `wiki/00-master-hub.md`, `wiki/00-core-trunk/00-hub-core-trunk.md`, and module `00-index-*.md` catalogs.
   - Activate `weekly-study-plan` to generate **Week 1 (`docs/lich-hoc-tuan-1.md`, 5 days)** and validate with `study_helper.py check-week docs/lich-hoc-tuan-1.md`.
3. Hand back the ready-to-study summary and invite the user to start Day 1 with *"Tạo bài W1D1"*.
