# Reference — Doc Templates

Templates cho Phase A của `dev-delete-feature-content`. Docs nằm ở `docs/modules/<task>/` (gitignored trong repo này) — vì vậy manifest JSON phải tự chứa đủ dữ liệu cho tool, docs chỉ phục vụ người duyệt và rollback.

```
docs/modules/<task>/
├── design/<task>-design.md          # A1 — danh sách feature đóng, mục tiêu, scope, backup
├── spec/<task>-spec.md              # A2 master — 1 lần cho mọi bundle
├── spec/bundles/<bundle>.md         # A2 — 1 file / bundle, viết sau khi trace
├── manifests/<bundle>.json          # gen_manifest.py; + <bundle>.quarantine.patch
├── trace/report_<bundle>.md         # trace_bundle.py output (không sửa tay)
├── dev-status.md                    # A3
└── plans/<YYYY-MM-DD>-<task>-plan.md# A4
```

---

## Design Doc (A1)

```markdown
---
status: draft | approved
date: YYYY-MM-DD
---
# <Task> — Design

## Mục tiêu
Giảm dung lượng APK bằng cách xóa resource của feature đã đóng vĩnh viễn. **Không xóa source JS** (giữ để mở lại).

## Danh sách feature đóng
| Module (dòng ModuleMgr, var/class) | Module dir | Bundle content resolve được (`res/content/<x>`) | Lý do đóng | Raw size |
|---|---|---|---|---:|
*(Điền từ `trace_bundle.py --module <Tên>` — không cần tag `//D`; folder dùng chung như `system`/`lobby` không phải bundle)*

## Scope
- Có: `res/content/<bundle>` + `res#tcf_astc/content/<bundle>`
- Không: source JS, packet/CMD constant, config JSON, `project.json`, animation (`res/animation` — Phase 2), tập tag khác (`//remove`)

## Backup & rollback
Backup root ngoài repo: `<path>\<build>\` mirror client. Rollback 1 feature = Restore + `git apply -R quarantine.patch`.

## Acceptance Criteria
- [ ] Mỗi bundle 1 commit độc lập, message ghi số file/bytes/backup
- [ ] Không crash: launch → lobby → vào bàn → rời bàn → logout/login → reload config
- [ ] Feature active dùng chung folder vẫn render đủ
- [ ] APK Δ đo cùng flavor/ABI so với baseline <build>
```

---

## Master Spec (A2, viết 1 lần)

Sections bắt buộc: `Scope Confirmed` (bảng quyết định) · `Folder Structure` (files tạo mới, đều gitignored/ngoài repo) · `Files Cần Sửa — Toàn Task` (ModuleMgr, ResourceImage, cdn.json, Layer 3 trong module, caller — điều kiện áp dụng) · `Bundle Spec Index` (bundle, batch, mode, files, bytes, unresolved, link) · `Quarantine Contract` (tóm tắt + link reference) · `Removal Manifest — Schema` · `Safety Tool` (signature, action, refuse, exit) · `Backup Layout & Rollback` · `Verification Strategy` (Agent / User) · `Batch Order` (dễ → khó theo loại risk mới: không consumer ngoài → preload → CDN → nhiều điểm tích hợp → partial-prune → module cha active → path động) · `Cách chạy — duyệt docs 2 lần` · `Phase 2 Candidate` · `Open Items`.

Batch đầu chọn 1–2 bundle full-folder không consumer ngoài — mục đích **validate tool** trên ca an toàn trước khi trace hàng loạt.

---

## Bundle Spec (A2, 1 file / bundle)

```markdown
---
status: traced | approved | implemented — commit <hash>, chờ smoke | smoke-pass
date: YYYY-MM-DD
bundle: <bundle>
batch: <n>
removal-mode: full-folder | partial-prune
spec-ref: docs/modules/<task>/spec/<task>-spec.md
---

# <bundle> — Consumer Matrix & Quarantine Plan

## Resource Inventory — <N> file, <B> B · removed <n> (<b> B) / retained <m> (<b> B)
*(chép từ bảng "Tổng kết theo file" cuối `trace/report_<b>.md` — cột Quyết định = XÓA/GIỮ sau khi review; ghi rõ frame/ảnh active dùng và ai dùng cho từng dòng GIỮ)*
| Dependency group | File | Bytes | Consumer | Class |
|---|---|---:|---|---|
| UI JSON ×k | `A`, `B` `.json` | | `src/game/<dir>/ui/*` (retired) | Retired |
| **Atlas `XContent`** | `.plist` + `.png` + astc | | 5 UI JSON (retired) **+ `<active file:line>` frame `<name>` (active)** | **Retained** |
**`unresolved` = 0.**

## Gate Results
| Gate | Kết quả |
|---|---|
| G3 Atlas frame share | … |
| G4 `res.<key>` | … (preload dòng nào, giữ/comment) |
| G5 cdn.json | … |
| G6 Dynamic path | … |
| G8 4c / G9 4b | … |

## Vì sao retain / vì sao guard (nếu partial-prune hoặc Layer 3)
Lý do 2–4 câu: consumer active nào, retain rẻ hơn sửa code ở đâu, hoặc vì sao nhánh active đó không còn chạy đúng.

## Runtime Entry Points
| # | Entry | Vị trí | Xử lý |
|---|---|---|---|
| 1 | `X_SHOW_LOBBY_ICON` | `LobbyModule.js:529` | fire-and-forget → Layer 1 |
| 2 | CMD `…` | module | Layer 1 ⇒ không route |

## Quarantine Edits
### `src/gamemgr/ModuleMgr.js` — Layer 1
| Dòng | Nội dung |
### Layer 2 / 3 — không cần | `<file>:<line>` guard …

## Dependency Phải Giữ Nguyên
| Symbol | Lý do |

## Animation của bundle (G10b)
| Stem | Type | MiB | Quyết định (xóa / chờ `<bundle>` / giữ) | Caller |
|---|---|---:|---|---|
Manifest `<bundle>-anim` (mode `group`): N stem, M file, B bytes — hoặc "không có".

## Open Questions — cần user quyết trước khi Move
| # | Câu hỏi | Recommend | Nếu chọn khác |
|---|---|---|---|
| 1 | Module X (guard-only) — feature còn phục vụ user nào không? | Guard + xóa JSON | Retain JSON + atlas (giữ thêm N KB) |
*(để trống nếu không có; bundle có G-item P1 phải có mục này)*

## Verify Checklist
**Agent:** N dòng ModuleMgr · retained đủ cặp · Layer 4 grep `PoolFunction[.]<PREFIX>_` → k call đã phân loại · `Verify` exit 0
**User:** <smoke theo đúng entry point ACTIVE: màn nào, hành động nào>
```

---

## Dev Status (A3)

```markdown
---
updated: YYYY-MM-DD
phase: A — Docs | B — batch i/N committed · smoke … · còn …
branch: <branch>
---
# <Task> — Dev Status

| # | Bundle | Mode | Trace | Manifest | Layer 1 | Audit | Move | Verify | Commit | Smoke | APK Δ |
|---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|:---:|---:|
| 1 | `<bundle>` | full-folder | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | — | ⬜ | — |

Cột `Commit` ghi hash. `Smoke` ghi ngày user test pass. `APK Δ` so với baseline (Known Issue nếu chưa có baseline).

## Chi tiết từng bundle
### `<bundle>` — ✅ commit `<hash>` · ⬜ chờ smoke
- Mode, số file/bytes, code sửa (file:dòng), điểm khác so với trace ban đầu.
- **User smoke:** <danh sách theo entry point ACTIVE>.

## Known Issues / Gaps
| ID | Mô tả | Priority | Trạng thái |
|---|---|---|---|
| G1 | … | P1/P2/P3 | Open / Closed <ngày> — cách xử lý |
```

Mọi phát hiện ngoài trace ban đầu (module dùng chung folder, false positive, crash) ghi thành **G-item** với priority; đóng G-item kèm commit hash. Đây là nguồn bài học để cập nhật skill.

---

## Implementation Plan (A4)

```markdown
# <Task> — Implementation Plan
> Design / Spec / Status: <paths>

## Tasks
### Task 1: Safety tool sẵn sàng
- [ ] `scripts/tests/run_tests.ps1` pass trên fixture · tool có trong skill, không cần viết lại
### Task 2: Manifest + batch 1–2 (bundle an toàn — validate tool)
- [ ] `gen_manifest.py` → `Audit` → `Move` → `Verify` → commit → dev-status → **User smoke**
### Task 3: Trace toàn bộ bundle còn lại — 1 lượt
- [ ] `trace_bundle.py` từng bundle → review → `spec/bundles/<b>.md` → `gen_manifest.py` → `Audit -DryRun`
- [ ] **Checkpoint duyệt 1 lần:** tập trung bundle có quyết định thật (retained list, Guard-Only, Layer 3)
### Task 4 → N: Batch loop (mỗi bundle 1 commit)
- [ ] Pre-Move guard (trace lại, so spec) · Layer 1 (`modulemgr_retire.py`) · Layer 2/3 theo spec · preload/cdn · patch → Audit → Move → Verify · Agent Verify · commit `chore (deletecontent): remove <bundle> content — N files, B bytes, backup <build>` · dev-status · User smoke
### Task N+1: QA final
- [ ] Acceptance Criteria design · APK Δ · scan artifact không còn path bundle · smoke tổng · `git log` N commit khớp dev-status · backup đủ `_meta`
```

Commit message (đuôi `Co-Authored-By` theo quy ước repo):

```
chore (deletecontent): remove <bundle> content — <N> files, <B> B, backup <build>[ (partial-prune)]

Layer 1: <Module> (<k> dòng ModuleMgr → region Deleted Content). <mode, retained gì, vì sao>.
Layer 4: <caller active đã phân loại>. 4b/4c: <kết quả>.
Animation (<bundle>-anim): <n> group <stem…> chỉ module này dùng — <m> file, <B> B; registry AniSource giữ nguyên. (bỏ dòng nếu không có)
Không xóa source JS. Backup + manifest (+ quarantine.patch) tại <backup>\<build>\_meta\<bundle>\ (và _meta\<bundle>-anim\).
```

Chỉ `git add` **path tường minh**: `src/gamemgr/ModuleMgr.js`, file Layer 2/3, `res/content/<b>`, `res#tcf_astc/content/<b>`, cdn.json nếu có. Không `git add -A` toàn repo (working tree của user có file khác).
