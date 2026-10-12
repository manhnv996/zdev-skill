---
name: dev-delete-feature-content
description: "Use when asked to delete or retire a closed BidaMobile Cocos 2dx JS feature/module by name to reduce APK size — removing its content (res/content/<bundle>, res#tcf_astc mirror, atlas .plist/.png, UI .json) and the animations only it uses, or when rolling back such a removal."
argument-hint: "[bundle-name | danh sách bundle | đường dẫn design doc]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, PowerShell
---

# dev-delete-feature-content — BidaMobile (Cocos 2dx JS)

Xóa content resource **và animation chỉ feature đó dùng** của feature đã đóng, **không xóa source JS**, có backup + rollback theo từng feature. Workflow 2 phase theo hình dạng `dev-feature`: **Phase A docs được duyệt trước khi Phase B đụng vào file**. Mỗi bundle cho ra tối đa 2 manifest cùng batch/commit: `<bundle>` (content, mode full-folder/partial-prune) và `<bundle>-anim` (animation, mode `group`).

**Nguyên tắc cốt lõi:** trạng thái module (không `init`) chỉ chứng minh packet và `PoolFunction` chết. Nó **không** chứng minh từng file an toàn — class retired có thể được code active **kế thừa**, util retired có thể được code active **gọi**, atlas có thể dùng chung frame. Mỗi file phải qua đủ gate trace. Code sửa ít nhất: `ModuleMgr` là điểm rollback duy nhất cho module fully retired.

**Violating the letter of the gates is violating the spirit of the task.** Một file sót = crash mọi lần đổi scene (đã xảy ra 2 lần trong task đầu).

---

## Khi nào dùng / không dùng

- Dùng: user muốn giảm APK bằng cách bỏ resource của feature đóng vĩnh viễn — input chỉ cần **tên module/feature** (module có thể đang đăng ký sống, không tag gì trong `ModuleMgr.js`); rollback 1 feature đã xóa; retire thêm module vào region `Deleted Content` / `Guard-Only`.
- Dùng cho **animation** (`res/animation` — group DragonBones/Spine, registry `AniSource`/`AniSpineSource`): đi theo `reference-animation-gates.md` (`trace_anim.py`, `gen_anim_manifest.py`), không có Layer 1/2/3, mục tiêu 0 dòng code.
- Không dùng: xóa config JSON, source JS, `project.json` entry (ngoài scope theo design đã chốt); feature chỉ tắt tạm bằng flag server; asset là CDN group trong `cdn.json` (không pack APK).

**REQUIRED BACKGROUND:** đọc `reference-quarantine-contract.md` trước khi quyết định bất kỳ dòng code nào.

---

## Bước 0: Thu thập & xác nhận

Đọc argument: đường dẫn design doc → normalize vào `docs/modules/<task>/design/`, checkpoint A1 ngắn; tên bundle → dùng làm scope gợi ý; không có gì → hỏi.

Xác nhận 6 mục (gợi ý sẵn, **không tự quyết một mình**):

1. **Module/feature → bundle.** Input thường chỉ là **tên module hoặc feature** (vd "xóa BuffetOfferModule"). Tool tự resolve: `python scripts/trace_bundle.py --module <Tên>` → tìm dòng `var X = new <Tên>Module()` trong `ModuleMgr.js` → file class → module dir → mọi `content/<folder>/` (literal + `res.<key>`) mà module dir tham chiếu → bundle = folder duy nhất/folder trùng tên (nhiều folder ⇒ tool dừng, bạn chọn `--bundle`; folder dùng chung như `system`/`lobby` không phải bundle). **Không cần tag `//D`** trong ModuleMgr — tag chỉ là dấu do skill gắn khi retire (`modulemgr_retire.py --retire` tự thêm `//D //<bundle>`), và "retired" được nhận diện bằng **ctor đã comment**, không bằng tag. Trình user: module, dir, folder content, kích thước — xác nhận feature đã đóng server trước khi trace tiếp. Bundle dùng chung folder với module khác? (vd `firstcharge` = 7 module + 3 feature active). Bundle nhiều module ⇒ quyết định **riêng từng module**: retire (Layer 1) hay Guard-Only (G7 có nhiều caller active dùng return value). Module Guard-Only vẫn chạy ⇒ GUI trong dir của nó là consumer active, phải có `return` guard (G0 gate báo THIẾU GUARD).
2. **Scope:** content only (mặc định) — không config, không animation, không tập tag khác.
3. **Build tag** (`build180`) và **branch** — ghi vào manifest, layer backup.
4. **Backup root** ngoài repo (mặc định `D:\workspace\BidaMobile\client-delete-content-backup\<build>\`).
5. **Docs path:** `docs/modules/<task>/` (mặc định `deletefeaturecontent`).
6. **Cách chạy:** batch đầu 1–2 bundle an toàn để validate tool → trace toàn bộ còn lại 1 lượt → duyệt 1 lần → batch liên tục chỉ smoke giữa các batch (mặc định, đã chứng minh hiệu quả).

---

# PHASE A — DOCS

> Mỗi step 1 file, user confirm xong mới sang step sau. Template: `reference-doc-templates.md`.

## A1 — Design doc
`docs/modules/<task>/design/<task>-design.md`: danh sách feature đóng + lý do, scope có/không, backup & rollback, acceptance criteria. **Checkpoint A1.**

## A2 — Master spec (1 lần) + bundle spec (mỗi bundle)

**Master spec** viết 1 lần: scope, files cần sửa toàn task, bundle index, quarantine contract (link reference), manifest schema, tool contract, backup layout, verification, batch order dễ→khó, Phase 2. **Checkpoint A2 master.**

**Bundle spec** — mỗi bundle 1 file, sinh từ trace:

1. `python scripts/trace_bundle.py --bundle <b>` → `docs/modules/<task>/trace/report_<b>.md` (đủ 12 gate G0–G11, xem `reference-trace-gates.md`).
2. **Mở từng dòng ACTIVE** trong G2/G3/G7/G8/G9 — xác nhận full path, atlas nào được load, caller dùng return value không, body util có construct không. Bảng cuối report **"Tổng kết — file GIỮ LẠI"** (chỉ file không xóa được ngay; XÓA/ĐÃ XÓA chỉ đếm ở dòng Tổng, đủ trong `trace/files_<b>.tsv`): cột **File | Size | Frame/ảnh active dùng | Consumer active** — 1 hàng/atlas, Frame = `k/n frame:` + danh sách; Consumer 2 hàng: `UI JSON:` file → node (`;` giữa các file, ≥3 file cùng tên gốc gom `folder/prefix*.json ×n`) và `JS:` file:dòng. Ở A2 bảng này chỉ là dữ liệu trong report để viết bundle spec (user quyết trên spec); **dán bảng vào chat ở bước 12 Phase B** (recap sau commit). Mục *Đề xuất* nằm dưới bảng, không trộn vào dữ kiện. Tool xuất kèm `summary_<b>.html` (rowspan + xuống dòng thật) — chỉ là phụ. Không dùng `<br>` trong bảng (nhiều viewer không render).
3. Phân loại 4 nhóm → quyết định mode, retained list, Layer 2/3, Guard-Only.
3b. **G5b Downloader runtime:** caller **khởi phát** ACTIVE phải = 0 (`listGroupInQueue`, `checkExistAssetFileByGroupName`, `showDL(`, `addGroupToQueue`…). Bundle có group trong `gv.groupDL`/`GROUP_INFO` ⇒ ghi vào spec mục "Dọn downloader": key `gv.groupDL.<key>`, entry `GROUP_INFO`, nhánh `getGroupDLName`, nhánh folder/fileCheckList `GroupMinigameAssetUtil`, chuỗi `||` `LayerDLBackground`/`GuiPlay` — comment kèm marker (Phase B row 4b).
4. **G10b Animation:** report liệt kê group DragonBones/Spine có usage trong module dir của bundle với 3 quyết định — **xóa** (chỉ bundle này dùng, hoặc chung với bundle đã Layer 1) · **chờ** (còn module chưa retire dùng — bundle sau sẽ xóa) · **giữ** (ACTIVE/Guard-Only/họ động/config). Danh sách xóa được ghi sẵn `trace/anim_<b>.stems.txt`. Mở từng dòng "xóa" xác nhận caller (xem `reference-animation-gates.md`); `preloadAllAnimation` phải 0 caller.
5. Viết `spec/bundles/<b>.md` theo template (có mục Animation). `unresolved` phải = 0.
6. `python scripts/gen_manifest.py --bundle <b> --build <build> --branch <branch> [--retained …]` → `Audit -DryRun` pass. Có animation ⇒ thêm `python scripts/gen_anim_manifest.py --bundle <b>-anim --from-file trace/anim_<b>.stems.txt --build <build> --branch <branch>` → `Audit -DryRun` pass.

Batch đầu (1–2 bundle an toàn) viết spec ngay; các bundle còn lại **trace 1 lượt** sau khi tool đã chạy thật. **Checkpoint duyệt 1 lần** cho toàn bộ bundle spec: trình những bundle có quyết định thật (retained list, Guard-Only, Layer 3) — đừng bắt user đọc bundle không có gì để quyết.

## A3 — Dev status
`docs/modules/<task>/dev-status.md`: bảng lifecycle (Trace · Manifest · Layer 1 · Audit · Move · Verify · Commit · Smoke · APK Δ) + Known Issues (G-item có priority). Cập nhật sau **mỗi** batch.

## A4 — Plan
`docs/modules/<task>/plans/<date>-<task>-plan.md`: tool → batch 1–2 → trace 1 lượt → checkpoint → batch loop → QA. **Checkpoint A4**, rồi hỏi: "Bắt đầu Phase B?"

---

# PHASE B — THỰC THI (mỗi bundle = 1 batch = 1 commit)

## Execution Guard
Sau compact/resume: đọc lại section này, plan (task unchecked đầu), `dev-status.md` (bundle nào đang ở bước nào), manifest `status`. Không chắc bước trước đã Verify ⇒ chạy `-Action Verify` lại trước khi làm tiếp.

## Vòng lặp chuẩn cho 1 bundle

| # | Bước | Lệnh / điều kiện |
|---|---|---|
| 1 | **Pre-Move guard** | `trace_bundle.py` lại; G7/G8/G9 ACTIVE khác bundle spec đã duyệt ⇒ **dừng, hỏi** |
| 2 | Layer 1 | `python scripts/modulemgr_retire.py --retire <var> <bundle>` (mỗi module của bundle); gate `grep "<var>" ModuleMgr.js \| grep -v ':\s*//'` = 0. Guard-Only ⇒ `--guard-only <var> "<note>"` |
| 3 | Layer 2/3 | **chỉ** những gì bundle spec ghi (file:dòng). Guard đặt trong module retired, callback gọi trước `return` |
| 4 | Preload / CDN | `ResourceImage.js`: comment dòng `res.<key>` **chỉ khi atlas bị xóa**, marker `//deleted content <bundle> <build>`. `cdn_prune.py --folder <b> --group <g>` khi G5 có hit. Không đụng `src/resource.js` |
| 4b | Downloader | G5b có group ⇒ comment (marker `//deleted content <build>: group đã xóa content…`) key `gv.groupDL.<key>`, entry `GROUP_INFO`, mọi nhánh passive so tên group (LayerDL/LayerDLBackground/GroupMinigameAssetUtil/GuiPlay); `node --check` từng file. Gate: `grep -rn "gv\.groupDL\.<key>" src/ \| grep -v ':\s*//'` chỉ còn dòng trong module retired. **Điều kiện tiên quyết:** `gv.showDL` phải có guard `featureDownloadData == null` → top notify `dl_update_fail` + return (có từ `e4a9137ac`); branch chưa có guard ⇒ thêm trước, nếu không group `undefined` làm layer download hiện mãi (treo mềm) |
| 5 | Layer 4 gate | `grep -rn "PoolFunction[.]<PREFIX>_" src/ \| grep -vE "^(<retired dirs>)/" \| grep -v CmdDefine.js \| grep -v src/base/PoolFunction.js \| grep -v ':\s*//'` → đúng số + đúng dòng trong spec. **Expect = G7 của `trace_bundle.py`** (đã loại cả `/* */`); grep tay chỉ loại `//` nên có thể lệch +k ⇒ kiểm block comment trước khi kết luận |
| 6 | Patch | `git diff -- <mọi file code đã sửa> > docs/modules/<task>/manifests/<b>.quarantine.patch` (kiểm số dòng +/-) |
| 7 | Tool | Manifest phải trỏ **BackupRoot thật** (manifest sinh lúc trace với scratch ⇒ regen hoặc sửa field). `-Action Audit` → `Move` → `Verify` đều exit 0 (gọi qua `powershell -NoProfile -ExecutionPolicy Bypass -File …`). Refuse "file đích đã tồn tại" chỉ phát hiện được với BackupRoot thật. Trong script: `set -o pipefail`/`${PIPESTATUS[0]}`, và **đọc `status` trong manifest = `verified` trước khi commit** |
| 7b | Animation | Nếu G10b có "xóa": `gen_anim_manifest.py --bundle <b>-anim --from-file trace/anim_<b>.stems.txt …` (mode `group`, patch rỗng) → `Audit` → `Move` → `Verify` như trên. Không sửa `AnimationMgr` registry |
| 8 | Agent Verify | checklist dưới |
| 9 | Commit | `git add` **path tường minh** (ModuleMgr, file Layer 2/3, `res/content/<b>`, `res#tcf_astc/content/<b>`, cdn.json, **+ `res/animation` `res#tcf_astc/animation` nếu có 7b**); staged count = removed content + removed anim + code files; message theo `reference-doc-templates.md` (ghi cả số animation); đuôi `Co-Authored-By` theo repo. **Không push** |
| 10 | Docs | dev-status (hash, cột lifecycle, section bundle + smoke list), plan tick, bundle spec `status: implemented` |
| 11 | **User Verify** | smoke theo entry point ACTIVE trong bundle spec; ghi ngày pass vào dev-status. Fail ⇒ `Restore` đúng bundle, systematic-debugging, ghi G-item |
| 12 | **Recap** | chạy lại `trace_bundle.py --bundle <b> --skip-anim` (đọc manifest `verified` ⇒ ĐÃ XÓA/GIỮ đúng hiện trạng) và **dán bảng "Tổng kết — file GIỮ LẠI" vào chat**: còn giữ file nào, frame nào, consumer nào — kèm Đề xuất (re-pack / Layer 2 / Layer 3) để user quyết đợt 2 nếu muốn |

Đóng gói nhiều batch trong 1 script `.sh` (retire → gate → patch → Audit/Move/Verify → commit với `[ "$N" -eq <expect> ] || exit 1`) — mọi gate có số expect rõ, abort khi khác. Bash tool: đặt lệnh dài vào file, không one-liner có `\\`.

## Agent Verify — mỗi bundle
- [ ] Manifest `status = verified`; `removed`/`retained` khớp bundle spec từng path
- [ ] Không còn `<var>` sống trong ModuleMgr (hoặc guard-only đúng region + marker)
- [ ] Layer 4 grep = bản đã duyệt; G8/G9 ACTIVE có guard hoặc resource retained
- [ ] `ResourceImage.js` không còn preload path đã xóa; `cdn.json` không còn group/path đã xóa
- [ ] G5b: `gv.groupDL.<key>` sống chỉ còn trong module retired; `GroupMinigameAssetUtil.listGroupInQueue` không chứa group; `gv.showDL` có guard group lạ
- [ ] `res/content/<b>` + astc: full-folder ⇒ gone; partial ⇒ chỉ retained còn, đủ cặp plist/png/astc
- [ ] Có `<b>-anim`: manifest `verified`; không còn file nào của các stem trong `res/animation/**` + astc; folder `config/texture/atlas` vẫn còn; `AnimationMgr.js` không đổi
- [ ] `git status` chỉ chứa file thuộc bundle + code trong spec — không lẫn file uncommitted của user
- [ ] Backup `_meta\<b>\{manifest.json, quarantine.patch}` tồn tại

## User Verify — tối thiểu
Launch → login → lobby (không log missing texture/JSON) → vào bàn → rời bàn → logout/login → reload config; feature **active** dùng chung folder render đủ; entry point ACTIVE cụ thể trong bundle spec.

## B-QA cuối task
Acceptance criteria design → APK Δ (cùng flavor/ABI, ghi dev-status) → scan artifact không còn path bundle → smoke tổng → `git log` N commit khớp dev-status → backup đủ `_meta` → dev-status phase Done → cập nhật skill này với G-item mới.

---

## Red Flags — dừng và quay lại gate

| Suy nghĩ | Thực tế |
|---|---|
| "Consumer duy nhất là `X.js:24`" sau grep literal path | Chưa qua G3/G4/G8/G9. Baseline không skill đã xóa nhầm JSON được lớp con active kế thừa |
| "Chỉ cần comment 4 dòng ModuleMgr là đủ" | Đủ cho packet/PoolFunction. Không đủ khi folder dùng chung, class được kế thừa, util được gọi |
| "Comment preload / `resource.js` cho chắc" | Sửa thừa = thêm file phải revert. Chỉ sửa khi atlas bị xóa và dòng đó thực sự load |
| "Backup copy ra ngoài rồi `git rm`" | Không SHA, không lifecycle, không patch rollback. Dùng tool |
| "Module không init nên mọi thứ của nó an toàn" | Sai cho 4b/4c/G3 — đã gây crash thật |
| "Guard ở caller cho gọn" | Guard trong module retired; caller active không đổi |
| "Trace bằng grep tay nhanh hơn" | 49 lần grep vẫn sót; `trace_bundle.py` 1 lệnh đủ 12 gate |
| "Basename khớp ⇒ đang dùng" | Kiểm full path và folder của file tham chiếu (duplicate atlas) |
| "Xóa luôn animation của module này" | Ngoài scope; registry `AniSource` dùng chung 4 feature (G1 thật) |

## Common Mistakes (đã gặp)
- Regex prefix trần (`RACE_EVENT_`) match constant khác → luôn `PoolFunction[.]PREFIX_`.
- `.ps1` không BOM → tokenizer vỡ; script Python đọc ModuleMgr text-mode → CRLF→LF 896 dòng diff (dùng `newline=''`).
- Grep tool từ repo root trả rỗng/timeout → grep theo `src/`, `res/` hoặc dùng script.
- Gate 4b đặt "expect 0" trong khi có util pure-data hợp lệ → expect = tập đã phân tích, ghi rõ trong spec.
- Manifest viết tay bytes/sha → để tool điền. `gen_manifest.py --only` không ghi đè manifest đã audited.
- Đặt guard `if (!_isEnable)` mà module vẫn `init` (guard-only) → `_isEnable` do server set; guard-only phải `return` vô điều kiện trong hàm show GUI.
- Grep gate tay đếm cả dòng trong `/* … */` → lệch với G7 (`GuiPMZing.js:242`); dùng số của `trace_bundle.py` làm expect.
- Marker `//guard-only` ghi "GUI đã return-guard" nhưng module chưa có guard (FirstTel, FirstDeal lúc chuyển region) → G0 gate báo THIẾU GUARD; thêm guard **trong batch của bundle đó**, không để marker hứa trước.
- Chuỗi `Move/Verify` không dry-run được (cần status thật) → thử trọn vòng bằng fixture `scripts/tests/`, không thử trên repo.
- Script Python ad-hoc trên Windows ghi comment tiếng Việt → crash cp1252: luôn `io.open(..., encoding='utf-8', newline='')` và `PYTHONIOENCODING=utf-8` (4 script của skill đã tự `reconfigure`).
- Ghi chú hardening `ScreenMgr` (try/finally) có thể **chưa có trên branch đang làm** → `grep -n finally src/base/screen/ScreenMgr.js` trước khi coi crash ctor screen là "chỉ 1 lần".
- **G5b bỏ sót khởi phát download đi qua util riêng của feature** (`VipAssetUtil.checkAutoUpdateDownloadContent()` gọi từ `LobbyScreen` ACTIVE; util nằm ở `src/base/download/util/`, không trong module dir): regex G5b chỉ bắt `gv.groupDL.<key>` trực tiếp. Bundle có group downloader ⇒ grep tay `<Feature>AssetUtil.` ngoài module dir, comment dòng khởi phát ACTIVE; util đó để nguyên (dead sau guard).
- **Guard-Only thực chiến (vip):** G7 có ≥10 caller ACTIVE `doFunc(X).field` ở payment/shop ⇒ đừng Layer 1 hay Layer 2 hàng loạt; `--guard-only` 2 module + `return` vô điều kiện ở **mọi** hàm construct GUI trong module, kể cả hàm check mà packet handler dùng để quyết định show (`checkHaveOfferVip → return false` chặn 3 đường 1 lúc). Getter phải tự tạo object mặc định (`getMyVipInfo` `new VipInfo()`) — kiểm trước khi chốt.
- Bỏ key `gv.groupDL.<key>` khi module retired vẫn còn `gv.showDL(gv.groupDL.<key>, …)`: không crash (`undefined`) nhưng `gv.showDL` cũ show layer trước khi tra `GROUP_INFO` ⇒ layer hiện mãi, callback không gọi. Guard `e4a9137ac` xử lý bằng top notify `dl_update_fail` + return (không callback để không mở feature với resource đã xóa) — kiểm guard có trên branch trước khi dọn downloader.
- Module **đã bị comment sẵn** trong ModuleMgr (feature đóng từ trước, vd LuckyShoot) nhưng content còn: `--retire` (v1.6) nhận cả dòng `//var X = new …` ngoài region → dời vào region + gắn `//D //<bundle>`; test trên **bản copy** ModuleMgr (4 dòng / idempotent 0 / đã-trong-region 0 / module sống 4) trước khi chạy thật.
- GUI của module retired được `new` từ file ACTIVE (G8 CẦN QUYẾT) — trace **caller của hàm chứa `new`** trước khi thêm Layer 3: nếu caller duy nhất nằm trong module retired (vd `RoomScreen.initLuckyShoot` ← `showForLuckyShoot` ← `LuckyShootModule`) ⇒ dead, XÓA JSON, không sửa code.
- `sed | cat -A` / `grep -c $'$'` trong Git Bash **không thấy CRLF** (MSYS chuyển đổi trong pipe) → đừng kết luận file là LF; script sửa code luôn tự dò `
` trong nội dung và ghép chuỗi so khớp theo line ending đó (SlotGift/ResourceImage/GuiPlay đều CRLF, LayerDL LF).
- Heredoc Bash nuốt `\` → chuỗi Python `'\r\n'` thành xuống dòng thật, file script vỡ syntax → script Python đặt trong file (Write tool) và dùng `chr(13)+chr(10)` thay literal escape.
- **Bug gate script batch (ca thật B1 animation):** `powershell … | grep -E "OK|FAIL" || abort` — exit code của tool bị `grep` nuốt (grep match "FAIL" ⇒ exit 0) ⇒ script commit dù Verify FAIL. Luôn `set -o pipefail` hoặc lấy `${PIPESTATUS[0]}`; và **kiểm `status=verified` trong manifest trước `git commit`**.
- Xóa theo nhóm file trong folder dùng chung (animation) phải dùng `removalMode: group` — `full-folder` đòi folder cha biến mất ⇒ Verify FAIL 5 lỗi dù SHA khớp.
- **Đi tìm tag `//D` trong ModuleMgr để biết module nào xóa** — sai: repo thật không có tag; tag là dấu do `--retire` gắn. Resolve từ **tên module** (`--module`), retired = ctor đã comment. Module `//remove`/không tag đang sống vẫn là ACTIVE cho tới khi user yêu cầu xóa.
- **Atlas retained vì 1 frame icon quà trong `SlotGift.js`** (`es_item`, `stickBox5`, `x2BattlePassBall`…): feature đóng ⇒ server không trả gift đó ⇒ comment case kèm lý do (fallback `icon_random.png`), xóa atlas — đừng giữ 100–300 KB cho 1 icon. Nhưng **kiểm JSON retained trong cùng folder** trước: `guiThankfulMonth.json` (active) khai báo `FirstChargeContent.plist` ⇒ atlas đó vẫn phải giữ. Scan "frame dùng ngoài folder" không thấy consumer nằm trong folder.
- **Edit tool trên file mixed CRLF/LF** (`SlotGift.js`) làm churn line ending ở hunk khác (68 dòng diff thay vì 8) → `git checkout` file rồi áp lại bằng Python `io.open(..., newline='')`; luôn kiểm `git diff --stat` = số dòng sửa thật trước khi patch/commit.

---

## Quick Reference

```bash
S=.claude/skills/dev-delete-feature-content/scripts
python $S/trace_bundle.py --module <TênModule>            # tự resolve bundle từ ModuleMgr → module dir → content/<folder>/ (khuyên dùng)
python $S/trace_bundle.py --bundle <b> [--module-var <var> --module-dir <dir>] [--repo-root .] [--out docs/modules/<task>/trace] [--skip-anim]
python $S/gen_manifest.py --bundle <b> --build build180 --branch <branch> [--retained <p>]...
python $S/modulemgr_retire.py --init-regions | --retire <var> <b> | --guard-only <var> "<note>"
python $S/cdn_prune.py --folder <b> --group <name> [--dry-run]
powershell -NoProfile -ExecutionPolicy Bypass -File "$PWD/$S/delete_feature_content.ps1" -Action Audit|Move|Verify|Restore -Bundle <b> [-DryRun]
bash $S/tests/make_fixture.sh && powershell -NoProfile -File "$PWD/$S/tests/run_tests.ps1"   # 41 ca tool
# animation (Phase 2)
python $S/trace_anim.py [--out docs/modules/<task>/phase2-animation/trace] [--only <stem>]
python $S/gen_anim_manifest.py --bundle anim-<x> --build build180 --branch <branch> (--class retired-only | --stem <k>... | --from-file <txt>)
```

| File | Nội dung |
|---|---|
| `reference-trace-gates.md` | 12 gate G0–G11, kind hit, đọc report, 4 nhóm phân loại, false positive, pre-move guard |
| `reference-animation-gates.md` | Phase 2: group DragonBones/Spine, registry + wrapper 2 hop, AG1–AG8, soát tay T1/T2, vòng lặp batch animation |
| `reference-quarantine-contract.md` | 2 fact runtime, Layer 1/2/3/4/4b/4c, Guard-Only, sửa gì/không, rollback |
| `reference-manifest-schema.md` | schema, lifecycle, dependency group, tool contract, refuse, backup layout |
| `reference-doc-templates.md` | design / master spec / bundle spec / dev-status / plan / commit message |

## Phase 2 — Animation (`reference-animation-gates.md`)
`res/animation/{config,texture,atlas}` phẳng, resolve qua registry `AniSource`/`AniSpineSource` trong `AnimationMgr.js`; đơn vị xóa = **group theo tên** (DragonBones xml+plist+png+astc · Spine json+atlas+png-theo-.atlas+astc). Không Layer 1/2/3, 0 dòng code. Bắt buộc: AG2 quét cả wrapper trong `AnimationMgr` (2 hop), AG3 họ tên động, AG6 `preloadAllAnimation` = 0 caller, soát tay từng ORPHAN trước khi xóa (T1 xóa / T2 user duyệt). Tool `.ps1` dùng nguyên trạng với `-ManifestDir` trỏ `phase2-animation/manifests`.
