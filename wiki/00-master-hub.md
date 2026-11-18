---
title: Bản đồ Tổng thể Kho Tri thức (Master Hub)
type: master-hub
status: draft
confidence: high
---

# 🏛️ Bản đồ Tổng thể Kho Tri thức (Master Hub — Tầng 0)

> **Trạng thái:** ⏳ *Vault đang ở trạng thái Clean Slate (Chưa khởi tạo).*
> Hãy gõ **`/init`** trong khung chat với AI Agent để thiết lập lĩnh vực học tập của bạn. Agent sẽ tự động tạo toàn bộ hệ thống Hub Tầng 1 (`00-hub-*`) và Bảng Danh mục Tầng 2 (`00-index-*`) tại đây!

---

## 🧭 Hệ thống Điều hướng 4 Tầng (Sẽ được kích hoạt sau `/init`)

```mermaid
flowchart TD
    T0["🏛️ Tầng 0: 00-master-hub.md<br/>(Bản đồ Tổng thể Toàn Lĩnh vực)"] --> T1A["🌱 Tầng 1: 00-hub-core-trunk.md<br/>(Giai đoạn Nền tảng Cốt lõi)"]
    T0 --> T1B["🚀 Tầng 1: 00-hub-track-X.md<br/>(Các Chuyên đề Chuyên sâu)"]
    T1A --> T2["📋 Tầng 2: 00-index-hoc-phan.md<br/>(Bảng Danh mục & Lộ trình Học phần)"]
    T2 --> T3A["📖 Tầng 3: concept-*.md & compare-*.md<br/>(Bài học Lý thuyết, Ví dụ & Đối chiếu)"]
    T2 --> T3B["🎒 Tầng 3: backlog-*.md<br/>(Chủ đề Chuyên sâu để dành cho Track sau)"]
```
