---
name: study-day-init
description: >-
  Use this skill when the user asks to create or initialize a NotebookLM study
  notebook for a specific day from a weekly schedule (e.g. "tạo bài W2D4",
  "tạo notebook Tuần 1 Ngày 1", "tạo bài Track 1 W1D1"). Automates multi-source
  validation (URL, YouTube, local PDF/DOCX/audio, Drive, text), notebook
  creation, source ingestion, Configure Chat prompt merging, and runs the
  initial /outline automatically.
---

# Daily Study Notebook Initializer (MCP End-to-End, Multi-Source)

Create a fully configured NotebookLM notebook for a specific study day **without touching NotebookLM's UI** and immediately generate its `/outline`.

## Step 0: Resolve Target Day & Parse Schedule

1. Identify the schedule file (`docs/lich-hoc-tuan-X.md` or `docs/lich-hoc-track-T-tuan-W.md`) and day number (`1..5`) requested by the user. If ambiguous, ask for the exact week/day rather than guessing.
2. Run the cross-platform helper (`python` or `python3`):

```bash
python .agents/plugins/notebooklm-study/scripts/study_helper.py parse-day docs/<schedule>.md <day> --include-merged
```

3. Verify from the JSON output:
   - `counts.base_prompt_ok == true` (`<= 8,350` chars)
   - `counts.scope_ok == true` (`<= 1,400` chars)
   - `counts.merged_ok == true` (`<= 10,000` chars)
   - `sources` is non-empty.
   If `merged_ok` is false, stop and report the exact character excess before making any MCP call.

## Step 1: Validate All Sources (URL / File / Drive / Text)

```bash
python .agents/plugins/notebooklm-study/scripts/study_helper.py check-sources --file docs/<schedule>.md --day <day>
```

Verify `"all_ok": true`:
- Every `url` returns HTTP `200 OK`.
- Every `file` exists locally with one of NotebookLM's 43 supported extensions.
- Every `drive` and `text` entry is well-formed.
If any source fails (broken URL or missing local file in `sources/`), stop and alert the user before creating the notebook.

## Step 2: Ensure NotebookLM MCP & Auth Readiness

If NotebookLM MCP tools (`notebook_create`, `source_add`, `chat_configure`, `notebook_query_start`) are missing or fail with an authentication error (`UNAUTHENTICATED` / expired cookies), run `python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live` and activate the **`notebooklm-connect`** skill (alongside `study-init` health check) to resolve `uv`, Android `proot`/remote shim, or auth cookies cleanly across Windows, macOS, Linux, and Android.

## Step 3: Create Notebook, Add All Sources & Configure Chat via MCP

Execute these MCP calls in strict order:

1. **Create notebook:**
   - Call `notebook_create(title=<notebook_title>)`.
   - Record `notebook_id`.
2. **Add all sources non-blockingly (`wait=False` ALWAYS):**
   - **URL / YouTube sources** (all `type == "url"` entries batched in 1 call):
     `source_add(notebook_id=<notebook_id>, source_type="url", urls=[...], wait=False)`
   - **Local files** (each `type == "file"` entry):
     `source_add(notebook_id=<notebook_id>, source_type="file", file_path=<abs_file_path>, wait=False)`
   - **Google Drive documents** (each `type == "drive"` entry):
     `source_add(notebook_id=<notebook_id>, source_type="drive", document_id=<document_id>, doc_type=<doc_type>, wait=False)`
   - **Pasted text sources** (each `type == "text"` entry):
     `source_add(notebook_id=<notebook_id>, source_type="text", title=<title>, text=<text>, wait=False)`
   - **NEVER** pass `wait=True` on batches (sequential 120s waits risk MCP timeouts).
3. **Wait until every source is indexed:**
   - Poll `notebook_get(notebook_id=<notebook_id>)` (short pauses between calls if needed) until all expected sources appear with resolved titles and none are in processing/error state (`status == 2` or `status` omitted once title is populated). If any source errors out, report which source failed.
4. **Configure Chat (`chat_configure`):**
   - Call:
     ```
     chat_configure(
       notebook_id=<notebook_id>,
       goal="custom",
       custom_prompt=<merged_prompt>,
       response_length="longer"
     )
     ```

## Step 4: Run `/outline` Immediately

1. Start the query asynchronously to avoid client timeouts:
   - Call `notebook_query_start(notebook_id=<notebook_id>, query="/outline")`.
   - Poll `notebook_query_status(query_id=<query_id>)` until `status == "completed"`.
2. Record `result.conversation_id` and `result.answer` (the generated `/outline`).

## Step 5: Persist Active Study State & Present Result

1. Save active session metadata (gitignored under `.state/`):
   ```bash
   python .agents/plugins/notebooklm-study/scripts/study_helper.py state-set \
     --notebook-id "<notebook_id>" \
     --title "<notebook_title>" \
     --conversation-id "<conversation_id>" \
     --schedule "docs/<schedule>.md" \
     --day <day> \
     --raw-file "<raw_file>"
   ```
2. Respond to the user with:
   - Clickable link to the notebook: `https://notebook.google.com/notebook/<notebook_id>` (ready to continue on Web or Mobile too).
   - Brief confirmation: source breakdown ready + merged `Configure Chat` char count (`X / 10,000`).
   - **Verbatim `/outline` returned by NotebookLM (`result.answer`).**
   - Short hint: *"Gõ `/teach` ngay tại đây để học trên Antigravity (tự đồng bộ lên NotebookLM — có thể hạ xuống `Gemini 3.8 Flash (Low / Medium)` hoặc `Claude Sonnet 5.5 (Low)` cho mượt và tiết kiệm quota), hoặc mở link trên điện thoại học rồi quay lại nhắn `đồng bộ`."*
