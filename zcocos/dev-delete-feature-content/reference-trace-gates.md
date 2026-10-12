# Reference — Trace Gates (G0–G10) & Classification

Mọi bundle đi qua **đủ 12 gate (G0–G11)** bằng 1 lệnh, rồi review tay từng dòng report. Không trace bằng grep tay rải rác — baseline cho thấy 49 lần grep vẫn sót kế thừa class. G8 phân biệt class **GUI/Node** (ctor load resource) và **data model** (cc.Class, không load gì) — chỉ GUI/Node mới là rủi ro; cột "guard gần" là heuristic 15 dòng, vẫn phải mở hàm chứa để xác nhận.

```bash
python .claude/skills/dev-delete-feature-content/scripts/trace_bundle.py --bundle <b> [--repo-root <path>] [--out <dir>]
# → <out>/report_<b>.md + inventory_<b>.tsv ; default out = docs/modules/deletefeaturecontent/trace/
# --module-var <var> / --module-dir <dir>   : module không có tag //<bundle> trong ModuleMgr
# --extra-retired-dir <dir>                  : dir coi là retired ngoài auto
# --no-auto-retired                          : không coi module //D khác là retired
```

Module của bundle: dùng `--module <Tên>` — tool tìm dòng `var X = new <Tên>Module()` trong `ModuleMgr.js` (khớp class/var, không cần tag), module dir = dirname file định nghĩa class, bundle = folder `content/<x>/` mà module dir tham chiếu (literal hoặc `res.<key>`); nhiều folder ⇒ chọn `--bundle`. **Retired dir** = module có ctor **đã comment** trong ModuleMgr (bất kỳ lý do) hoặc có tag `//D`; module sống không tag = ACTIVE; module có marker `//guard-only` sống = `GUARD-ONLY(active)`. Report gắn kind cho mỗi hit: `module` / `retired-other` / **`ACTIVE`** / `GUARD-ONLY(active)`. Tag `//D //<bundle>` chỉ là dấu do `modulemgr_retire.py --retire` gắn khi comment — không phải điều kiện đầu vào.

## Bảng gate

| Gate | Phát hiện | Đọc thế nào | Quyết định |
|---|---|---|---|
| **G0** ModuleMgr | var/class/dir, ctor line, LIVE/commented, marker guard-only, các dòng init/reset | Đủ 3–4 dòng? Có module nào cùng tag nhưng khác folder code? | Danh sách var cho `modulemgr_retire.py` |
| **G1** Inventory | mọi file res + ASTC, bytes, parity | Parity LỆCH ⇒ có ASTC không có bản gốc hoặc ngược lại | Sửa inventory/manifest trước |
| **G2** Consumer từng file | literal `content/<b>/f` · basename-only · res JSON ngoài folder (đánh dấu `DUP-in-own-folder` khi folder JSON có file cùng tên) | Cột class: `Retired` / `ACTIVE-CONSUMER` / `ORPHAN?`. Basename-only **phải mở file xác nhận** full path | ACTIVE-CONSUMER ⇒ retain hoặc Layer 3 (xem dưới). ORPHAN? ⇒ xác nhận thêm field `"Plist"`/frame trong JSON khác, `git log` |
| **G3** Atlas frame | frame trong `.plist` bundle được dùng ở file ngoài folder; tách **chỉ có ở bundle** vs **trùng tên atlas khác** (ambiguous); liệt kê JSON **trong folder bundle** khai báo atlas | Sprite frame cache global theo tên. ACTIVE dùng frame chỉ-có-ở-bundle ⇒ atlas retained, **trừ** khi consumer duy nhất là `SlotGift.js` case `giftInfo.name == "<gift feature đóng>"` ⇒ **Layer 2 comment case** (fallback `icon_random.png`) và xóa atlas (ca `es_item`). JSON retained trong bundle khai báo atlas (`"Plist"`) ⇒ atlas **phải** retained (ca `guiThankfulMonth.json` → `FirstChargeContent`) | Ambiguous ⇒ xem atlas nào được `addSpriteFrames` (thường bản trong folder của feature active — bản trong bundle là duplicate chết) |
| **G4** `res.<key>` | key trong `src/resource.js` trỏ vào bundle + usage ngoài retired dir (thường `ResourceImage.js` preload) | Preload là *loader*, không phải consumer | Atlas xóa ⇒ comment dòng `ResourceImage.js`; atlas retained ⇒ giữ. **Không sửa `resource.js`** |
| **G5** CDN | `build/**/cdn.json` có `res/content/<b>/` hoặc group path | Group được request từ đâu? (`listGroupInQueue`, downloader) | Chỉ từ module retired ⇒ `cdn_prune.py --folder <b> --group <name>` (28 file, line-based) |
| **G5b** Downloader runtime | group của bundle trong `src/base/download` (`gv.groupDL.<key>` ↔ `GROUP_INFO[name].PATH_TO_RESOURCE = res/content/<b>/`) → mọi chỗ dùng `gv.groupDL.<key>` ngoài module | **passive** = nhánh `if (groupName == …)` map tên/folder/UI theo groupName truyền vào (vô hại) · **khởi phát** = `listGroupInQueue`, `downloadGroup*`, `checkExistAssetFileByGroupName`, `addGroupToQueue`, `showDL(` | Khởi phát ở ACTIVE ⇒ phải đổi group / comment trước khi xóa (ca thật: `LuckyShootModule:281` check `minigameLuckyCue` = copy-paste từ BidaRace — may là module cũng đã đóng). Kiểm `GroupMinigameAssetUtil.listGroupInQueue` (danh sách tải khi unlock minigame) không còn group này ở dòng sống. **Dọn sau xóa** (commit riêng `d9da4ec69` cho baucua/luckyshoot/bidarace/exchangesubstance): comment key `gv.groupDL`, entry `GROUP_INFO`, mọi nhánh passive — chỉ khi `gv.showDL` đã có guard group lạ (`e4a9137ac`) **Giới hạn đã biết:** không bắt khởi phát qua `<Feature>AssetUtil.check*DownloadContent()` (ca vip: `LobbyScreen.js:493`) — grep tay khi bundle có group downloader |
| **G6** Dynamic path | `content/<b>` ghép chuỗi không kèm tên file (rank image, Spine `AniPathFolder`) | Trong module dir ⇒ Layer 1 đủ | ACTIVE ⇒ phải xử lý (Layer 3) |
| **G7** PoolFunction | constant regFunc trong module → caller ngoài; `fire-and-forget` vs `RETURN-VALUE?` | RETURN-VALUE ở ACTIVE: `undefined` có an toàn không? Default hiện tại là gì? | Nhiều caller dùng default ≠ undefined ⇒ **Guard-Only**; crash-case đơn lẻ ⇒ Layer 2 |
| **G8** Layer 4c/3 | `new X(` / `= X.extend(` với **mọi** class retired, ở code ngoài module | EXTENDS từ ACTIVE ⇒ ctor cha load JSON | EXTENDS ⇒ **retain JSON** (kiểm method kế thừa dùng frame không). `new` từ ACTIVE ⇒ Layer 3 (guard tại util/module) |
| **G9** Layer 4b | `X.fn(` với X định nghĩa trong module (kể cả object không `var`), body construct/load?, guard `_isEnable`? | construct + caller ACTIVE ⇒ crash khi resource mất | Guard đầu hàm util, trả safe default đúng kiểu. pure-data ⇒ giữ |
| **G10** CMD | CMD module handle (Layer 1 ⇒ không route) | Chỉ inventory | — |
| **G10b** Animation của bundle | gọi `trace_anim.analyze` (AG1–AG8): group DragonBones/Spine có usage (trực tiếp hoặc qua wrapper `AnimationMgr`) trong module dir của bundle | **xóa** = chỉ bundle này dùng, hoặc chung với bundle đã Layer 1 · **chờ** = còn module chưa retire dùng (bundle sau xóa) · **giữ** = ACTIVE/Guard-Only/họ động/config/CDN | "xóa" → `trace/anim_<b>.stems.txt` → `gen_anim_manifest.py --bundle <b>-anim --from-file` (mode `group`). `preloadAllAnimation` phải 0 caller. Mở từng dòng xóa xác nhận caller (xem `reference-animation-gates.md`). `--skip-anim` để bỏ qua |
| **G11** `*.manifest` | entry `content/<b>/` trong manifest legacy AssetsManager (`download.manifest`) ở repo root / `res/` | Chỉ thông tin | **Không sửa** — downloader chỉ so md5 file có trong manifest local; các batch trước không đụng |

**Kind của hit:** `module` (dir module retire — an toàn sau Layer 1) · `retired-other` (dir module `//D` khác) · **`ACTIVE`** · **`GUARD-ONLY(active)`** (dir module Guard-Only — module vẫn `init` nên consumer ở đó chạy thật; xử lý như ACTIVE: retain hoặc Layer 3 chặn đường construct ngay trong module đó). G0 in thêm **Guard-Only gate**: số hàm `show*/open*/popup*` có `return` guard — THIẾU GUARD ⇒ việc của batch này.

`Verdict` cuối report chỉ là gợi ý mode. **Không copy verdict vào spec khi chưa mở từng dòng ACTIVE.**

## Tổng kết — file GIỮ LẠI (cuối report + `trace/files_<b>.tsv` + `summary_<b>.html`)

**Bố cục chốt với user 2026-09-10 (v11):** chỉ liệt kê file GIỮ / CẦN QUYẾT / XÓA?; XÓA và ĐÃ XÓA (theo manifest) chỉ đếm ở dòng Tổng. Cột `File | Size | Frame/ảnh active dùng | Consumer active`. Mỗi dependency group 1 hàng chính (File = tên + quyết định; Size; Frame = `k/n frame:` + danh sách phẩy) và Consumer tách **2 hàng**: `**UI JSON:** folder/file.json node a, b; folder/other.json node c; folder/prefix*.json ×n node d` rồi `**JS:** File.js:dòng1, dòng2`. Không dùng `<br>`, không tách hàng theo từng frame/file (user đã thử và bác). *Đề xuất* (re-pack / Layer 2 / Layer 3) đặt **dưới bảng**. Thời điểm: ở **A2** bảng chỉ là dữ liệu trong report (user quyết trên bundle spec); **sau Phase B** (bước 12 Recap) agent chạy lại trace và **dán bảng vào chat** để nhắc còn giữ gì, vì đâu. Bản HTML `summary_<b>.html` có rowspan + xuống dòng thật, xuất kèm cho ai muốn mở trình duyệt.

### Ý nghĩa cột / nguồn dữ liệu

Mọi file trong `res/content/<b>` + astc, gom theo **dependency group** (atlas = `X.plist + .png + astc ×1`; JSON/ảnh rời từng dòng): **Bundle | File | Size | Frame/ảnh active dùng | Consumer active | Quyết định**. Cột Consumer ghi **node Cocos Studio** (`room/guiResultVersus.json node imageTitle, imageX2`) cho UI JSON và **file:dòng** cho code; ≥3 file cùng folder gom `folder/ ×n`. In ở **Phase A** (trace) và **pre-Move Phase B**; nếu bundle đã có manifest `moved/verified` (đợt 1, đợt 2…) thì các file đã xóa hiện thành **ĐÃ XÓA** — chạy lại sau khi xóa vẫn ra bức tranh đủ của cả folder (trả lời "vì sao còn giữ ảnh X" bằng chính bảng này).

| Quyết định | Nghĩa | Việc cần làm |
|---|---|---|
| **XÓA** | 0 consumer active; texture/astc theo atlas/bản gốc bị xóa | vào `removed` |
| **GIỮ** | JSON được active `syncAllChild`; atlas có frame active dùng (ghi `k/n frame` + file:dòng); JSON **giữ lại trong folder** khai báo atlas; ảnh rời được JSON giữ lại tham chiếu | vào `retained` **cả dependency group**; hoặc Layer 3 nếu nhánh active đó đã chết |
| **CẦN QUYẾT** | consumer active duy nhất là `SlotGift.js` case `giftInfo.name` (icon quà server) | hỏi user: Layer 2 comment case (fallback `icon_random.png`) rồi XÓA |
| **XÓA?** | frame chỉ trùng tên với atlas khác (duplicate) | xác nhận atlas nào được `addSpriteFrames` |

Với atlas GIỮ, dòng "Ai dùng" gom consumer theo folder (`res/content/room/ ×6 (guiRoomUserInfo.json…)`) và kèm **gợi ý phương án** (re-pack k frame sang atlas dùng chung + sửa n UI JSON / m chỗ JS; hoặc Layer 2 nếu chỉ SlotGift). Bảng phụ **"Chi tiết frame giữ atlas"** liệt kê từng frame → consumer → loại (UI JSON Cocos Studio / SlotGift icon quà / JS) — UI JSON tham chiếu frame theo tên nên xóa atlas đòi art re-pack + đổi tham chiếu, không sửa được bằng code thuần.

Trình user bằng chính bảng này (lọc GIỮ/CẦN QUYẾT) khi họ hỏi "vì sao còn giữ ảnh X". Stdout của tool in các dòng không xóa được ngay. Ca mẫu: `battlePassContent` 2.85 MiB giữ vì 7/90 frame ← `room/guiRoomUserInfo*.json` ×6, `room/guiResultVersus.json`, `pm/*Slot.json` ×3, `SlotGift.js`.

## Phân loại 4 nhóm → manifest

| Nhóm | Điều kiện | Manifest |
|---|---|---|
| Retired | mọi consumer đều trong module dir / retired-other | `removed` |
| Orphan | 0 consumer sau khi kiểm `"Plist"` ref, frame ref, git log; hoặc duplicate chết (`DUP-in-own-folder`) | `removed` (ghi lý do trong spec) |
| Retained dependency group | consumer ACTIVE hợp lệ (G2/G3/G8-EXTENDS) và **giữ rẻ hơn sửa code** | `retained` — cả group (plist+png+astc) |
| Cần Layer 3 | consumer ACTIVE nhưng feature đóng ⇒ nhánh đó không bao giờ chạy đúng nữa (offer đã hết, telco đã tắt) | `removed` + guard trong module retired |

Nguyên tắc chọn giữa retain và guard: **0 dòng code > guard trong module retired > sửa caller active**. File nhỏ (<200 KB) có consumer active hợp lệ ⇒ retain. Đừng "tiết kiệm" vài trăm KB bằng cách sửa code active.

## False positive đã gặp — phải kiểm

| Kiểu | Ví dụ | Cách xác nhận |
|---|---|---|
| Basename trùng, folder khác | `EuroContent.plist` trong `worldcup/` — euro có bản riêng `res/content/euro/EuroContent.plist` | G2 cột res JSON: `DUP-in-own-folder` ⇒ không phải consumer. G3 cột ambiguous |
| Constant chứa prefix | grep `RACE_EVENT_` match `ITEM_NAME_RACE_EVENT_LIVE` (SlotGift) | luôn grep `PoolFunction[.]<PREFIX>_` |
| Tên method trùng | `fn: function` cùng tên ở object khác | G9 chỉ ghép `X.fn` với X là identifier của module |
| Bảng `res` | `src/resource.js:113` xuất hiện khi grep basename | Không phải consumer — G4 xử lý |
| Frame trùng tên ở atlas khác | `pm_telco_ruby_change.png` (PMContent) vs `telco_ruby_change.png` (7dayContent) | G3 tách 2 cột; frame cache lấy atlas load sau cùng |
| `//D` nhưng module thật sự đang phục vụ active | `FirstDealModule` là backend offer NewShop | G7 RETURN-VALUE nhiều caller ⇒ Guard-Only |

## Từ report → bundle spec

Bundle spec (template ở `reference-doc-templates.md`) chép **kết quả đã review**, không chép report thô: inventory theo dependency group + class; gate results 1 dòng/gate; runtime entry points (G7/G8/G9 ACTIVE) + xử lý; quarantine edits file:dòng; dependency phải giữ; AniSource; verify checklist (agent + user smoke theo đúng entry point ACTIVE tìm được).

## Pre-Move guard

Trước `Move` của mỗi batch (master có thể đã đổi từ khi duyệt): chạy lại `trace_bundle.py`, so G7/G8/G9 ACTIVE với bundle spec. **Khác ⇒ dừng, hỏi**, không tự quyết.
