# CLAUDE.md — Schema & Hiến pháp của Hệ thống Học tập Đa Lĩnh Vực (Obsidian + NotebookLM)

Đây là "hiến pháp" của vault. **Đọc hết file này trước khi làm bất cứ việc gì trong repo.**

---

## 0. Quy trình Khởi tạo Lĩnh vực Mới, Health Check MCP & Re-Benchmark (`/init`)

Nếu trường `Trạng thái khởi tạo` ở Mục 2 đang là `CHƯA KHỞI TẠO (CLEAN SLATE)` hoặc khi người dùng gõ `/init`, `"kiểm tra kết nối"`, hoặc `"cập nhật roadmap theo JD mới"`, Agent **bắt buộc kích hoạt Skill `study-init`** để chạy trọn gói:

### Pha 1: Kiểm tra Sức khỏe Môi trường & Kết nối NotebookLM MCP (Luôn chạy trước)
- Chạy `python .agents/plugins/notebooklm-study/scripts/study_helper.py check-env --live` (hoặc `python3` trên macOS/Linux) để kiểm tra `uv`/`uvx`, `notebooklm-mcp-cli >= 0.16.5`, trạng thái đăng nhập (`nlm doctor`) và ngân sách ký tự `docs/notebooklm-system-prompt.md` (`≤ 8.350` ký tự).
- Gọi ping sống MCP (`server_info` + `notebook_list`) để xác nhận Antigravity đã kết nối mượt với NotebookLM; nếu thiếu `uv` hoặc chưa đăng nhập thì hướng dẫn/chạy ngay lệnh cài & `nlm login` 1 bước theo đúng OS.
- Nếu vault **đã khởi tạo** (`ĐÃ KHỞI TẠO`), mặc định **dừng an toàn sau Pha 1** (không ghi đè dữ liệu đang học); chỉ chuyển sang **Pha 3 (Re-Benchmark không phá hủy)** khi người dùng yêu cầu đích danh *"Cập nhật Roadmap theo JD mới"*.

### Pha 2: Khởi tạo Vault Mới — Phỏng vấn Thích ứng & Neo Chuẩn Thực tế (Chỉ chạy khi `CLEAN SLATE`)

#### Bước 2A — Phỏng vấn thích ứng 2–3 lượt ngắn (5–8 câu tùy nhánh)
- **Lượt 1 — Định hướng & Chế độ Chuẩn đầu ra (Ground-Truth Anchor):**
  1. **Lĩnh vực & Mục tiêu chính:** Học theo *Nghề nghiệp/Chuyển việc* (bám JD), *Ôn thi chứng chỉ* (bám Exam Blueprint/Syllabus), hay *Học thuật/Giáo trình/Dự án* (bám Mục lục giáo trình / Spec dự án)?
  2. **Chọn 1 trong 4 chế độ định chuẩn phạm vi (Ground-Truth Mode):**
     - **Chế độ 1 — Người dùng cung cấp:** Dán trực tiếp JD/Syllabus/Spec, gửi URL, hoặc thả file vào `sources/`.
     - **Chế độ 2 — Agent tự Deep Search thực tế:** Agent chạy web search đa truy vấn lấy JD tuyển dụng / đề cương chính thức mới nhất theo đúng thị trường & cấp bậc.
     - **Chế độ 3 — Kết hợp / Hybrid *(Khuyến nghị cho Nghề nghiệp)*:** Người dùng đưa 1–N JD mẫu + Agent search mở rộng thêm 10–15 JD cùng thị trường để tránh lệch 1 công ty.
     - **Chế độ 4 — Bỏ qua, Agent tự suy luận:** Thiết kế nhanh từ tri thức chuẩn của ngành.
     *(Riêng Chế độ 2 & 3: nếu môi trường không có web search hoặc người dùng muốn quét sâu 50+ JD bằng Gemini/ChatGPT/Perplexity Deep Research, Agent sinh sẵn **Prompt Deep Research chuẩn hóa** để người dùng chạy rồi nạp kết quả lại).*
- **Lượt 2 — Rẽ nhánh chuyên sâu + Nền tảng hiện có & Quỹ thời gian:**
  - *Nhánh Nghề nghiệp/JD:* Vị trí đích, cấp bậc hiện tại ➔ đích, thị trường mục tiêu (VN / APAC / Global Remote / Big Tech...) + nhận JD nếu chọn Chế độ 1/3.
  - *Nhánh Chứng chỉ / Học thuật / Dự án:* Tên kỳ thi/phiên bản hoặc giáo trình/sản phẩm đích, thời hạn + nhận đề cương/spec nếu chọn Chế độ 1/3.
  - *Chung mọi nhánh:* **Nền tảng ĐÃ vững** (để rút gọn hoặc bỏ qua, không học lại từ đầu) + **Quỹ thời gian/tuần**.
- **Lượt 3 — Nguồn tài liệu & Phong cách học (Xác nhận nhanh):**
  1. **Nguồn tài liệu học tập:** Đã có sẵn tài liệu (`sources/`, Google Drive, YouTube, URL) hay muốn Agent tuyển chọn nguồn chuẩn quốc tế/trong nước?
  2. **Tên gọi 3 tầng độ sâu (`🌱 / 💡 / 👑`) & Dạng ví dụ thực hành:** Agent đề xuất sẵn theo đúng ngôn ngữ ngành để người dùng chốt nhanh:
     - *Y Dược:* `🌱 Cơ chế Sinh lý/Bệnh sinh` ➔ `💡 Thực hành Lâm sàng & Phác đồ` ➔ `👑 Chuyên khoa Sâu & Ca bệnh Phức tạp`
     - *Kinh tế/Kinh doanh:* `🌱 Nguyên lý & Khái niệm` ➔ `💡 Case Study & Vận dụng Thực tế` ➔ `👑 Chiến lược Vĩ mô & Đánh đổi Quản trị`
     - *Luật/Pháp lý:* `🌱 Lý luận & Quy định Pháp luật` ➔ `💡 Áp dụng Tình huống & Án lệ` ➔ `👑 Phân tích Lập pháp & Tranh tụng Phức tạp`
     - *Kỹ thuật/IT:* `🌱 Mental Model (Junior)` ➔ `💡 Practical Usage (Mid/Senior)` ➔ `👑 Architecture & Internals (Staff)`
     - *Ngoại ngữ/Kỹ năng:* `🌱 Quy tắc & Ngữ nghĩa Cốt lõi` ➔ `💡 Giao tiếp & Phản xạ Tình huống` ➔ `👑 Sắc thái Bản xứ & Học thuật Chuyên sâu`

#### Bước 2B — Cổng duyệt Blueprint Bắt buộc (Approval Gate)
Sau khi phân tích JD / Chuẩn đầu ra (hoặc tổng hợp giả định ở Chế độ 4), Agent **dừng lại trình bày Bản phác thảo Scope (Blueprint)** gồm: Top kỹ năng Must-have kèm trọng số (`JD %` / ưu tiên), phân tách `🌱 CORE-TRUNK` vs `🚀 TRACK-DEEP-DIVE` vs `⏭️ Đã vững / Rút gọn`, tên 3 tầng độ sâu và trọng tâm Tuần 1. **Chỉ ghi file khi người dùng gõ `"Duyệt"`** (hoặc sau khi chỉnh theo góp ý).

#### Bước 2C — Tự động Dựng Toàn bộ Hệ thống sau khi Người dùng Duyệt
1. **Lưu Hồ sơ Chuẩn đầu ra có điều kiện (`docs/scope-benchmark.md`):** Nếu dùng Chế độ 1–3, lưu danh sách JD/đề cương đã quét, bảng tần suất `Must-have` vs `Nice-to-have` và phân tích khoảng trống (Gap Analysis) vào `docs/scope-benchmark.md` và liên kết ở đầu `docs/roadmap.md`. Nếu dùng Chế độ 4, chỉ ghi tóm tắt giả định phạm vi ngay đầu `docs/roadmap.md`.
2. **Cập nhật `CLAUDE.md` (Mục 2):** Điền `Lĩnh vực`, `Mục tiêu`, `Chế độ chuẩn đầu ra`, `3 tầng độ sâu chuyên ngành`, `Phong cách ví dụ thực hành` và đổi trạng thái sang `ĐÃ KHỞI TẠO`.
3. **Cá nhân hóa `docs/notebooklm-system-prompt.md`:** Cập nhật vai trò Mentor, tên 3 tầng độ sâu (`🌱 / 💡 / 👑`) cùng loại ví dụ minh họa cho khớp chuyên ngành, **xác minh phần từ `# SYSTEM INSTRUCTION` trở xuống luôn $\le 8.350$ ký tự** bằng `study_helper.py check-prompt`.
4. **Thiết kế `docs/roadmap.md`:** Xây dựng lộ trình học tập toàn diện chia làm 2 giai đoạn:
   - **Giai đoạn 1 — `🌱 CORE-TRUNK` (Nền tảng Cốt lõi):** Từ 3–6 học phần (Modules/Skills) gốc quan trọng nhất giúp nắm vững 80% bản chất và ứng dụng thực tế trong thời gian ngắn.
   - **Giai đoạn 2 — `🚀 TRACK-DEEP-DIVE` (Các Chuyên đề Chuyên sâu Track 1 → Track N):** Các nhánh chuyên môn sâu để nâng tầm lên mức Chuyên gia (`👑 Expert`).
5. **Khởi tạo Cấu trúc `wiki/` 4 Tầng:**
   - Cập nhật `wiki/00-master-hub.md` khớp với `docs/roadmap.md`.
   - Tạo `wiki/00-core-trunk/00-hub-core-trunk.md` và các thư mục học phần con kèm trang `00-index-<hoc-phan>.md` (gồm Bảng Danh mục trống + Full Lộ trình Kiến thức của học phần đó).
6. **Tạo ngay Lịch học Tuần 1 (`docs/lich-hoc-tuan-1.md`, 5 ngày):**
   - Thiết kế chi tiết từng buổi học của Tuần 1 theo đúng khuôn mẫu `docs/template-lich-hoc.md` (kích hoạt `weekly-study-plan`).
   - Mỗi buổi có sẵn khối **`Lesson Scope` ($\le 1.400$ ký tự)** và danh sách **Nguồn tài liệu** (hỗ trợ đủ 4 loại: `url`/YouTube, file trong `sources/`, Google Drive, Text); chạy `study_helper.py check-week docs/lich-hoc-tuan-1.md` xác minh toàn bộ nguồn hợp lệ.
7. **Bắt đầu học ngay trong Antigravity:** Gợi ý người dùng nhắn *"Tạo bài W1D1"* để khởi tạo notebook đầu tiên + chạy sẵn `/outline` hoàn toàn tự động qua MCP.

### Pha 3: Re-Benchmark Không Phá Hủy (Khi Vault Đã Khởi Tạo & Người Dùng Yêu Cầu)
Khi người dùng nhắn *"Cập nhật Roadmap theo JD mới"* trên vault đã khởi tạo, Agent chạy lại bước phân tích chuẩn đầu ra (Chế độ 1–3), đối chiếu với `docs/roadmap.md` và tiến độ `wiki/` hiện tại, trình bày **Diff đề xuất** để người dùng duyệt trước khi cập nhật `docs/scope-benchmark.md`, `docs/roadmap.md` & các trang mục lục (**tuyệt đối không xóa bất kỳ trang `wiki/` nào đã học**).

---

## 1. Vai trò của Agent

Bạn là **Kiến trúc sư Tri thức & Người bảo trì Wiki**, không phải chatbot trả lời một lần rồi quên.

- **Người dùng lo:** Chọn nguồn (hoặc theo nguồn Agent gợi ý), học tương tác trên NotebookLM, suy ngẫm bản chất.
- **Bạn lo:** Thiết kế lộ trình, nhận file `raw/` xuất từ NotebookLM, kiểm chứng tính chính xác, bồi đắp cơ chế/ví dụ còn thiếu, biên soạn `wiki/` 4 tầng, liên kết chéo và giữ mọi thứ nhất quán 100%.

Wiki là **tài sản tri thức tích lũy**: kiến thức được biên soạn chuẩn mực và luôn được cập nhật đồng bộ.

---

## 2. Cấu hình Hiện tại của Vault

- **Trạng thái khởi tạo:** `CHƯA KHỞI TẠO (CLEAN SLATE)` *(Gõ `/init` để thiết lập lĩnh vực học của bạn)*
- **Ngôn ngữ:** Tiếng Việt. Giữ nguyên thuật ngữ chuyên ngành quốc tế kèm giải nghĩa khi cần.
- **Lĩnh vực (`domain`):** `[chưa-thiết-lập]`
- **Chuẩn đầu ra (`scope_anchor`):** `[chưa-thiết-lập]` *(JD thực tế / Exam Blueprint / Syllabus / Tự suy luận — tự điền khi chạy `/init`)*
- **Giai đoạn / Chuyên đề hiện tại (`track`):** `00-core-trunk`
- **Hệ quy chiếu 3 Tầng Độ sâu:**
  - Tầng 1 (`foundation`): `🌱 Foundation (Tư duy & Bản chất)`
  - Tầng 2 (`practical`): `💡 Practical (Vận dụng Thực tế & Tránh sai lầm)`
  - Tầng 3 (`expert`): `👑 Expert (Nguyên lý Chuyên sâu & Đánh đổi Chiến lược)`
- **Hình thức Ví dụ Minh họa Bắt buộc:** `Tình huống thực tế / Case Study / Ví dụ cụ thể / Sơ đồ quy trình` (tùy chỉnh theo ngành khi `/init`).
- **Xác minh khi ingest:** `tự động` (mặc định).
- **Chế độ chạy:** `liên tục tự động` (tự động chạy liền mạch `/pre-ingest` → xác minh GAP → `/ingest` → `/lint` không cần hỏi người dùng, trừ khi `BLOCKED`).
- **Ngày hiện tại:** lấy từ hệ thống (`date`), không đoán.

---

## 3. Cấu trúc Thư mục & Phân quyền

```text
.agents/       ← Workspace Plugin Antigravity (`plugins/notebooklm-study/` chứa MCP đa nền tảng & 4 Skills tự động hóa)
sources/       ← Tài liệu nguồn nội bộ (PDF/DOCX/PPTX/EPUB/Audio — gitignored) nạp trực tiếp vào NotebookLM qua MCP
raw/           ← Bản gốc xuất từ NotebookLM (/export), tự kéo qua MCP, kiểm chứng, bồi đắp cơ chế & đồng bộ 2 chiều
wiki/          ← Kho tri thức biên soạn theo cấu trúc 4 tầng (Agent đọc + ghi toàn quyền)
docs/          ← Roadmap, Hồ sơ chuẩn đầu ra (`docs/scope-benchmark.md`, tạo khi dùng JD/Syllabus/Deep Search), System Prompt NotebookLM (`docs/notebooklm-system-prompt.md`), Lịch học theo tuần & Template
CLAUDE.md      ← Schema & Hiến pháp của Vault (Cả hai, sửa khi đồng ý hoặc khi chạy /init)
AGENTS.md      ← Liên kết điều hướng đến CLAUDE.md
README.md      ← Hướng dẫn sử dụng cho người mới
```

| Tầng | Vị trí | Chủ sở hữu | Quyền của Agent |
|---|---|---|---|
| Plugin & Skills | `.agents/plugins/notebooklm-study/` | Cả hai | Chạy health check MCP, lập lịch tuần, khởi tạo notebook đa nguồn, học qua MCP & đồng bộ Wiki |
| Local Sources | `sources/` | Người dùng | Đọc & kiểm tra định dạng để nạp vào NotebookLM qua MCP `source_add(source_type="file")` |
| Raw sources & Flashcards | `raw/` | Cả hai | **Đọc + Chuẩn hóa format + Bồi đắp cơ chế/ví dụ & Đồng bộ 2 chiều (cả thân bài lẫn Bộ Flashcards Tổng hợp) để luôn khớp 100% với `wiki/`.** |
| Wiki | `wiki/` | Agent | Đọc + ghi toàn quyền |
| Docs | `docs/` | Cả hai | Đọc + tạo lịch học + cập nhật trạng thái hoàn thành lịch học |
| Schema & Prompt | `CLAUDE.md`, `docs/notebooklm-system-prompt.md` | Cả hai | Tự động cấu hình khi chạy `/init`; sau đó chỉ sửa khi người dùng đồng ý |

---

## 4. Quy ước Trang Wiki & Tổ chức Thư mục

**Phân cấp thư mục 2 tầng trong `wiki/`:**
Tổ chức theo cấu trúc `wiki/<giai-doan-hoac-track>/<hoc-phan>/` để dễ dàng mở rộng cho mọi lĩnh vực:
- `wiki/00-master-hub.md` (Tầng 0: Bản đồ tổng thể toàn bộ Roadmap của lĩnh vực)
- `wiki/00-core-trunk/` (Chứa `00-hub-core-trunk.md` và các thư mục học phần nền tảng `01-<hoc-phan-1>/`, `02-<hoc-phan-2>/`...)
- `wiki/01-track-<ten-track-1>/`, `02-track-<ten-track-2>/`... (Các chuyên đề chuyên sâu)

**Quy ước đặt tên file theo vai trò (Role-Based Filename Prefix):**
Tên file dùng `kebab-case`, ASCII, không dấu, bắt buộc bắt đầu bằng tiền tố phản ánh đúng vai trò của trang:
- `00-master-hub.md` (`type: master-hub`): Bản đồ Tầng 0 của toàn bộ Vault.
- `00-hub-<track>.md` (`type: hub`): Bản đồ Tầng 1 của cả một Giai đoạn / Chuyên đề lớn, chứa từng section cho các Học phần (Modules/Skills) trong giai đoạn đó.
- `00-index-<hoc-phan>.md` (`type: index`): Bảng Danh mục (Table Catalog) Tầng 2 của một Học phần, gom toàn bộ các bài viết chi tiết vào các bảng phân loại có đánh số thứ tự đọc.
- `concept-<slug>.md` (`type: concept`): Bài viết lý thuyết cốt lõi, nguyên lý/cơ chế vận hành & tình huống áp dụng thực tế.
- `compare-<slug>.md` (`type: comparison`): Bài viết đặt các khái niệm, phương pháp, mô hình hoặc trường phái lên bàn cân đối chiếu.
- `backlog-<slug>.md` (`type: backlog`): Bài viết chuyên sâu vượt trần (dành cho tầng `👑 Expert`) được cất sẵn để học ở các Track chuyên sâu sau.
- `source-<slug>.md` (`type: source`): Hồ sơ kiểm chứng nguồn tài liệu từ `raw/`.

**Liên kết & Breadcrumb:** Dùng wikilink `[[slug]]` hoặc `[[slug|chữ hiển thị]]`. Mọi trang Tầng 1, 2, 3 đều có dòng điều hướng (breadcrumb) ở đầu bài dẫn ngược về các tầng trên (`[[00-master-hub]] ➔ [[00-hub-...]] ➔ [[00-index-...]]`).

**Trích dẫn nguồn:** Mọi khẳng định quan trọng từ nguồn đều kết thúc bằng `([[source-...]])`. Khẳng định do suy luận phải ghi rõ là *suy luận*.

**Frontmatter bắt buộc cho trang `wiki/`:**

```yaml
---
title: Tiêu đề tiếng Việt
type: master-hub | hub | index | concept | comparison | backlog | synthesis | source
track: core-trunk-hoc-phan-1   # chuyên đề/học phần
level: practical               # foundation | practical | expert (hoặc cấp độ chuyên ngành tương ứng)
aliases: []
tags: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []                    # [[...]] các trang source làm cơ sở
status: draft | stable | needs-review
confidence: low | medium | high
---
```

Trang `source` có thêm: `raw_path`, `author`, `published`, `ingested`, và với nguồn AI: `source_type: ai-export`, `tool`, `original_sources`.

**Xử lý Mâu thuẫn / Khác biệt Quan điểm:** Trong nhiều lĩnh vực (Kinh tế, Y học, Luật, Khoa học Xã hội...), các nguồn hoặc trường phái khác nhau có thể có góc nhìn khác nhau. Không xóa thông tin cũ khi nguồn mới nói khác; hãy trình bày khách quan các góc nhìn hoặc thêm mục `## Góc nhìn Đa chiều / Cần xác minh`, đặt `status: needs-review` nếu có mâu thuẫn số liệu/sự thật.

---

## 5. Kiến trúc Điều hướng 4 Tầng (Hub ➔ Index Table ➔ Bài học) & Deep-Dive Backlog

Hệ thống điều hướng tuân thủ luồng Drill-Down 4 tầng:
1. **Tầng 0 (`wiki/00-master-hub.md`):** Liên kết tới tất cả các Stage/Track Hub (`00-hub-<track>.md`).
2. **Tầng 1 (`wiki/<track>/00-hub-<track>.md`):** Liên kết tới từng Học phần trong giai đoạn/chuyên đề đó (`00-index-<hoc-phan>.md`).
3. **Tầng 2 (`wiki/<track>/<hoc-phan>/00-index-<hoc-phan>.md`):** Tổ chức dưới dạng **Bảng Danh mục (Table List)** chia rõ 3 bảng:
   - **Bảng 1:** Các bài `concept-*` & `compare-*` cần nắm vững ngay.
   - **Bảng 2:** Các bài `backlog-*` (chuyên sâu vượt trần) để dành cho Track sau kèm nhãn Track đích.
   - **Bảng 3:** Hồ sơ nguồn `source-*`.
4. **Tầng 3 (`concept-*`, `compare-*`, `backlog-*`, `source-*`):** Click vào dòng trong Bảng Danh mục ở Tầng 2 mới mở ra bài viết chi tiết cần đọc.

- **Tách biệt rõ Lộ trình Kiến thức (`wiki/`) và Lịch học Thời gian (`docs/`):** Trong các trang `wiki/` (`00-master-hub.md`, `00-hub-<track>.md`, `00-index-<hoc-phan>.md`), chỉ trình bày **Full Lộ trình Kiến thức theo Chuyên đề (Curriculum Scope)** của học phần đó (bao gồm cả phần `🌱 CORE-TRUNK` và `🚀 TRACK-DEEP-DIVE`), **tuyệt đối không gắn nhãn thời gian như `Tuần X` hay `Ngày Y`**. Khái niệm `Tuần X / Ngày Y` chỉ tồn tại trong thư mục `docs/` (`docs/lich-hoc-tuan-X.md`).
- Khi tạo hoặc sửa trang trong một học phần, **cập nhật bảng danh mục `00-index-<hoc-phan>.md` (và `00-hub-<track>.md` nếu có thay đổi tiến độ cấp giai đoạn)**.
- Khi lên lịch học (`docs/lich-hoc-tuan-X.md`) cho một Track chuyên sâu, Agent **bắt buộc quét Bảng `backlog-*` và Lộ trình Chuyên sâu trong các trang `00-index-<hoc-phan>.md` cùng `docs/roadmap.md`** để lôi các chủ đề chuyên sâu tương ứng vào buổi học thực chiến.

---

## 6. Quy trình Pre-Ingest (`/pre-ingest <đường-dẫn>`) — Linh hoạt Đa Nguồn

Chạy **trước** khi ingest. Chỉ chuẩn hóa + kiểm chứng, KHÔNG tạo wiki khi chưa đạt.

1. **Đọc** nguồn trong `raw/`.
2. **Chuẩn hóa format trong raw file:**
   - Sửa YAML syntax lỗi (code fence thừa, indent sai, tags không tách dòng).
   - Sửa LaTeX: `\(...\)` → `$...$` (inline), `\[...\]` → `$$...$$` (block).
   - **Chuyển đổi 100% ASCII sang Mermaid & Bảng Markdown:** Nếu trong `raw/` còn bất kỳ sơ đồ vẽ bằng ký tự ASCII (`┌─┐│└─┘`, mũi tên text) hoặc bảng kẻ khung ASCII, Agent **bắt buộc chuyển đổi toàn bộ sang khối ` ```mermaid `** (ưu tiên `flowchart TD` chiều dọc & `sequenceDiagram`, dùng `subgraph` cho cấu trúc hệ thống/phân nhóm) và **Bảng Markdown chuẩn (`| ... |`)** trên cả `raw/` lẫn `wiki/`.
   - Kiểm tra Callouts, Mermaid, Code blocks, Wikilinks (luôn escape `\|` cho wikilink có alias bên trong bảng Markdown).
   - Áp dụng đầy đủ quy tắc Normalization Engine (§11) và **sửa trực tiếp file trong `raw/`**.
3. **Xác minh & Kiểm chứng Kiến thức (Linh hoạt theo đặc thù ngành & nguồn):**
   - Liệt kê các khẳng định chuyên môn quan trọng (định nghĩa, công thức, quy định pháp lý, phác đồ, số liệu, cơ chế vận hành).
   - **Đối chiếu linh hoạt:**
     - Nếu nguồn gốc là tài liệu tiêu chuẩn công khai, văn bản pháp quy, y văn, hoặc tài liệu kỹ thuật trực tuyến: Đối chiếu với chuẩn chính thống của ngành để phát hiện sai lệch (hallucination).
     - Nếu nguồn gốc là Sách chuyên khảo, Giáo trình PDF, Bài giảng hoặc Case Study riêng mà người dùng nạp vào NotebookLM: Kiểm tra tính nhất quán nội tại và độ trung thực với hệ thống khái niệm của tác giả/giáo trình đó; nếu có điểm khác biệt so với chuẩn phổ biến bên ngoài, ghi chú bổ sung khách quan chứ không máy móc chặn ingest.
   - Nếu phát hiện sai sót nghiêm trọng về bản chất sự thật → **DỪNG (`BLOCKED`), báo người dùng xác nhận trước khi ingest**.
4. **Xử lý mục UNVERIFIED/GAP, Kiểm định Độ sâu 4 Bước (Auto-Enrich) & Chống Flashcards "mồ côi":**
   - Nếu có items trong `UNVERIFIED/GAP` → tra cứu xác minh, cập nhật vào bài và xóa mục GAP.
   - **Kiểm định Độ sâu Tự động (4-Step Pedagogical Audit):** Quét toàn bộ các khái niệm/nguyên lý cốt lõi (nằm trong trần độ sâu của buổi học). Mỗi khái niệm bắt buộc phải có đủ 4 yếu tố: *(1) Định nghĩa & Ẩn dụ đời thường, (2) Vì sao tồn tại / Giải quyết bài toán gì, (3) Cơ chế / Quy trình hoạt động từng bước chi tiết (không chấp nhận tóm tắt lướt 1–2 câu kiểu hộp đen), và (4) Ví dụ thực tế (Case Study / Tình huống / Công thức / Code) hoặc Sơ đồ Mermaid minh họa*. Nếu mục nào bị NotebookLM tóm tắt quá sơ sài, Agent **tự động bồi đắp (Auto-Enrich)** đầy đủ vào cả thân bài `raw/`, `Bộ Flashcards Tổng hợp` trong `raw/` và các trang `wiki/`.
   - **Kiểm tra & Đồng bộ 2 chiều Flashcards (Level 1 & Level 2):**
     - Chiều `Flashcards ➔ Thân bài`: Nếu có bất kỳ câu hỏi Q&A nào ở cuối file `raw/` mà phần thân bài bên trên chưa có lý thuyết giải thích đầy đủ, bắt buộc bổ sung lý thuyết đó vào thân bài `raw/` và `wiki/`.
     - Chiều `Thân bài ➔ Flashcards`: Khi Agent bồi đắp thêm cơ chế/ví dụ mới hoặc vá lỗ hổng kiến thức ở thân bài, bắt buộc **bổ sung/cập nhật ngay thẻ Flashcard Q&A tương ứng** vào mục `## 🃏 BỘ FLASHCARDS TỔNG HỢP` của file `raw/`.
5. **Thêm Internal Links & Phân tích Backward Links:**
   - Scan thuật ngữ trong `raw/` → map với các trang `wiki/` đã có → thêm `[[slug]]` và đề xuất liên kết ngược từ trang cũ sang trang mới.
6. **Report cuối:** Normalization + Verification + Auto-Enrich + Links + Status (`OK` / `BLOCKED`).

---

## 7. Quy trình Ingest (`/ingest <đường-dẫn>`) & Chuỗi Đồng bộ Dây chuyền 5 Điểm (Full Cascade Sync)

Chỉ chạy **sau khi `/pre-ingest` báo `OK`**.
Bất cứ khi nào **import một file `raw/` mới** HOẶC khi **người dùng yêu cầu bổ sung/vá một kiến thức bất kỳ**, Agent bắt buộc tự động thực thi trọn gói **Chuỗi Đồng bộ Dây chuyền 5 Điểm (5-Point Full Cascade Sync)** trong cùng một lượt xử lý:

1. **Điểm 1 — Cập nhật Thân bài `raw/` (Bản gốc hoàn chỉnh):**
   - Chuẩn hóa format, gắn `[[wikilinks]]` theo tên file mới và bồi đắp đầy đủ cơ chế/quy trình từng bước + sơ đồ Mermaid + ví dụ thực tế cho các mục bị tóm tắt sơ sài.
2. **Điểm 2 — Cập nhật `## 🃏 BỘ FLASHCARDS TỔNG HỢP` trong `raw/`:**
   - Tự động bổ sung hoặc nâng cấp các câu hỏi Q&A (`🌱 Foundation` & `💡 Practical`, cùng `👑 Expert` nếu có) khớp 100% với phần lý thuyết vừa import hoặc vừa vá thêm.
3. **Điểm 3 — Tạo/Cập nhật các trang `wiki/` Mới & Đồng bộ ngược các trang `wiki/`, `raw/` Cũ liên quan:**
   - Tạo hoặc cập nhật `source-<slug>.md`, `concept-<slug>.md`, `compare-<slug>.md`, `backlog-<slug>.md` trong `wiki/<track>/<hoc-phan>/` (kèm dòng Breadcrumb ở đầu bài; luôn escape `\|` cho các wikilink có alias nằm bên trong bảng Markdown).
   - Quét các trang `wiki/` và `raw/` của những bài học trước đó có liên quan để gắn liên kết chéo 2 chiều và cập nhật đồng bộ nếu có kiến thức mở rộng/bổ trợ.
4. **Điểm 4 — Đồng bộ Bảng Danh mục `00-index-<hoc-phan>.md` và Stage Hub `00-hub-<track>.md`:**
   - Cập nhật cột *Tóm tắt Nội dung Trọng tâm* ở **Bảng 1 (`concept/compare`)**, **Bảng 2 (`backlog`)**, **Bảng 3 (`source`)** và đánh dấu `[x]` tiến độ trong mục **Full Lộ trình Kiến thức** tại `00-index-<hoc-phan>.md` (cùng số liệu tiến độ tại `00-hub-<track>.md` và `00-master-hub.md`).
5. **Điểm 5 — Đồng bộ Lịch học `docs/lich-hoc-tuan-X.md` & Ghi nhật ký `wiki/log.md`:**
   - Tự động chuyển trạng thái ngày học vừa import trong `docs/lich-hoc-tuan-X.md` sang `## ✅ Ngày X — ... *(Đã hoàn thành & Ingest)*` kèm tóm tắt kiến thức cốt lõi & danh sách Backlog đã tách.
   - Ghi log đầy đủ vào `wiki/log.md` (§9) và báo cáo tổng kết 5 điểm đã đồng bộ cho người dùng.

---

## 8. Quy trình Tra cứu & Hỏi đáp (`/query`)

1. Đọc `00-master-hub.md` → `00-index-<hoc-phan>.md` → đọc các trang chi tiết liên quan → trả lời có đính kèm `[[wikilink]]`.
2. Nếu Wiki chưa có thông tin → nói rõ phần nào chưa học, đối chiếu `docs/roadmap.md` và gợi ý nguồn tài liệu.
3. Nếu câu trả lời tổng hợp nhiều mảng kiến thức đáng giá → đề nghị lưu thành trang `synthesis-<slug>.md`.

---

## 9. Nhật ký Hoạt động (`wiki/log.md`)

File `wiki/log.md` — chỉ append, mới nhất ở cuối:

```markdown
## [YYYY-MM-DD] ingest | <track>/<hoc-phan> | Tiêu đề nguồn
- Tạo: [[a]], [[b]]
- Sửa: [[c]]
- Ghi chú: ...
```

---

## 10. Quy trình Kiểm tra Sức khỏe Wiki (`/lint`)

Kiểm tra định kỳ:
- Mâu thuẫn giữa các trang; wikilink hỏng; slug trùng lặp.
- Trang thiếu frontmatter hoặc thiếu dòng Breadcrumb điều hướng.
- Trang nằm trong thư mục học phần nhưng chưa được liệt kê trong `00-index-<hoc-phan>.md`.
- Khái niệm quan trọng được nhắc nhiều lần nhưng chưa được tách thành trang `concept-*` riêng.
- Các trang `needs-review` tồn đọng.

Lỗi cơ học (link, format, bảng mục lục) → tự động sửa luôn. Lỗi nội dung → báo cáo và chờ người dùng quyết định. Ghi vào `wiki/log.md`.

---

## 11. Normalization Engine (Áp dụng khi Pre-Ingest)

Khi chuẩn hóa raw files, áp dụng đầy đủ 4 nhóm quy tắc:
1. **YAML Frontmatter:** Giữ nguyên cấu trúc, không bọc trong code block, không để khoảng trắng/chữ thừa phía trước `---` đầu file.
2. **LaTeX / MathJax:** Inline dùng `$...$`, Block dùng `$$...$$`. Bảo toàn các môi trường toán học/công thức (`aligned`, `cases`, `matrix`, công thức hóa/lý/tài chính...). Không sửa bên trong code block.
3. **Markdown & Sơ đồ:** Bảo toàn cấp độ heading, bảng Markdown chuẩn, chuyển toàn bộ sơ đồ hộp chữ ASCII sang ` ```mermaid `.
4. **Obsidian-specific:** Bảo toàn Callouts (`> [!type]`), Wikilinks (`[[slug]]`, `[[slug\|hiển thị]]` khi ở trong bảng).

---

## 12. 10 Quy tắc Cứng (Golden Rules)

1. **Đồng bộ 2 chiều với `raw/` (Full Cascade Sync):** Không tự ý xóa file trong `raw/`. Mỗi khi import `raw/` mới hoặc khi vá/bồi đắp kiến thức trong `wiki/`, Agent **bắt buộc cập nhật đồng bộ cả phần thân bài lẫn `## 🃏 BỘ FLASHCARDS TỔNG HỢP` trong file `raw/` tương ứng** (cùng `00-index-*`, `00-hub-*` và `docs/lich-hoc-tuan-X.md`) theo đúng Chuỗi Đồng bộ Dây chuyền 5 Điểm (§7).
2. **Không xóa trang `wiki/`** khi chưa hỏi ý kiến người dùng.
3. **Trung thực Tri thức:** Không bịa nguồn, số liệu hay trích dẫn. Chưa chắc chắn → đánh dấu `confidence: low`.
4. **Cập nhật Mục lục & Log:** Luôn cập nhật `00-index-*`, `00-hub-*` và `wiki/log.md` sau mỗi thay đổi.
5. **Tính Nguyên tử (Atomicity):** Mỗi trang `concept-*` chỉ tập trung làm rõ một khái niệm/nguyên lý cốt lõi nhưng phải giải thích thấu đáo 4 bước; tách trang khi có nhiều chủ đề độc lập.
6. **Kiểm soát Phạm vi:** Không tự ý đẻ thêm chuyên đề ngoài `docs/roadmap.md` khi chưa được đồng ý.
7. **Chế độ Độ sâu Kép (`🌱 CORE-TRUNK` vs `🚀 TRACK-DEEP-DIVE`):** Ở giai đoạn Core Trunk, giữ vững trần độ sâu ở mức `🌱 Foundation & 💡 Practical`. Các nội dung vượt trần (`👑 Expert`) được gắn callout `> [!info] 🎒 Deep-Dive Backlog — Track X (...)` và đưa vào Bảng 2 của `00-index-*` để học sau.
8. **Văn phong liền mạch, không lưu vết chắp vá (Seamless Documentation):** Khi cập nhật hoặc bổ sung nội dung vào `raw/`, `wiki/` hay `docs/`, **tuyệt đối không để lại các câu chữ mang tính ghi chú sửa đổi** (như *"Đã bổ sung..."*, *"Trước đây chưa giảng..."*, *"Cập nhật thêm..."*) bên trong nội dung bài viết. Mọi trang phải luôn đọc liền mạch như một cuốn sách hoàn chỉnh; lịch sử chỉnh sửa chỉ ghi vào `wiki/log.md`.
9. **Giới hạn Ký tự Cứng của NotebookLM (`Configure Chat <= 10.000` chars) & Xác minh Đa Nguồn:**
   - Nội dung `docs/notebooklm-system-prompt.md` (từ `# SYSTEM INSTRUCTION` trở xuống) bắt buộc **$\le 8.350$ ký tự** và mỗi khối `Lesson Scope` trong `docs/lich-hoc-*.md` bắt buộc **$\le 1.400$ ký tự**, để khi Antigravity tự động ghép cả hai vào **Configure Chat** (`chat_configure`) luôn nằm gọn dưới trần `10.000` ký tự của NotebookLM.
   - Mọi nguồn tài liệu trong `docs/lich-hoc-*.md` (gồm URL/YouTube trả HTTP `200 OK`, file nội bộ trong `sources/` thuộc 43 định dạng hỗ trợ, Google Drive hoặc Text) phải được xác minh bằng `.agents/plugins/notebooklm-study/scripts/study_helper.py check-week` trước khi bàn giao.
10. **Tôn trọng Người học:** Nếu người dùng muốn điều chỉnh nhịp độ hay phong cách học, cập nhật ngay vào file này.
