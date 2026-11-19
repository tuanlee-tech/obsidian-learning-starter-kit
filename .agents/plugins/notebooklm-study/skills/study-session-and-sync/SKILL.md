---
name: study-session-and-sync
description: >-
  Use this skill when the user wants to study interactively inside Antigravity
  via NotebookLM MCP (/teach, answering quiz questions, "tiếp", /flash-1,
  /flash-2, /export), finish a lesson with one command ("kết bài", "chốt bài"),
  or sync a completed NotebookLM lesson (from Web, Mobile, or Antigravity)
  straight into `raw/` and run the full `CLAUDE.md` wiki pipeline
  (/pre-ingest -> /ingest -> /lint).
---

# Study Session Bridge & Auto-Sync to Obsidian Wiki

Handles all interactive learning turns via NotebookLM MCP and one-command lesson completion / wiki ingestion.

## Step 0: Resolve Active Notebook

1. Check `.agents/plugins/notebooklm-study/.state/active-notebook.json`:
   ```bash
   python .agents/plugins/notebooklm-study/scripts/study_helper.py state-get
   ```
2. If MCP tools are unavailable or return an auth error, invoke the **`study-init`** health check (`study_helper.py check-env --live`) first.
3. If the user explicitly names another day/notebook or gives a NotebookLM URL (e.g. *"đồng bộ W2D1"*, *"học tiếp W2D2"*):
   - Extract the UUID from the URL or match via `notebook_list()` (by title / `W{X}D{Y}` / `Track ...`) and parse its schedule entry via `study_helper.py parse-day` to know the target `raw_file` and `schedule_file`.
   - Update `.state/active-notebook.json` with `state-set`.
4. **Cross-device resume caveat:** If the user switched mid-lesson from Mobile/Web back to Antigravity to continue `/teach`, note briefly that `notebooklm-mcp-cli` builds follow-up `conversation_history` from its in-memory cache; if NotebookLM loses track of an earlier turn from Mobile, pass a 1-line summary of the last completed outline item alongside the query (or use `chat_get` to inspect the latest server turn first).

---

## Mode A: Interactive Learning Turn (`/outline`, `/teach`, Quiz Answer, `"tiếp"`, `/flash-1`, `/flash-2`, Questions)

When the user sends a study command or replies to NotebookLM's quiz:

1. Map shorthand cleanly to the exact NotebookLM message:
   - `teach` → `"/teach"`
   - `outline` → `"/outline"`
   - `flash-1` / `flash 1` → `"/flash-1"`
   - `flash-2` / `flash 2` → `"/flash-2"`
   - `export` → `"/export"`
   - Any quiz answer, `"tiếp"`, or conceptual question → forward the user's message verbatim.
2. Execute via MCP async query (avoids client timeout):
   - Call `notebook_query_start(notebook_id=<notebook_id>, query=<message>, conversation_id=<conversation_id or omit if empty>)`.
   - Poll `notebook_query_status(query_id=<query_id>)` until `status == "completed"`; read `result.answer` and `result.conversation_id`.
3. If `result.conversation_id` changed or was newly assigned, persist it via `study_helper.py state-set`.
4. **Display NotebookLM's `result.answer` verbatim** in your response — do NOT summarize away explanations, ASCII diagrams, examples/code, or the end-of-turn quiz question.

---

## Mode B: One-Command Finish (`"kết bài"` / `"chốt bài"`)

When the user finishes the final `/teach` item inside Antigravity and types `"kết bài"` (or `"chốt bài"`):

> **Model & Context Tip (non-blocking):** Because Mode C runs full `/pre-ingest` fact-checking, 4-step Auto-Enrich, and 5-point `/ingest` across 5–8 files, if the user is on a lightweight model (such as `Gemini 3.8 Flash (Low / Medium)`) or after a long 10+ turn `/teach` thread, briefly note they can switch to **`Claude Sonnet 5.5 (Medium / High)`**, **`Gemini 4 Argon (Medium / High)`**, or **`Gemini 4 Neon (Medium / High)`** and optionally run `/compact` for best accuracy — proceed directly unless they choose to switch first.

1. Check `chat_get(notebook_id=<notebook_id>)` to see which of `/flash-1`, `/flash-2`, `/export` have already been run in the latest session (avoid duplicate runs).
2. Run any missing steps sequentially on NotebookLM using `notebook_query_start` + `notebook_query_status` (preserving `conversation_id`):
   - If `/flash-1` not yet run → send `"/flash-1"`.
   - If `/flash-2` not yet run → send `"/flash-2"`.
   - If `/export` not yet run → send `"/export"`.
3. Proceed immediately to **Mode C (Extract `/export` → Save `raw/` → Full Wiki Pipeline)** without stopping to ask the user.

---

## Mode C: Sync & Full Wiki Pipeline (`"đồng bộ [ngày]"` or continuation from Mode B)

Works whether the user studied on **NotebookLM Mobile/Web** or **Antigravity**:

1. **Fetch `/export` from NotebookLM:**
   - Call `chat_get(notebook_id=<notebook_id>)` (retrieves latest 20 server turns even from Mobile/Web).
   - Locate the latest turn whose query is `/export` (or contains `/export`) and extract its complete Markdown `answer`.
   - If no `/export` turn exists yet in the notebook's chat history, automatically invoke `notebook_query_start(notebook_id=<notebook_id>, query="/export", conversation_id=<conversation_id>)` + poll `notebook_query_status`, and use `result.answer`.
2. **Clean wrapper artifacts & save to `raw/`:**
   - Strip any outer Markdown/YAML code fence wrapping the YAML frontmatter or entire response so the file starts directly with `---`.
   - Determine target path: use `raw_file` from `active-notebook.json` / `study_helper.py parse-day` (or explicit `File lưu sau khi /export` path).
   - Write the file into `raw/` (check first if a file with that name already exists so nothing is silently overwritten without noticing).
3. **Run the Full Automated `CLAUDE.md` Pipeline (No Pause Unless `BLOCKED`):**
   - Strictly follow [CLAUDE.md](../../../../../CLAUDE.md) §2 (`liên tục tự động`), §6 (`/pre-ingest`), §7 (`/ingest` — **5-Point Full Cascade Sync**), §9 (`wiki/log.md`), §10 (`/lint`), §11 (Normalization Engine), and §12 (Hard Rules):
     1. **`/pre-ingest`**: Normalize YAML/LaTeX/Mermaid/tables directly in `raw/`, verify high-risk technical/domain claims against authoritative sources (or internal consistency for offline textbooks/PDFs), run 4-Step Pedagogical Auto-Enrich, enforce 2-way Flashcards ↔ Body sync, add internal `[[wikilinks]]`. **STOP and report if `BLOCKED`.**
     2. **`/ingest` (5-Point Cascade Sync)**:
        - Point 1: Finalize `raw/` body
        - Point 2: Sync `## 🃏 BỘ FLASHCARDS TỔNG HỢP` in `raw/`
        - Point 3: Create/update `source-*`, `concept-*`, `compare-*`, `backlog-*` pages in `wiki/<track>/<module>/` + cross-link existing pages
        - Point 4: Update `00-index-<module>.md` (all 3 tables + curriculum checkboxes), `00-hub-<track>.md`, and `00-master-hub.md`
        - Point 5: Mark the completed day `## ✅ Ngày X — ... *(Đã hoàn thành & Ingest)*` in `docs/lich-hoc-*.md` and append entry to `wiki/log.md`
     3. **`/lint`**: Audit links, frontmatter, escaped `\|` inside tables, zero ASCII boxes, zero `Tuần/Ngày` labels inside `wiki/`.
4. **Final Report:** Output a concise 5-point sync summary with clickable links to the saved `raw/` file, created/updated `wiki/` pages, updated schedule file, and `wiki/log.md`.
