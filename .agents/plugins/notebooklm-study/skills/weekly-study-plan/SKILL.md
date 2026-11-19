---
name: weekly-study-plan
description: >-
  Use this skill when the user asks to create or update a weekly study schedule
  (typically 5 days per week) in `docs/lich-hoc-*.md` based on `docs/roadmap.md`,
  `docs/template-lich-hoc.md`, and pending `backlog-*` topics in `wiki/`.
---

# Weekly Study Plan Generator (5 Days / Week — Universal & Multi-Source)

Generate a complete, validated **5-day weekly study schedule** (`docs/lich-hoc-tuan-X.md` for Core Trunk or `docs/lich-hoc-track-T-tuan-W.md` for Track 1–N) that integrates seamlessly with `study-day-init` and NotebookLM MCP across any learning domain.

## Inputs to Read First

1. Read [CLAUDE.md](../../../../../CLAUDE.md) (especially §2, §5, and §12.7–12.9).
2. Read [docs/roadmap.md](../../../../../docs/roadmap.md) and [docs/template-lich-hoc.md](../../../../../docs/template-lich-hoc.md).
3. Inspect the previous week's schedule file (if any) to keep naming, continuity, and Track links consistent.
4. **Mandatory for Track Deep-Dive (`🚀 TRACK-DEEP-DIVE`):** Scan `Bảng 2 (backlog-*)` across relevant `wiki/**/00-index-*.md` pages and pull matching Core Trunk backlog items directly into the week's lessons so they are explicitly paid down.

## Authoring Rules

1. **Always design 5 days** (`Ngày 1` through `Ngày 5`) unless the user explicitly asks for another number.
2. **Enforce Dual-Mode Depth Control:**
   - `🌱 CORE-TRUNK`: Lock ceiling to Tier 1 (`🌱`) + Tier 2 (`💡`). Use **2–4 authoritative core sources** per day. Push advanced Tier 3 (`👑`) topics into `🎒 DEEP-DIVE BACKLOG` with explicit target Track.
   - `🚀 TRACK-DEEP-DIVE`: Unlock all 3 tiers (`🌱 → 💡 → 👑`), include explicit `Tên NotebookLM gợi ý` and `File lưu sau khi /export: raw/<slug>.md`.
3. **Support All 4 Official NotebookLM Source Types:**
   Declare sources cleanly under `### Nguồn tài liệu (nạp vào NotebookLM)` (or `### Tài liệu official (nạp vào NotebookLM)`):
   - **Web / YouTube URL:** `- [Tên tài liệu](https://...)`
   - **Local File (43 supported formats: `.pdf`, `.docx`, `.pptx`, `.epub`, `.md`, `.txt`, `.csv`, images, audio/video):** `- [Chương 1 PDF](sources/chuong-1.pdf)` or `` `sources/bai-giang.pptx` ``
   - **Google Drive (Docs / Slides / Sheets / PDF):** paste the standard `https://docs.google.com/...` or `https://drive.google.com/file/d/...` URL (or `drive:<doc|slides|sheets|pdf>:<ID>`)
   - **Pasted Text:** add `#### 📝 Nguồn Text: <Tiêu đề>` followed by a fenced code block
4. **Use the `Lesson Scope` block:**
   - Put the day's `Buổi học`, `Track`/`Học phần`, `Mode`, `Depth ceiling`, `Nền tảng`/`Prerequisite`, `✅ CHECKLIST HÔM NAY`, and `🎒 DEEP-DIVE BACKLOG` inside a fenced ````text` block under `### Lesson Scope (tự động ghép vào Configure Chat — ≤ 1.400 ký tự)`.
   - Every day's `Lesson Scope` block **MUST be `<= 1,400` characters** so that `docs/notebooklm-system-prompt.md` (`<= 8,350` chars) + block stays strictly under NotebookLM's `10,000`-char `Configure Chat` limit.
5. **Seamless Vietnamese documentation (`CLAUDE.md` §12.8):** No meta-edit notes inside the schedule file.

## Mandatory Automated Verification

Before handing the schedule back to the user, run the cross-platform validator (`python` on Windows or `python3` on macOS/Linux):

```bash
python .agents/plugins/notebooklm-study/scripts/study_helper.py check-week docs/<new-schedule-file>.md
```

Verify that `"all_ok": true`:
- `day_count == 5` (or requested count).
- Every day's `scope_chars <= 1400` and `merged_chars <= 10000`.
- Every URL returns HTTP **`200 OK`**, every local file exists with a valid official extension, and every Drive/Text source is valid. Fix any failed source and re-run `check-week` until `"all_ok": true`.

## Output to User

Present a concise summary table of the 5 days (topic, source count & types, char count, validation status) with a clickable link to the created file, and remind the user they can spin up any day with a short prompt (e.g., *"Tạo bài W1D1"*).
