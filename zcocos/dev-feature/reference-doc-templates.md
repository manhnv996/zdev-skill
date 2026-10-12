# Reference — Doc Templates

Templates dùng trong Phase A của `dev-feature`.

Main `SKILL.md` giữ flow/gate và checkpoint. File này chỉ chứa nội dung template dài để agent đọc đúng lúc cần tạo file.

---

## Design Doc Template

Dùng ở Step A1.

**Tạo file:** `docs/modules/{featureName}/design/{featureName}-design.md`

```markdown
---
status: draft | approved
date: YYYY-MM-DD
author: [tên]
---

# {FeatureName} — Feature Design

## Overview

- **Loại:** Event (giới hạn thời gian) | Feature thường
- **Mục đích:** [Làm gì, tại sao cần]
- **Entry point:** [Icon lobby / auto popup khi load / menu X]
- **Điều kiện hiển thị:** [Luôn / Chỉ khi event active / Level X+ / ...]

## Player Fantasy

[1-3 câu: cảm giác player muốn có khi dùng tính năng này — viết theo góc nhìn player]

## Flow Màn Hình

```
[Entry] → {FeatureName}LobbyIcon
  ↓ tap
{FeatureName}MainGui
  ├─ [Action A] → Nhận kết quả → Update UI
  ├─ [Action B] → {FeatureName}PopupGui → Confirm → Gửi gói tin
  └─ [Đóng]
```

## Detailed Rules

### [Tên rule / section 1]
- [Rule chi tiết]
- [Điều kiện, exception]

### [Tên rule / section 2]
- ...

## Formulas

[Các công thức tính toán nếu có, e.g. validate gold, tính reward, điểm...]

## Edge Cases

- [Trường hợp đặc biệt 1]: → xử lý thế nào
- [Trường hợp đặc biệt 2]: → xử lý thế nào
- Event hết hạn khi đang mở GUI: → [xử lý]
- Lỗi mạng / server error: → [xử lý]

## Dependencies

- Dùng data/module nào? (e.g. UserInfo.gold, OfferSystem, SkinSystem)
- Module nào cần gọi tính năng này?

## Tuning Knobs

[Những thứ có thể thay đổi qua config/server mà không cần sửa code]

## Acceptance Criteria

- [ ] [Tiêu chí 1 — hành vi cụ thể, kiểm tra được]
- [ ] [Tiêu chí 2]
- [ ] Event kết thúc: icon và GUI ẩn đúng cách
- [ ] Server trả lỗi: hiển thị message đúng
```

---

## Dev Status Template

Dùng ở Step A3.

**Tạo file:** `docs/modules/{featureName}/dev-status.md`
*(Nằm ở root module, không phải trong spec/ — vì đây là tracking, không phải spec)*

> Chỉ liệt kê file đã có trong spec. Không copy row ví dụ như `LobbyIcon`, `SendPacket`, `ReceivePacket` nếu spec không có file tương ứng.

```markdown
---
updated: YYYY-MM-DD
phase: A — Docs
---

# {FeatureName} — Dev Status

> Cập nhật sau mỗi session làm việc.
> Spec: `docs/modules/{featureName}/spec/{featureName}-spec.md`

---

## Tóm tắt

| File | Trạng thái | Session | Ghi chú |
|------|-----------|---------|---------|
| `{FeatureName}Module.js` | ⬜ Todo | — | |
| `{FeatureName}SendPacket.js` | ⬜ Todo | — | |
| `{FeatureName}ReceivePacket.js` | ⬜ Todo | — | |
| `{FeatureName}Util.js` | ⬜ Todo | — | |
| `{FeatureName}MainGui.js` | ⬜ Todo | — | |
| `{FeatureName}LobbyIcon.js` | ⬜ Todo | — | |
| *(thêm các file đã confirm trong spec — không thêm file chưa có trong spec)* | | | |

**Ký hiệu:** ⬜ Todo · 🔄 In Progress · ✅ Done · ❌ Blocked

---

## Chi tiết từng file

### `{FeatureName}Module.js` — ⬜ Todo
*(Điền khi bắt đầu file này: những gì đã làm, những gì còn lại, vấn đề gặp phải)*

---

## Known Issues / Gaps

| ID | Mô tả | Priority | Trạng thái |
|----|-------|----------|-----------|
| — | — | — | — |

*(Điền khi phát hiện vấn đề — P1 Critical / P2 Major / P3 Minor)*

---

## Localization Keys (cần dịch)

> Luôn giữ section này để tracking localization. Nếu chưa có key mới, để bảng trống dưới header. Nếu có key mới, điền bằng key thật đã derive từ spec/UI. Không để row placeholder như `{prefix}_title`.

Key mới của feature dùng prefix `{prefix}_` và cần thêm vào file localization cho từng ngôn ngữ. Key có sẵn được reuse giữ nguyên tên gốc và dùng trạng thái `N/A`.

Ký hiệu: ✅ text hiện tại đã được ghi và verify trong Excel · ⬜ key/text draft đang chờ add hoặc update Excel · `N/A` key có sẵn được reuse, không thuộc batch này

| Key | Gợi ý text (VI) | Ghi chú | Excel |
|-----|----------------|---------|-------|
```

---

## Implementation Plan Template

Dùng ở Step A4.

**Tạo file:** `docs/modules/{featureName}/plans/{YYYY-MM-DD}-{featureName}-plan.md`
*(date = ngày hôm nay)*

> Plan chỉ sinh task từ spec đã approve. Task ví dụ như Lobby Icon / Network Layer / Optional chỉ giữ nếu spec có phần tương ứng; nếu không có thì bỏ hoặc đổi tên theo flow thật.

```markdown
# {FeatureName} — Implementation Plan

> **Design:** `docs/modules/{featureName}/design/{featureName}-design.md`
> **Spec:** `docs/modules/{featureName}/spec/{featureName}-spec.md`
> **Status:** `docs/modules/{featureName}/dev-status.md`

**Goal:** [1 câu mô tả mục tiêu của plan này]
**Approach:** Bottom-up — data → network → UI

---

## File Map

| File | Hành động |
|------|-----------|
| `{FeatureName}Module.js` | Tạo mới |
| `{FeatureName}SendPacket.js` | Tạo mới |
| `{FeatureName}ReceivePacket.js` | Tạo mới |
| `{FeatureName}Util.js` | Tạo mới |
| `{FeatureName}MainGui.js` | Tạo mới |
| [các file khác] | Tạo mới / Sửa |

---

## Tasks

### Task 1: Scaffold & Constants
- [ ] Tạo folder: `{srcPath}/cmd/`, `logic/`, `ui/`
- [ ] Tạo tất cả file từ spec — stub rỗng
- [ ] Search `project.json` trước; chỉ thêm path JS còn thiếu vào cuối `jsList`, không thêm trùng. Thứ tự `cmd/` → `logic/` → `ui/` → `{Prefix}Module.js`
- [ ] Thêm `PoolFunction.{FEATURE}_*` constants
- [ ] Thêm `EXCHANGE.CMD.{FEATURE}_*` constants

### Task 2: Logic Layer
- [ ] `{FeatureName}Util.js` — state, reset(), helpers
- [ ] `{FeatureName}Model.js` — (nếu có)
- [ ] `{FeatureName}JSONConfig.js` — dùng `/dev-config {jsonPath} {jsPath}`, đính kèm đường dẫn spec để dev-config đọc getter table đã confirm, không hỏi lại từ đầu *(nếu có trong spec)*

### Task 3: Network Layer
- [ ] `{FeatureName}SendPacket.js` — tất cả lệnh gửi
- [ ] `{FeatureName}ReceivePacket.js` — tất cả parsers
- [ ] `{FeatureName}Module.js` — `init()` (PoolFunction.regFunc), `reset()`, `send*()`, `onGameMessage()`, `cmdReceive*()`
- [ ] Đăng ký vào `src/gamemgr/ModuleMgr.js`: `var {prefix}Module = new {FeatureName}Module()`

### Task 4: UI — Lobby Icon
- [ ] `{FeatureName}LobbyIcon.js` — show/hide theo event state
- [ ] Wiring: sau LOAD_INFO → show/hide icon đúng

### Task 5: UI — Main GUI
- [ ] `{FeatureName}MainGui.js` — layout, bind data từ Util
- [ ] Wiring: icon tap → showMainGui

### Task 6: UI — Actions & Other GUIs
- [ ] [Action 1]: button → sendPacket → response → update UI
- [ ] [Action 2]: ...
- [ ] Error handling: EXPIRE_TIME, NOT_ENOUGH_ITEM, server error
- [ ] `{FeatureName}PopupGui.js` (nếu cần)

### Task 7: Optional
- [ ] `{FeatureName}Animate.js` — (nếu cần)
- [ ] `{FeatureName}Tutorial.js` — (nếu cần)

### Task 8: QA
- [ ] Happy path trên simulator/device
- [ ] Edge cases từ design doc
- [ ] Fix bugs qua `/diagnose`

---

## Ước lượng

| Task | Effort |
|------|--------|
| 1. Scaffold | ~0.5h |
| 2. Logic | ~1-2h |
| 3. Network | ~1-2h |
| 4. Lobby Icon | ~0.5-1h |
| 5. Main GUI | ~2-4h |
| 6. Actions | ~2-6h |
| 7. Optional | ~1-3h |
| 8. QA | ~1-2h |
| **Total** | **~8-20h** |
```
