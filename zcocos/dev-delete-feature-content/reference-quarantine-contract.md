# Reference — Quarantine Contract

Cách chặn code của feature retired chạm vào resource đã xóa. Nguyên tắc: **chặn trước constructor** (resource load trong `ctor` qua `syncAllChild`), **sửa ít nhất**, `ModuleMgr` là điểm rollback duy nhất cho module fully retired.

## 2 fact runtime làm nền (đã verify trong source)

| Cơ chế | Source | Hệ quả |
|---|---|---|
| Packet routing | `src/base/BaseModule.js` — `init()` mới `MODULES.push(this.onGameMessage)` | Module không `init()` ⇒ **không nhận packet nào**, dù server gửi |
| PoolFunction | `src/base/PoolFunction.js` — `doFunc`: `if(!isFunction(poolFunc[fId])) return;` | Key chưa `regFunc` ⇒ `doFunc` **trả `undefined` im lặng**, không throw |

⇒ Với module fully retired, **Layer 1 là đủ và là layer duy nhất bắt buộc**. Nhưng 2 fact này **không** bảo vệ: class retired được code active **kế thừa** (4c), util retired được code active **gọi** (4b), atlas frame dùng chung (G3), JSON được module cha active `syncAllChild` (Layer 3). Trạng thái module không suy ra được an toàn của từng file.

## Layer 1 — ModuleMgr (bắt buộc)

Comment **đủ 4 điểm**: ctor `var x = new XModule()`, `x.init()`, `x.reset()` trong `reset`, `x.reset()` trong `resetReloadConfig` (một số module thiếu điểm cuối → 3 dòng). Dùng script, không sửa tay:

```bash
python .claude/skills/dev-delete-feature-content/scripts/modulemgr_retire.py --init-regions            # 1 lần / repo
python .claude/skills/dev-delete-feature-content/scripts/modulemgr_retire.py --retire <var> <bundle>   # mỗi module
```

Kết quả: dòng ctor **dời** vào `// #region Deleted Content` với marker `//deleted content <build>` (module chưa có tag ⇒ tool tự gắn `//D //<bundle>` trước marker để trace sau nhận ra bundle); init/reset comment tại chỗ trong `// #region Deleted Content` của từng block. Script idempotent, giữ CRLF (đọc/ghi `newline=''`), không đổi thứ tự init/reset của module sống. Diff kỳ vọng cho 1 module: **3+/3− hoặc 4+/4−** tùy G0 (module không có `reset()` trong `resetReloadConfig` ⇒ 3) — ctor bị dời = 1−/1+, mỗi init/reset comment = 1−/1+. Lấy số dòng từ G0, không đoán.

> Không để biến bị comment mà còn `init()`/`reset()` sống ⇒ `undefined is not an object`. Gate: `grep -n "<var>" ModuleMgr.js | grep -v ':\s*//'` phải = 0.

## Guard-Only — giữ register, chặn GUI trong module

Áp dụng khi module tag retired nhưng **code active gọi PoolFunction của nó và dùng return value với default khác `undefined`** (vd `FIRSTCHARGE_TELCO_IS_CHARGED` default `true` ở 22 payment GUI; `FIRST_DEAL_GET_OFFERS` → `.length`). Retire sẽ đổi behavior/crash ở nhiều caller active ⇒ không retire:

```bash
python modulemgr_retire.py --guard-only <var> "<lý do: constant nào, bao nhiêu caller>"
```

Dòng `new` dời vào `// #region Guard-Only`, init/reset giữ vị trí + marker `//guard-only`. Rồi **Layer 3 trong file module đó**: `return;` đầu mọi hàm show GUI / construct GUI riêng của nó (biến thể có callback: gọi `callback()` trước `return` để không kẹt flow). Gate Layer 4 cho guard-only đổi thành: **mọi caller ngoài có handler sống** (module vẫn regFunc).

Hai gate bắt buộc đi kèm:
- **G0 Guard-Only gate** của `trace_bundle.py`: đếm hàm `show*/open*/popup*` trong dir module có `return` đầu body; báo **THIẾU GUARD** ⇒ thêm guard **trong batch của bundle**. Marker `--guard-only` không được hứa "đã guard" khi chưa có (ca thật: `FirstTel`, `FirstDeal` sau `35043ed48` đều 0 guard).
- Code trong dir module Guard-Only là **ACTIVE về runtime** (report gắn kind `GUARD-ONLY(active)`): JSON được `syncAllChild` ở đó là consumer active ⇒ retained, hoặc guard chặn **mọi** đường construct tới nó trong chính module (kể cả đường qua module active khác như `PmModule` → `FirstTelModule.checkChargeAfter3Day`).

## Layer 2 — Return-value guard tại caller (hiếm)

| Kiểu call `doFunc(X_*)` ngoài module | Xử lý |
|---|---|
| Fire-and-forget `doFunc(X_SHOW_ICON)` | **Không sửa** |
| Dùng return value, `undefined` an toàn: `if (doFunc(X_CHECK))` | **Không sửa** |
| Dùng return value, `undefined` crash: `doFunc(X_GET_LIST).length`, `doFunc(X_TIME) - now` | Guard tại caller hoặc cân nhắc Guard-Only |
| **Icon quà server của feature đóng** — `SlotGift.js` (`SlotGiftUtil.getResNameIcon` / `setInfo`) có case `giftInfo.name == "<gift của feature>"` trỏ frame trong atlas của bundle (ca thật: `es_item → es_icon_material.png`, `stickBox5 → gratefull_random_s.png`, `x2BattlePassBall → battle_pass_icon_ball_x2.png`) | Feature đóng ⇒ server không trả gift đó nữa ⇒ **comment case tại caller kèm lý do** (hàm rơi về default `icon_random.png`, không crash) và **xóa atlas** thay vì retain cả atlas cho 1 frame. Rollback = uncomment + Restore. User quyết định 2026-09-09 (`b3083ab97`) |

> Không comment call site "cho sạch". Mỗi dòng sửa thêm là một dòng phải revert khi rollback. Ngoại lệ có chủ đích: case icon quà ở trên (đổi 1 atlas 100–300 KB lấy 3 dòng comment).

> **Trước khi xóa atlas retained:** kiểm **JSON retained trong cùng bundle** có khai báo atlas đó ở field `"Plist"` không (ca thật: `guiThankfulMonth.json` — ThankfulMonth active — dùng `FirstChargeContent.plist` + frame `gratefull_random_s.png` ⇒ atlas FirstCharge **không** xóa được dù SlotGift đã có thể comment). Scan frame "ngoài folder" bỏ sót consumer nằm trong chính folder bundle — `gen_manifest.py` nay refuse khi retained JSON tham chiếu file bị removed.

## Layer 3 — Chặn trong module retired khi code active chạm vào nó

Áp dụng khi: module cha active construct GUI retired; active gọi util retired mà body construct/load (4b); GUI retired được `new` trực tiếp từ màn dùng chung (G8 `new`). Sửa **trong file của module retired**, không sửa caller:

```js
PieceCollectionInRoomUtil.createNodeGuideInHole = function (parent, holeId) {
    if (!PieceCollectionUtil._isEnable) return;          // Layer 3: resource đã xóa (deleted content build180)
    ...
```

Quy tắc: kiểm caller có dùng return value không → trả safe default đúng kiểu (`false`, `null`, `[]`), không trả `undefined` nếu caller `.length`/so sánh. Thứ tự ưu tiên: (1) retain resource (0 dòng code) nếu file nhỏ và consumer active hợp lệ; (2) guard trong module; (3) sửa caller active — chỉ khi 2 cách trên không được.

## Layer 4 — Gate grep sau khi sửa

```bash
grep -rn "PoolFunction[.]<PREFIX>_" src/ | grep -vE "^(<retired dirs>)/" \
  | grep -v CmdDefine.js | grep -v src/base/PoolFunction.js | grep -v ':[[:space:]]*//'
```

- Prefix **phải** kèm `PoolFunction[.]` — `RACE_EVENT_` trần match constant `ITEM_NAME_RACE_EVENT_LIVE`.
- Loại `CmdDefine.js`, `PoolFunction.js` (khai báo), dòng comment. Mọi hit còn lại phải thuộc bảng phân loại Layer 2 và **khớp bản đã duyệt trong bundle spec**. Khác ⇒ dừng, hỏi.

## Layer 4b — Util của module retired được code active gọi (bắt buộc)

Ca thật: `TableImage.createTableImage()` (active) → `PieceCollectionInRoomUtil.createNodeGuideInHole()` → `new PieceCollectionRoomHoleNode()` → JSON đã xóa → TypeError trong `ScreenGame.createScreen` → `ScreenMgr._isIniting` kẹt → **crash mọi lần đổi scene**. `trace_bundle.py` gate G9 liệt kê mọi `X.fn(` với X định nghĩa trong module dir (kể cả object không có `var`), body có construct/load hay không, caller ACTIVE hay không. Construct + ACTIVE ⇒ Layer 3 trong hàm đó. Pure-data ⇒ giữ.

## Layer 4c — Code active KẾ THỪA class retired (bắt buộc)

Ca thật: `minigame/ui/GuiMinigameGetGift.js:4 = Gui7DayGetGift.extend({` không override `ctor` ⇒ ctor cha `syncAllChild("content/sevendaybonus/gui7DayGetGift.json")` ⇒ TypeError khi minigame hiện popup quà. Gate G8 quét **đủ** class retired (mọi `X = <Base>.extend(`, không giới hạn base) cho `= X.extend(` và `new X(` ở code ngoài module. EXTENDS từ ACTIVE ⇒ JSON của ctor cha **retained** (kiểm method kế thừa có dùng frame atlas không — nếu lớp con override method đó thì atlas không cần giữ).

## Lưu ý `ScreenMgr`

`src/base/screen/ScreenMgr.js` `getScreen` set `_isIniting = true` trước `ScreenGame.createScreen`; bản cũ chỉ reset khi thành công ⇒ exception trong ctor bất kỳ screen làm brick đổi scene vĩnh viễn (triệu chứng `viewScreen addChild : wrong number of arguments`). Đã harden bằng `try/finally` ở commit `e08011e99` (branch `build180_update_deletecontent`) — **kiểm trên branch đang làm**: `grep -n finally src/base/screen/ScreenMgr.js`; không có ⇒ mọi exception ctor screen là brick. Dù có hardening, resource mà **ctor screen** có thể đụng (kể cả gián tiếp qua util, vd `TableImage.ctor → createTableImage → InRoomUtil`) vẫn là rủi ro P1, không phải "icon trống".

## Sửa gì / không sửa gì

| File | Sửa khi | Không sửa khi |
|---|---|---|
| `src/gamemgr/ModuleMgr.js` | luôn (Layer 1 / Guard-Only) | — |
| JS của module retired | Layer 3 / Guard-Only cần guard | module fully retired không ai gọi |
| `src/game/loading/logic/ResourceImage.js` | atlas **bị xóa** VÀ dòng `res.<key>` đó thực sự load nó — comment dòng, marker `//deleted content <bundle> <build>` | atlas retained; key không được preload |
| `src/resource.js` (bảng `res`) | **không bao giờ** — là khai báo, JSB preload bỏ qua | — |
| `build/**/cdn.json` | group/path của folder bị xóa (`cdn_prune.py`) | không có ref |
| Caller active | chỉ Layer 2 crash-case | fire-and-forget, `if (doFunc())` |
| Source JS, packet class, CMD constant, config JSON, `project.json` | **không bao giờ** (giữ để mở lại) | — |

## Rollback 1 feature

```powershell
.\.claude\skills\dev-delete-feature-content\scripts\delete_feature_content.ps1 -Action Restore -Bundle <bundle>
git apply -R "<BackupRoot>\<build>\_meta\<bundle>\quarantine.patch"
```

Hoặc tay: copy 2 folder content của bundle từ backup về, uncomment các dòng ModuleMgr của module đó (và bỏ guard Layer 3 nếu có — đều nằm trong patch). **Resource về mà không revert code thì feature vẫn tắt.**
