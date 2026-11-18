# Template Lịch học Tuần (Đa Lĩnh Vực)

> **Cách dùng:** Agent tạo file `lich-hoc-tuan-X.md` từ [`roadmap.md`](./roadmap.md), tuân thủ chế độ độ sâu (`🌱 CORE-TRUNK` cho giai đoạn nền tảng hoặc `🚀 TRACK-DEEP-DIVE` khi đi vào chuyên đề chuyên sâu).
> **Nguyên tắc 1-Copy Block & Giới hạn Ký tự NotebookLM:**
> - Toàn bộ **`Mode`**, **`✅ CHECKLIST HÔM NAY`** và **`🎒 DEEP-DIVE BACKLOG (Kèm Track đích)`** phải nằm trọn bên trong một block `Customize notebook` duy nhất.
> - **Giới hạn cứng:** Mỗi block `Customize notebook` **BẮT BUỘC $\le 1.400$ ký tự** (vì ô Custom của NotebookLM giới hạn cứng **1.500 ký tự**), còn `GEMINI.md` (Configure Chat) **BẮT BUỘC $\le 9.000$ ký tự** (giới hạn cứng **10.000 ký tự**).

---

## Nguyên tắc thiết kế buổi học theo Mode

| Tiêu chí | Chế độ `🌱 CORE-TRUNK` (Giai đoạn Nền tảng Cốt lõi) | Chế độ `🚀 TRACK-DEEP-DIVE` (Chuyên đề Chuyên sâu) |
|---|---|---|
| **Trần độ sâu** | `🌱 Foundation` + `💡 Practical` (Nắm vững bản chất & vận dụng thực tế) | Mở khóa đủ 3 tầng `🌱 Foundation → 💡 Practical → 👑 Expert` |
| **Mục tiêu** | Hiểu đúng nguyên lý cốt lõi để áp dụng ngay vào thực tế, tránh các lỗi phổ biến | Nắm vững cơ chế chuyên sâu, phân tích đa chiều, đánh đổi chiến lược & trả nợ Backlog |
| **Nguồn tài liệu** | **2–4 nguồn chuẩn mực nhất** (Sách giáo trình chuẩn, Văn bản chính thống, Tài liệu gốc hoặc Bài giảng uy tín — KHÔNG nạp tràn lan gây nhiễu) | Giáo trình chuẩn + Bài báo nghiên cứu / Chuyên khảo + Case Study phức tạp + Deep Search |
| **Kiến thức nâng cao** | Khai báo đầy đủ trong mục `🎒 DEEP-DIVE BACKLOG` ngay bên trong block `Customize notebook` để NotebookLM xuất ra ở cuối `/outline` và `/export` | Lôi các mục từ `🎒 Deep-Dive Backlog` của Core Trunk ra học gắn với bài toán thực tế |

---

## Format chuẩn cho mỗi ngày/buổi học

```markdown
## Ngày X — [Chủ đề Buổi học]

### Customize notebook (Copy trọn 1 block này → ⚙️ → Customize notebook hoặc paste kèm `/outline`)
\```
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

### Nguồn tài liệu (Nạp vào NotebookLM)
- **Tài liệu 1:** [Tên Sách / Giáo trình PDF / Chương X] hoặc [Tên Tài liệu Chính thống](URL)
- **Tài liệu 2:** [Tên Báo cáo / Bài viết chuẩn](URL)
*(Ở chế độ 🌱 CORE-TRUNK: Chỉ nạp 2–4 nguồn cốt lõi trên để giữ độ tập trung cao nhất)*

### Quy trình học & Tiến độ
- [ ] **Bước 1:** Tạo notebook mới trên NotebookLM → nạp các tài liệu ở mục *Nguồn tài liệu* làm Sources.
- [ ] **Bước 2:** Copy trọn vẹn block **Customize notebook** bên trên → paste vào **⚙️ → Customize notebook** (hoặc paste trực tiếp kèm lệnh `/outline` ở tin nhắn đầu tiên).
- [ ] **Bước 3:** Chạy tuần tự `/outline` → `/teach` → `/flash-1` → `/flash-2` → `/export`.
- [ ] **Bước 4:** Lưu kết quả `/export` vào `raw/` và nhờ Agent ingest vào `wiki/<track>/<hoc-phan>/`.
```
