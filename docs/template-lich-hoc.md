# Template Lịch học Tuần (Đa Lĩnh Vực & Đa Nguồn)

> **Cách dùng:** Skill `weekly-study-plan` tạo file `lich-hoc-tuan-X.md` (5 ngày/tuần) từ [`roadmap.md`](./roadmap.md), tuân thủ chế độ độ sâu (`🌱 CORE-TRUNK` cho giai đoạn nền tảng hoặc `🚀 TRACK-DEEP-DIVE` khi đi vào chuyên đề chuyên sâu).
> **Nguyên tắc Lesson Scope & Giới hạn Ký tự NotebookLM:**
> - Toàn bộ **`Mode`**, **`✅ CHECKLIST HÔM NAY`** và **`🎒 DEEP-DIVE BACKLOG (Kèm Track đích)`** phải nằm trọn bên trong một block `Lesson Scope` duy nhất.
> - **Giới hạn cứng:** Mỗi block `Lesson Scope` **BẮT BUỘC $\le 1.400$ ký tự** và [`docs/notebooklm-system-prompt.md`](./notebooklm-system-prompt.md) **BẮT BUỘC $\le 8.350$ ký tự**, để khi Antigravity tự động ghép cả hai vào **Configure Chat** (`chat_configure`) luôn nằm gọn dưới trần `10.000` ký tự của NotebookLM.

---

## Nguyên tắc thiết kế buổi học theo Mode

| Tiêu chí | Chế độ `🌱 CORE-TRUNK` (Giai đoạn Nền tảng Cốt lõi) | Chế độ `🚀 TRACK-DEEP-DIVE` (Chuyên đề Chuyên sâu) |
|---|---|---|
| **Trần độ sâu** | `🌱 Foundation` + `💡 Practical` (Nắm vững bản chất & vận dụng thực tế) | Mở khóa đủ 3 tầng `🌱 Foundation → 💡 Practical → 👑 Expert` |
| **Mục tiêu** | Hiểu đúng nguyên lý cốt lõi để áp dụng ngay vào thực tế, tránh các lỗi phổ biến | Nắm vững cơ chế chuyên sâu, phân tích đa chiều, đánh đổi chiến lược & trả nợ Backlog |
| **Nguồn tài liệu** | **2–4 nguồn chuẩn mực nhất** (URL chính thống, YouTube, file PDF/DOCX/PPTX/Audio trong `sources/`, Google Drive hoặc Text — KHÔNG nạp tràn lan gây nhiễu) | Giáo trình chuẩn + Bài báo nghiên cứu / Chuyên khảo + Case Study phức tạp + Deep Search |
| **Kiến thức nâng cao** | Khai báo đầy đủ trong mục `🎒 DEEP-DIVE BACKLOG` ngay bên trong block `Lesson Scope` để NotebookLM xuất ra ở cuối `/outline` và `/export` | Lôi các mục từ `🎒 Deep-Dive Backlog` của Core Trunk ra học gắn với bài toán thực tế |

---

## Format chuẩn cho mỗi ngày/buổi học

```markdown
## Ngày X — [Chủ đề Buổi học]

### Lesson Scope (Tự động ghép vào Configure Chat qua Antigravity — `≤ 1.400 ký tự`)
\```text
Buổi học: Tuần X — Ngày Y — [Chủ đề]
Học phần: [Tên học phần, ví dụ: Core Trunk #1 — ...]
Mode: [🌱 CORE-TRUNK | 🚀 TRACK-DEEP-DIVE]
Depth ceiling: [🌱 Foundation & 💡 Practical (Tập trung bản chất & vận dụng, hoãn phần chuyên sâu cực đoan) | 👑 Full Mastery (Foundation → Practical → Expert)]
Nền tảng học viên: [Ghi chú trình độ hiện tại & loại ví dụ thực tế mong muốn: Case study / Tình huống / Bài tập / Code...]

✅ CHECKLIST HÔM NAY (CẦN GIẢNG TRONG /OUTLINE & /TEACH):
1. [Khái niệm cốt lõi 1 — 🌱 Foundation]: [Mô tả cụ thể bản chất/nguyên lý cần hiểu]
2. [Khái niệm cốt lõi 2 — 💡 Practical]: [Mô tả tình huống vận dụng thực tế / quy trình thực hiện]
3. [Khái niệm cốt lõi 3 — 💡 Pitfalls]: [Mô tả sai lầm thường gặp và cách phòng tránh]

🎒 DEEP-DIVE BACKLOG (KHÔNG GIẢNG HÔM NAY — BẮT BUỘC XUẤT RA Ở CUỐI /OUTLINE & /EXPORT):
- [Chủ đề chuyên sâu 1]: [Mô tả 1 câu vì sao hoãn lại] → Track đích: [Track X — Tên chuyên đề]
- [Chủ đề chuyên sâu 2]: [Mô tả 1 câu vì sao hoãn lại] → Track đích: [Track Y — Tên chuyên đề]
\```

### Nguồn tài liệu (nạp vào NotebookLM — hỗ trợ đủ 4 loại nguồn)
- [Tên tài liệu Web hoặc YouTube](https://example.com/official-guide)
- [Giáo trình Chương 1 (PDF nội bộ trong sources/)](sources/giao-trinh-chuong-1.pdf)
- [Slide bài giảng trên Google Drive](https://docs.google.com/presentation/d/<GOOGLE_DOC_ID>/edit)
*(Hoặc dùng `#### 📝 Nguồn Text: <Tiêu đề>` kèm code block để nạp ghi chú văn bản trực tiếp. Ở chế độ 🌱 CORE-TRUNK: chỉ chọn 2–4 nguồn cốt lõi nhất.)*

### Quy trình học & Tiến độ
- [ ] **Bước 1:** Gọi Antigravity khởi tạo ngày học (*"Tạo bài W{X}D{Y}"*) → tự kiểm tra nguồn, tạo notebook, nạp đủ nguồn (`url`/`file`/`drive`/`text`), ghép `docs/notebooklm-system-prompt.md` + `Lesson Scope` vào `Configure Chat` và chạy sẵn `/outline`.
- [ ] **Bước 2:** Học `/teach` → trả lời → `tiếp` ngay trên Antigravity (qua MCP) hoặc mở link NotebookLM Web/Mobile.
- [ ] **Bước 3:** Nhắn `"kết bài"` (nếu học trên Antigravity) hoặc `"đồng bộ W{X}D{Y}"` (nếu học trên Mobile/Web) để tự chạy `/flash-1` → `/flash-2` → `/export` → lưu `raw/` → `/pre-ingest` → `/ingest` → `/lint`.
```
