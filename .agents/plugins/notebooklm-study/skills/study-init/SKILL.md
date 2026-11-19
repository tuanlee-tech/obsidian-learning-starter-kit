---
name: study-init
description: >-
  Use this skill when the user runs `/init`, asks to initialize a new learning
  vault/domain (Clean Slate), sets up a freshly cloned vault on a new machine,
  asks to run a health check on the NotebookLM MCP connection (`uv`/`uvx`, auth
  cookies, prompt budget — "khởi tạo", "kiểm tra kết nối", "health check",
  "cài mcp"), or asks to re-benchmark an existing roadmap against fresh JDs or
  exam blueprints ("cập nhật roadmap theo JD mới", "re-benchmark roadmap").
---

# Vault Init, NotebookLM MCP Health Check & Demand-Driven Scope Setup

Run a full cross-platform health check of the NotebookLM MCP stack (Windows / macOS / Linux), auto-heal or guide any missing prerequisite in 1 step, and — if the vault is Clean Slate — execute the **Adaptive Discovery → 4-Mode Ground-Truth Anchor (JD / Syllabus / Spec) → Blueprint Approval Gate → Full Repo Scaffold** workflow from `CLAUDE.md` §0. On already-initialized vaults, safely stop after Health Check unless the user explicitly asks to run a non-destructive Re-Benchmark (Phase 3).

---

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

5. **Post-Health-Check Routing:**
   - If `clean_slate == false` and the user only requested `/init`, `"kiểm tra kết nối"`, or `"health check"` → report **✅ Vault đã khởi tạo và sẵn sàng học** and **STOP** (never overwrite an existing vault). Add a 1-line tip: *"Nếu muốn đối chiếu/mở rộng Roadmap theo JD hoặc chuẩn mới, nhắn: `Cập nhật Roadmap theo JD mới`."*
   - If `clean_slate == false` and the user explicitly requested a re-benchmark → jump to **Phase 3**.
   - If `clean_slate == true` → proceed to **Phase 2**.

---

## Phase 2: Clean-Slate Domain Onboarding (Adaptive Discovery & Ground-Truth Anchor)

> **Model Tier Tip (1 line, non-blocking):** Right before starting Phase 2, remind the user that designing a demand-driven roadmap and synthesizing JD/benchmark scope works best on a **High / Deep Reasoning tier** (`Claude Sonnet 5.5 (High)` or `Gemini 4 Neon (High)`).

### Step 2A: Adaptive Discovery Interview (2–3 Short Rounds, 5–8 Dynamic Questions)

Read [CLAUDE.md](../../../../../CLAUDE.md) §0 and run an **adaptive 2–3 round discovery interview** (prefer structured choices / `ask_question` where discrete; skip irrelevant branches):

- **Round 1 — Direction & Ground-Truth Mode (2–3 questions):**
  1. **Lĩnh vực & Mục tiêu chính:** Domain/subject + primary goal category:
     - *Nghề nghiệp / Nâng cấp vị trí / Chuyển việc (Career — Demand-Driven JD)*
     - *Ôn thi chứng chỉ / Kỳ thi chuẩn hóa (Certification — Exam Blueprint / Syllabus)*
     - *Học thuật / Nắm trọn giáo trình / Dự án thực chiến (Academic / Textbook / Project Spec)*
  2. **Cách định chuẩn phạm vi (4-Mode Ground-Truth Anchor)** — phrased to match their goal (*JD thực tế* for Career; *Exam Blueprint / Official Syllabus* for Certification; *Mục lục giáo trình / Project Spec* for Academic/Project):
     - **Chế độ 1 — Người dùng cung cấp:** User pastes text, gives URLs, or drops files (PDF/DOCX/MD/TXT) into `sources/`.
     - **Chế độ 2 — Agent tự Deep Search thực tế:** Agent runs multi-query web search across current-year market JDs, official exam blueprints, or industry competency frameworks.
     - **Chế độ 3 — Kết hợp / Hybrid *(Khuyến nghị cho Nghề nghiệp)*:** User supplies 1–N dream JDs/specs AND Agent runs broader web search (10–15 market benchmarks) to avoid overfitting to one company.
     - **Chế độ 4 — Bỏ qua, Agent tự suy luận (Fast Start):** Synthesize roadmap directly from domain knowledge without external JD/benchmark gathering.

- **Round 2 — Branch-Specific Deep-Dive + Baseline & Constraints (2–3 questions):**
  - *If Career / JD branch:* Target role, current level ➔ target level, target market/region & company tier (e.g., VN / APAC / Global Remote / Product vs Big Tech). If Mode 1 or 3, ask the user to paste/link their JD(s) or specify file paths in `sources/`.
  - *If Certification / Exam branch:* Exact exam name, current version/year, target score & deadline. If Mode 1 or 3, collect the official blueprint/syllabus.
  - *If Academic / Textbook / Project branch:* Core textbook/curriculum or concrete project deliverable & deadline. If Mode 1 or 3, collect the TOC/spec.
  - *Common to ALL branches:*
    - **Nền tảng ĐÃ vững (Baseline / Skip list):** Which fundamentals or skills the user already masters well (so we condense or skip them instead of re-teaching basics).
    - **Quỹ thời gian học:** Hours/day or sessions/week (default assumption: 5 study days/week).

- **Round 3 — Study Sources & Pedagogical Style (2 quick confirmation questions):**
  1. **Nguồn tài liệu học tập:** Existing sources (files in `sources/`, Google Drive, YouTube, URLs) to follow, OR Agent-curated canonical/official sources?
  2. **3 tầng độ sâu (`🌱 / 💡 / 👑`) & Dạng ví dụ thực hành:** Pre-propose domain-tailored tier labels (see `CLAUDE.md` §0) and practical example format (Case study, Clinical protocol, Legal precedent, Quantitative calculation, Dialogues, or Code) so the user can approve or adjust in 1 line.

### Step 2B: Execute Ground-Truth Research & Gap Synthesis

Execute strictly according to the selected mode:

- **Mode 1 (User-Provided):** Read/parse all provided JD/syllabus/spec text, URLs, or files in `sources/`. Extract required skill clusters, recurring competencies, and expected depth.
- **Mode 2 (Agent Deep Search) & Mode 3 (Hybrid):**
  - Run multiple focused web searches (`search_web` or equivalent) targeting current-year real JDs / official exam blueprints / industry skill reports matching the user's exact role, level, and market/region.
  - Synthesize a **Demand / Competency Matrix**: skill clusters, frequency/weight (`JD %` or `Exam %`), `Must-have` vs `Nice-to-have`, and gap analysis against the user's Baseline.
  - **External Deep Research Accelerator (Optional / Fallback):** If this environment has no web search OR the user wants an exhaustive 50+ JD sweep using Gemini / ChatGPT / Perplexity Deep Research, generate and output the tailored prompt below, pause, and resume once the user pastes the report or saves it to `docs/` / `sources/`:
    ```markdown
    Hãy đóng vai Chuyên gia Phân tích Thị trường & Thiết kế Lộ trình <Lĩnh vực>.
    Mục tiêu: Phân tích tối thiểu 30–50 <JD thực tế / Đề cương chuẩn> năm <Năm hiện tại> cho vị trí/mục tiêu "<Role / Kỳ thi>" ở thị trường "<VN / APAC / Global>", cấp bậc "<Current -> Target>".
    Yêu cầu đầu ra (Markdown có trích dẫn nguồn):
    1. Bảng Top 15–20 kỹ năng/chuyên đề kèm tần suất xuất hiện (%), phân loại Must-have vs Nice-to-have.
    2. Phân nhóm thành: (a) Nền tảng cốt lõi bắt buộc (Core Trunk — 80% ứng dụng thực tế) và (b) Các nhánh chuyên sâu (Tracks) ở cấp chuyên gia.
    3. Danh sách nguồn tài liệu chính thống / chuẩn ngành tốt nhất cho từng nhóm kỹ năng.
    ```
- **Mode 4 (Pure Synthesis):** Explicitly state key scope assumptions and move directly to Step 2C.

### Step 2C: Mandatory Blueprint Approval Gate (STOP Before Scaffolding)

**Do NOT modify `CLAUDE.md`, `roadmap.md`, `wiki/`, or `lich-hoc-tuan-1.md` yet.** Present a crisp **Scope Blueprint Proposal** containing:
1. **Tóm tắt Chuẩn đầu ra (Ground-Truth Summary):** Sources analyzed (Modes 1–3) + Top Must-have skills with weights (`JD %` / priority), or explicit scope assumptions (Mode 4).
2. **Phân tách 3 nhóm rõ ràng:**
   - `🌱 CORE-TRUNK` (3–6 foundational modules, ceiling at `🌱 Foundation` + `💡 Practical`, estimated hours).
   - `🚀 TRACK-DEEP-DIVE` (Track 1 → Track N for `👑 Expert` & resolving `🎒 Deep-Dive Backlog`).
   - `⏭️ Đã vững / Rút gọn` (skipped or fast-tracked items based on user's Baseline).
3. **Cấu hình Vault & Trọng tâm Tuần 1:** Proposed 3 depth labels (`🌱 / 💡 / 👑`), practical example format, and Week 1 focus.

Ask the user to reply **"Duyệt"** (or request tweaks such as *"Bỏ Track 4, đưa X vào Core Trunk"*). Iterate until approved.

### Step 2D: Full Repo Scaffolding (Execute Immediately Upon Approval)

1. **Conditional Persistence (`docs/scope-benchmark.md`):**
   - If **Mode 1, 2, or 3** was used: write `docs/scope-benchmark.md` recording the scanned JDs/blueprints/specs, `Must-have` vs `Nice-to-have` Skill Frequency Matrix, and Baseline Gap Analysis.
   - If **Mode 4** was used: do NOT create an empty benchmark file; write scope assumptions inline at the top of `docs/roadmap.md`.
2. **Update `CLAUDE.md` §2:** Fill domain, goal, ground-truth mode, 3 depth tiers, practical example format, and switch status to `ĐÃ KHỞI TẠO`.
3. **Personalize `docs/notebooklm-system-prompt.md`:** Update Mentor persona, 3 depth labels (`🌱 / 💡 / 👑`), and example format; **verify `<= 8,350` chars** from `# SYSTEM INSTRUCTION` via `python .agents/plugins/notebooklm-study/scripts/study_helper.py check-prompt`.
4. **Generate `docs/roadmap.md`:** Build the complete roadmap (`🌱 CORE-TRUNK` + `🚀 TRACK-DEEP-DIVE` + `🎒 Deep-Dive Backlog` mapping), referencing `[scope-benchmark.md](./scope-benchmark.md)` at the top when Modes 1–3 were used.
5. **Initialize 4-Tier `wiki/` Structure:**
   - Update `wiki/00-master-hub.md` to match `docs/roadmap.md` (Curriculum Scope only — never put `Tuần X / Ngày Y` inside `wiki/`).
   - Create `wiki/00-core-trunk/00-hub-core-trunk.md` and module subfolders with `00-index-<hoc-phan>.md` (3 empty catalog tables + Full Curriculum Scope).
6. **Generate Week 1 (`docs/lich-hoc-tuan-1.md`, 5 days):** Activate `weekly-study-plan` logic and validate every source (`url`, `file`, `drive`, `text`) + `Lesson Scope <= 1,400` chars with `study_helper.py check-week docs/lich-hoc-tuan-1.md`.
7. **Hand-off:** Present the ready-to-study summary and invite the user to start Day 1 with *"Tạo bài W1D1"* (and note they can switch to Fast tier `Gemini 3.8 Flash (Low / Medium)` for day-init + `/teach`).

---

## Phase 3: Non-Destructive Re-Benchmark (Already-Initialized Vaults Only, On Explicit Request)

Run ONLY when `clean_slate == false` AND the user explicitly requests *"Cập nhật Roadmap theo JD mới"*, *"re-benchmark roadmap"*, or *"cập nhật scope từ JD/đề cương mới"*:

1. Give a 1-line model tip suggesting **High / Deep Reasoning tier** (`Claude Sonnet 5.5 (High)` or `Gemini 4 Neon (High)`).
2. Read existing `CLAUDE.md`, `docs/roadmap.md`, `docs/scope-benchmark.md` (if present), and `wiki/00-master-hub.md` to preserve all completed progress.
3. Ask which Ground-Truth Mode (Mode 1 User JDs / Mode 2 Deep Search / Mode 3 Hybrid + optional external Deep Research prompt) and new market/role criteria to evaluate.
4. Run Step 2B analysis and present a **Non-Destructive Proposed Diff**:
   - Emerging skills to add (and which Track or `CORE-TRUNK` module they belong to).
   - Priority weight (`JD %`) updates or new `🎒 Deep-Dive Backlog` items.
   - Explicit guarantee: **zero existing `wiki/` pages will be deleted**.
5. After user replies **"Duyệt"**:
   - Create/update `docs/scope-benchmark.md` (appending dated benchmark revision).
   - Update `docs/roadmap.md`, `wiki/00-master-hub.md`, and affected `00-hub-*` / `00-index-*` Curriculum Scope checklists (keeping existing `[x]` progress intact).
   - Append a structured log entry to `wiki/log.md`.
