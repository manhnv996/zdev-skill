---
name: dev-feature
description: "Use when building a new BidaMobile Cocos 2dx JS feature/event through docs-to-code flow, or when modifying existing feature/event runtime code such as UI behavior, cmd/network, util/module wiring, QA, or dev-status tracking."
argument-hint: "[tên-feature hoặc đường dẫn design doc có sẵn]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
model: sonnet
---

# dev-feature — BidaMobile (Cocos 2dx JS)

Workflow 2 phase lớn. **Phase A hoàn thành và được approve trước khi Phase B bắt đầu** khi làm feature/event mới theo docs-to-code flow.

Ngoại lệ: với task sửa code nhỏ trên feature/event đã tồn tại, có thể vào thẳng **Phase B Lightweight Mode**.

---

## Bước 0: Thu thập thông tin ban đầu

**Đọc argument:**
- Có đường dẫn file (`.md`, `.txt`) → đọc design doc có sẵn, normalize/copy nội dung vào `docs/modules/{featureName}/design/{featureName}-design.md`, chạy checkpoint A1 ngắn rồi mới sang A2
- Có tên feature → dùng làm tên gợi ý, đi qua toàn bộ flow
- Không có gì → hỏi tên feature trước

**Hỏi (hoặc gợi ý nếu tên feature đã biết):**

> Cần xác nhận 5 thông tin sau — nếu bạn chưa quyết định, tôi sẽ gợi ý dựa trên tên feature:

1. **Tên feature:**
   - Folder name: `camelCase/lowercase` (e.g. `relichunt`, `rankingSystem`)
   - Class/file prefix: `PascalCase` (e.g. `RelicHunt`, `RankingSystem`)

2. **Đường dẫn src:** Nơi đặt code
   - Gợi ý nếu là **event** (giới hạn thời gian): `src/game/event/{featureName}/`
   - Gợi ý nếu là **feature thường**: `src/game/{featureName}/`
   - User có thể sửa lại tùy ý

3. **Danh sách UI files sơ bộ:**
   - `{Prefix}MainGui.js` — thường có nếu feature có màn chính
   - `{Prefix}LobbyIcon.js` — thường có với event/feature có entry ở lobby
   - Danh sách UI đầy đủ sẽ được chốt ở Step A2 sau khi đọc design/spec và resource `.json`

4. **Docs path:** `docs/modules/{featureName}/` ← cố định, không hỏi lại

5. **Resource path:** Nơi đặt file `.json` UI (tạo bằng Cocos Studio)
   - Gợi ý: `res/content/{featureName}/`
   - User có thể sửa lại nếu dự án dùng path khác

Gợi ý tất cả 5 mục, cho user confirm hoặc sửa. **Không tự quyết định một mình.**

---

# PHASE A — TẠO DOCS

> Mỗi step tạo ra 1 file. User review + confirm xong mới sang step tiếp theo.

---

## Step A1: Làm rõ Requirements → Design Doc

> **Mục tiêu:** Hiểu đủ để viết design doc — không code, không spec kỹ thuật.

**→ Dùng `/grill-me`** nếu requirements còn mơ hồ.

Nếu argument là design doc có sẵn: dùng nội dung đó làm source, chuẩn hóa vào template design doc canonical ở `docs/modules/{featureName}/design/{featureName}-design.md`. Không skip file design trong docs path, vì spec/plan sẽ reference path này.

Hỏi cho đến khi trả lời được:
- Tính năng làm gì? Player tương tác thế nào?
- Entry point: lobby icon / auto popup / từ menu nào?
- Flow màn hình chính (vào → làm gì → ra sao)?
- Điều kiện hiển thị (luôn hiện / event time / level / server flag)?
- Data từ server: load info gì, action gì, server có push không?
- Có config JSON không? Có tutorial không?
- MVP là gì, scope v1 gồm những gì?

**Tạo file:** `docs/modules/{featureName}/design/{featureName}-design.md`

> **Bắt buộc đọc reference:** `reference-doc-templates.md` → section `Design Doc Template`. Dùng template đó để tạo file trên, điền theo requirements đã làm rõ; không giữ placeholder nếu đã có dữ liệu thật.

**→ Checkpoint A1:** Trình bày design doc cho user review.
Hỏi: "Design doc này đã đúng ý chưa? Cần chỉnh gì trước khi tôi làm spec kỹ thuật?"
**Chờ user confirm xong mới sang A2.**

---

## Step A2: Technical Specification

> **Mục tiêu:** Định nghĩa rõ **cây file**, **API từng file**, **network protocol**, **wiring** — đủ để code mà không cần đoán.

**→ Dùng `/architecture-decision`** nếu có quyết định kỹ thuật cần ghi lại ADR.

### Xác định danh sách file trước khi viết spec

Dựa trên design doc đã approve ở A1, hỏi và quyết định chính xác từng file:

**Logic files** — hỏi từng cái:
- `{Prefix}Model.js` cần không? → Có nếu server trả dữ liệu dạng list object (map cells, item list...) cần typed class để parse
- `{Prefix}JSONConfig.js` cần không? (tên file cố định; class bên trong đặt theo mục đích, vd `{Prefix}{Purpose}JSONConfig`) → Có nếu feature đọc file `.json` config (balance, cost, reward table...) — nếu có, **toàn bộ việc tạo file này sẽ dùng `/dev-config`**, không xử lý inline trong skill này
- `{Prefix}Animate.js` cần không? → Có nếu animation/effect sequence đủ phức tạp để tách khỏi Util
- `{Prefix}Tutorial.js` cần không? → Có nếu design doc yêu cầu tutorial flow

**UI files** — yêu cầu user cung cấp một trong hai:
- **Resource UI path** (e.g. `res/content/{featureName}/`) → agent glob `.json` files, derive danh sách JS file tương ứng
- **Danh sách UI files** dự kiến → agent dùng trực tiếp

Từ danh sách đó, agent làm rõ với user:
1. Với mỗi `.json` / file GUI → xác nhận tên JS file và loại (`extends BaseScreen` / `ccui.Layout` / ...)
2. Nếu tên gợi ý là Slot (e.g. `*Slot.json`) → hỏi: có cần file Table không? Nếu có, Pattern A (1 item/hàng) hay Pattern B (N items/hàng, cần thêm TableRow)?
3. Có file JS nào không có `.json` tương ứng chưa có trong danh sách không (vd popup chưa design xong)?

Chỉ hỏi những gì còn chưa rõ — tóm tắt lại để user confirm trước khi sang bước tiếp.

Sau khi user confirm → **danh sách file đã cố định**. Trước khi viết spec, làm rõ network protocol.

### Làm rõ Network Protocol (nếu có cmd/)

**Đọc prompt/argument trước:** Nếu user đã cung cấp thông tin (CMD list, fields, error codes, CMD ID) → tóm tắt lại để confirm, chỉ hỏi thêm phần còn thiếu hoặc chưa rõ.

Nếu chưa đủ thông tin → từ **flow màn hình** và **detailed rules** trong design doc, derive và hỏi:

**Bước 1 — Gợi ý CMD list:**
Liệt kê các action có khả năng cần gói tin, vd:
```
Tôi thấy design doc có các action sau — mỗi action cần 1 cặp Send/Receive:
1. Load thông tin ban đầu   → {FEATURE}_LOAD_INFO
2. [Action A]               → {FEATURE}_{ACTION_A}
3. [Action B]               → {FEATURE}_{ACTION_B}

Danh sách này đúng chưa? Có action nào server push mà không cần client gửi trước không?
```

**Bước 2 — Với mỗi CMD, hỏi:**
```
CMD: {FEATURE}_{ACTION}

SendPacket — client gửi lên:
  Params: [gợi ý từ design, vd: itemId, quantity] — đúng chưa?

ReceivePacket — server trả về:
  Fields: [user cung cấp hoặc hỏi server team]
  Error codes cần xử lý: SUCCESS + [các lỗi đặc thù của action này]

CMD ID: [hỏi server team — để trống nếu chưa có]
```

> Nếu user chưa có CMD ID hoặc field list từ server → ghi `[TBD — hỏi server]` vào spec, đánh task tương ứng là blocked.

**Chờ user confirm xong protocol → mới viết template.**

---

### Gợi ý Methods cho từng class

Sau khi đã confirm danh sách file + network protocol, đọc lại design doc và với mỗi class đã confirm — suy luận từ design những gì class đó cần làm, rồi đề xuất danh sách methods tương ứng.

Trình bày gợi ý theo từng class, hỏi user: "Danh sách methods này đúng chưa? Cần bỏ, sửa tên, hay thêm method nào không?"

**Chờ user confirm xong → mới viết spec template.**

---

> **File chờ external input** (vd `{Prefix}JSONConfig.js` mà format do server/designer cung cấp): vẫn đưa vào spec và folder structure. Spec mô tả đủ mục đích file + các field/giá trị mà feature cần đọc từ config (dù format file thật chưa biết). Trong section JSONConfig của spec ghi thêm `> format TBD — chờ [ai cung cấp]`. Trong plan đánh task này là blocked. Khi implement: Util hardcode tạm các giá trị đó với đúng tên field đã spec — khi nhận được file config thật thì implement `readConfig()` và thay hardcode bằng config values.

**Tạo file:** `docs/modules/{featureName}/spec/{featureName}-spec.md`

> **Bắt buộc đọc reference:** `reference-spec-template.md` → section `Technical Specification Template`. Dùng template đó để viết spec sau khi đã confirm danh sách file, network protocol và methods. Giữ nguyên rule template có điều kiện: thay row ví dụ bằng dữ liệu thật, không copy placeholder máy móc.

**→ Checkpoint A2:** Trình bày spec cho user review.
Hỏi: "Spec kỹ thuật đúng chưa? Đặc biệt phần network protocol, Util state, và wiring?"
**Chờ user confirm xong mới sang A3.**

---

## Step A3: Khởi tạo Dev Status

> **Mục tiêu:** Tạo file tracking tiến độ ngay từ đầu — hoàn toàn tách biệt với spec kỹ thuật. File này sẽ được cập nhật liên tục trong Phase B.

**Tạo file:** `docs/modules/{featureName}/dev-status.md`
*(Nằm ở root module, không phải trong spec/ — vì đây là tracking, không phải spec)*

> **Bắt buộc đọc reference:** `reference-doc-templates.md` → section `Dev Status Template`. Chỉ liệt kê file đã có trong spec; không copy row ví dụ nếu spec không có file tương ứng.

---

## Step A4: Implementation Plan

> **Mục tiêu:** Chia nhỏ thành tasks có thứ tự rõ ràng, ước lượng effort.

**→ Dùng `/scope-check`** nếu cần đánh giá độ phức tạp trước khi ước lượng.

**Tạo file:** `docs/modules/{featureName}/plans/{YYYY-MM-DD}-{featureName}-plan.md`
*(date = ngày hôm nay)*

> **Bắt buộc đọc reference:** `reference-doc-templates.md` → section `Implementation Plan Template`. Sinh task từ spec đã approve; task ví dụ như Lobby Icon / Network Layer / Optional chỉ giữ nếu spec có phần tương ứng.

**→ Checkpoint A4:** Trình bày plan cho user review.
Hỏi: "Plan này hợp lý chưa? Có task nào thiếu hoặc ước lượng chưa đúng không?"

**Sau khi user confirm plan → Phase A hoàn thành. Hỏi:**
> "Docs đã đầy đủ. Bắt đầu Phase B (code) luôn không, hay dừng lại ở đây?"

---

# PHASE B — CODE

> Chỉ bắt đầu khi Phase A được approve hoàn toàn.

**Thứ tự thực hiện: đọc plan doc và follow đúng task order đã định nghĩa ở đó.** Phase B dưới đây cung cấp verify criteria cho từng loại task — không phải thứ tự cứng.

## Phase B Lightweight Mode — Existing Feature Code Task

Dùng mode này khi user yêu cầu sửa logic/code của feature/event đã tồn tại nhưng task không thuộc một plan/dev-status Phase A của skill này.

Áp dụng cho:
- UI runtime behavior trong GUI/Table/Slot, kể cả logic render, layout, progress, reload lifecycle
- Helper tính toán, state, cache, reset, lifecycle trong Util/Model/Module
- Cmd/network/action wiring trên module có sẵn
- Refactor nhỏ có thay đổi behavior

Không bắt buộc tạo/tick plan doc hoặc cập nhật `dev-status.md` nếu task không thuộc docs flow. Vẫn phải:
1. Đọc file liên quan và pattern gần nhất trước khi sửa.
2. Xác định task gần nhất với nhóm verify nào: UI Files / Logic Layer / Network Layer / Actions.
3. Chạy Agent Verify tương ứng ở mức phù hợp với phạm vi sửa.
4. Ghi rõ phần chưa verify runtime trong kết quả.

## Phase B Execution Guard

Khi bắt đầu Phase B hoặc sau compact/resume:
1. Đọc lại section `PHASE B — CODE` trong skill này.
2. Đọc plan doc đủ để xác định task unchecked đầu tiên hoặc task user yêu cầu làm tiếp.
3. Đọc `dev-status.md` đủ để biết trạng thái file/task liên quan.
4. Đọc verify criteria tương ứng với loại task sắp làm.

Trước mỗi task tiếp theo trong cùng session:
- Ưu tiên dùng context hiện có nếu còn rõ task/verify criteria.
- Tối thiểu phải nắm được: task hiện tại trong plan, trạng thái liên quan trong `dev-status.md`, và verify criteria tương ứng.
- Nếu bất kỳ phần nào không còn rõ, đọc lại đúng phần liên quan trước khi code hoặc verify.
- Có thể đọc thêm plan/status/spec/skill khi cần để tránh đoán.

Nếu sau compact/resume không chắc task trước đã verify chưa:
- Chạy lại verify tương ứng cho task đó trước khi làm tiếp.

Sau mỗi task trong plan (cần hoàn tất checklist này trước khi chuyển sang task tiếp theo):
1. Tick checkbox trong plan doc
2. Cập nhật `dev-status.md`
3. Chạy **Agent Verify** (tự check bằng Read/Grep)
4. Ghi note những gì cần **User Verify** (runtime — agent không tự check được)

---

## Localization Draft Handoff

Áp dụng tự động khi đang làm Phase B theo docs flow và task phát sinh localization key mới, thay đổi text của key đang được tracking, hoặc reuse key có sẵn cần ghi nhận dependency. Với **Phase B Lightweight Mode**, chỉ áp dụng nếu user đã cung cấp `dev-status.md` hoặc task đang thuộc một docs flow có sẵn.

### Trigger

Thực hiện handoff ngay trong task hiện tại khi có một trong các dấu hiệu:

- Thêm `fr.Localization.text("new_key")` cho user-facing text chưa có key phù hợp.
- Design/UI bổ sung user-facing text cần key mới.
- Requirement mới thay đổi text VI của một key đang được tracking.
- Reuse một localization key có sẵn và cần ghi nhận dependency của feature bằng row `N/A`.

Không trigger handoff cho:

- Node chỉ hiển thị giá, progress, level, số lượng hoặc dữ liệu runtime thô mà không có surrounding copy mới. Localized template mới chứa placeholder như `@num@` vẫn phải handoff.
- Raw text do server/config trả về mà client không sở hữu localization copy.
- Debug text, log, internal identifier hoặc placeholder art không hiển thị cho user.
- Key localization đã được tracking và task chỉ thêm text tạm vào `lang_vi.json` để test.
- Chỗ dùng key hiện có không thay đổi key, text VI hoặc dependency cần tracking.

Trước khi tạo key mới, kiểm tra các key hiện có trong localization/code toàn project để reuse nếu cùng semantics. Không tạo key mới chỉ để đổi cách đặt tên.

**Reuse check phải làm theo nội dung, không theo tên key.** Grep tên key dự kiến trong `src/` luôn ra "chưa tồn tại" vì đó là tên mình vừa đặt — vô nghĩa. Phải đọc `res/localize/lang_vi.json` (nhánh `text`) và tìm entry có **nghĩa tương đương**. Các nhóm hay lặp lại giữa feature: tên chế độ chơi/kênh, nhãn trạng thái ngắn (thắng/thua/bỏ qua/sẵn sàng/nhận), câu thông báo chung (sự kiện kết thúc, lỗi chung, chạm để nhận), mô tả khoảng thời gian.

Khi reuse, đọc text thật của key để biết **placeholder và color tag có sẵn** rồi sửa code cho khớp — không tự đặt placeholder mới.

### Handoff contract

Bắt buộc áp dụng `/dev-languagetool` với operation phase `status-draft` và truyền đủ payload tương đương:

```yaml
phase: status-draft
devStatusPath: docs/modules/{featureName}/dev-status.md
entries:
  - key: prefix_semantic_name
    vi: Nội dung tiếng Việt đề xuất
    note: GuiName.nodeName; mục đích hiển thị
    reuseExisting: false
```

Với key có sẵn được reuse, truyền `reuseExisting: true` sau khi đã verify key trong localization/code hiện có; `status-draft` sẽ dùng `Excel = N/A` thay vì `⬜`.

Quy tắc orchestration:

1. Key mới phải theo prefix đã chốt trong spec/dev-status; key có sẵn được reuse giữ nguyên tên gốc.
2. Khi requirement/design đã cung cấp đủ key hoặc có thể derive key rõ ràng theo convention, tự thực hiện handoff; **không dừng hỏi user có muốn thêm key vào `dev-status.md` hay không**.
3. Chỉ hỏi khi chính nội dung player-facing hoặc semantics của key còn mơ hồ và việc tự chọn có thể làm sai behavior.
4. Sau khi `status-draft` update và verify bảng thành công, tiếp tục task `dev-feature`; không chuyển sang `excel-commit`.
5. `status-draft` tự ghi text của **key mới** vào `res/localize/lang_vi.json` để feature test được runtime ngay — **mặc định làm, không cần user nhắc**. Key reuse không đụng tới. Đây là text tạm; nguồn sự thật vẫn là Excel ở phase `excel-commit`.
6. Handoff là single writer cho các row Localization trong task: `dev-feature` không tự sửa cùng row Localization ngoài handoff, nhưng vẫn cập nhật các section khác của `dev-status.md` theo flow bình thường.
7. Nếu `status-draft` report schema conflict, không tự tạo bảng/row thay thế; ghi nhận gap và tiếp tục phần implementation không phụ thuộc docs mutation.

### Agent Verify

- [ ] Mọi localization key mới được dùng trong code đều có row tương ứng trong `dev-status.md`
- [ ] **Đã reuse check theo nội dung trên `lang_vi.json`**, không chỉ grep tên key trong `src/`
- [ ] Không có key trùng semantics với key đã tồn tại trong localization/code toàn project
- [ ] Key reuse đã thay trong code; placeholder/color tag trong code khớp text thật của key đó
- [ ] Bảng chia 2 section: key reuse (`N/A`) ở trên, key mới (`⬜`) ở dưới
- [ ] Mọi key mới đã có text trong `res/localize/lang_vi.json` → chạy được runtime ngay
- [ ] Mọi `fr.Localization.text("...")` trong code feature đều tra ra text trong `lang_vi.json`
- [ ] Thay đổi ghi chú/nơi sử dụng không làm `✅` bị đổi về `⬜`
- [ ] Text động/server/debug không bị thêm nhầm vào bảng Localization
- [ ] Handoff không đọc/ghi Excel; chỉ được thêm key mới vào `lang_vi.json`, không sửa `lang_*.json` khác

---

## Verify: Scaffold & Constants

**Agent tự check:**
- [ ] Tất cả file trong spec tồn tại trên disk
- [ ] Đọc `project.json` → tất cả file mới từ spec có trong `jsList` đúng 1 lần
- [ ] Grep `PoolFunction.{FEATURE}_*` → có đủ constants theo spec trong file PoolFunction defs
- [ ] Grep `EXCHANGE.CMD.{FEATURE}_*` → có đủ constants theo spec trong file CMD defs
- [ ] Các file JS mới có `// #region` / `// #endregion` cho những nhóm logic rõ ràng

**User phải test:**
- Load game → không crash, không có undefined constant

---

## Verify: Logic Layer

**Agent tự check:**
- [ ] Đọc `{FeatureName}Util.js` → có đủ state vars với đúng default values như spec
- [ ] `reset()` tồn tại, reset tất cả state vars về default
- [ ] Đọc `Module.reset()` → gọi `{FeatureName}Util.reset()`
- [ ] Nếu có Model: fields đúng kiểu và default theo spec
- [ ] Nếu có JSONConfig: `/dev-config` đã chạy xong, file tồn tại, đã đăng ký ConfigMgr + project.json
- [ ] *(nên)* Hằng trong Util gom nhóm theo chủ đề, identifier tiếng Anh toàn phần
- [ ] **Thời gian theo server**: `rg "Date\.now|new Date\(\)|\.getDate\(|\.getHours\(|\.getMonth\(|\.setHours\(" {featureDir}` — mỗi chỗ trúng phải lấy "bây giờ" từ `PoolFunction.SERVER_TIME` hoặc đổi ngày/giờ qua helper Utility (xem reference-ui-patterns.md → *Thời gian — luôn theo SERVER*)

> **Soft rule — gom nhóm hằng trong Util.** Không chặn task, nhưng nên làm ngay từ đầu vì đổi tên hằng sau đó
> phải sửa cả code lẫn spec/dev-status.
> - Từ 2–3 hằng cùng chủ đề trở lên → gom vào một object theo convention `BattlePassCustomUtil`:
> `XUtil.JAR = {};` rồi `XUtil.JAR.MAX_DELTA = ...`, thay vì để phẳng với prefix lặp `XUtil.JAR_MAX_DELTA`.
> Scalar đứng một mình (`XUtil.EVENT_NAME`) giữ phẳng.
> - Hằng chỉ dùng nội bộ cũng gom vào nhóm, không để `_PREFIX_NAME` lẻ nằm giữa các region khác.
> - Identifier dùng **tiếng Anh toàn phần**. Tên riêng tiếng Việt trong design (Bảng Phượng, Bảng Long...)
> chỉ xuất hiện ở comment và localization key — không đưa vào tên hằng.
> - Không mass-refactor hằng của feature cũ chỉ để đổi style; chỉ áp dụng cho code mới hoặc block đang sửa.

**User phải test:** *(không có — logic layer không cần runtime)*

---

## Verify: Network Layer

**Agent tự check:**
- [ ] Đọc `{FeatureName}SendPacket.js` → có đủ class `CmdSend*` theo spec, đúng EXCHANGE.CMD
- [ ] Đọc `{FeatureName}ReceivePacket.js` → có đủ class `CmdReceive*`, fields đúng theo spec
- [ ] Đọc `Module.onGameMessage()` → mỗi CMD case có đúng 3 bước: `new CmdReceive* → readData() → Logger.trace → handler`
- [ ] Mỗi `cmdReceive*()` có `switch(cmd.getError())` với ít nhất `SUCCESS` và `default` case
- [ ] Với mỗi `send*()`, quyết định disable screen theo UX intent, không chỉ theo tên CMD
- [ ] Auto load / background sync / polling: không gọi `SHOW_DISABLE_SCREEN` dù CMD có thể tên `LOAD_INFO`
- [ ] User-triggered blocking flow cần chờ response để tiếp tục: gọi `SHOW_DISABLE_SCREEN` trước packet và handler tương ứng gọi `HIDE_DISABLE_SCREEN` trước switch, kể cả CMD được đặt tên `LOAD_INFO`
- [ ] Đọc `src/gamemgr/ModuleMgr.js` → có `new {FeatureName}Module()`, `.init()` trong `init`, `.reset()` trong cả `reset` và `resetReloadConfig`

**User phải test:**
- Gọi SEND_LOAD_INFO → Logger.trace xuất console → Util state update đúng

---

## Verify: UI Files (áp dụng cho từng file GUI)

> **Trước khi code UI:** đọc [reference-ui-patterns.md](reference-ui-patterns.md) (showGui/hideGui, Countdown, Button Listener, **Màu chữ trong button**, Localization, Purchase Price, Utility, **Thời gian theo server**, Send packet) và [reference-tableview-patterns.md](reference-tableview-patterns.md) (nếu có danh sách/bảng).

**Agent tự check:**
- [ ] Đọc section tương ứng trong spec (`## ui/ → ### {FileName}`) → từng method được liệt kê trong spec tồn tại trong file
- [ ] Nếu file `extends BaseScreen`: có `syncAllChild(...)` trong `ctor`, path khớp `{resPath}` đã confirm
- [ ] Nếu file là Table Node (`extends ccui.Layout`): có đủ 4 delegate methods theo pattern trong spec
- [ ] Đọc Module → các method show/hide/get GUI tương ứng tồn tại, logic guard và lazy init đúng như spec mô tả
- [ ] Mọi node text trong `btn_*` có texture `common_btn_*` **và** chưa set màu/viền trong `.json` → đã gọi đúng `Utility.setTextBtn*` một lần trong `ctor` (xem reference-ui-patterns.md)
- [ ] Mọi ngày/giờ hiển thị đi qua helper Utility (`millisToDateTime`, `millToDateHourMinute`...), không tự format bằng `new Date(ms).getDate()`; ngày **kết thúc** lùi 1ms (mốc đóng)

**User phải test:**
- Show/hide đúng luồng, data hiển thị đúng, không crash khi mở/đóng nhanh

---

## Verify: Actions (áp dụng cho từng action)

**Agent tự check:**
- [ ] GUI có button → gọi `PoolFunction.doFunc(PoolFunction.{FEATURE}_SEND_{ACTION})`
- [ ] Module `send{Action}()` gọi `SHOW_DISABLE_SCREEN` trước packet
- [ ] `onGameMessage` có case cho CMD này với đúng 3 bước
- [ ] Handler có case `SUCCESS`, `EXPIRE_TIME`, `NOT_ENOUGH_ITEM`, `default` (theo spec)
- [ ] `EXPIRE_TIME` handler hide cả icon lẫn GUI
- [ ] `default` handler show message với error code

**User phải test:**
- Từng error case với server thật hoặc cheat tool

---

## Verify: Optional Files

**`{FeatureName}Animate.js` — Agent tự check:**
- [ ] `doPlay()` tồn tại
- [ ] Được gọi từ `cmdReceive{Action}()` SUCCESS *sau* khi update data/Util

**`{FeatureName}Tutorial.js` — Agent tự check:**
- [ ] `reset()` tồn tại, được gọi trong `Module.reset()`
- [ ] State flags (`_isHasTutorial`, `_isRunning`...) đúng theo spec

**User phải test:** runtime behavior của animation và tutorial flow

---

## Step B-QA: Final Verification

1. Đọc từng Acceptance Criteria trong `design.md` → agent check từng cái có trong code chưa
2. `/smoke-check` — happy path
3. `/qa-plan` — edge cases
4. `/code-review` — trước merge
5. `/perf-profile` — nếu có animation nặng hoặc nhiều node đồng thời
6. Update `dev-status.md`: các file/task implementation đã hoàn tất → ✅ Done, ghi commit/PR; các row Localization được phép giữ `Excel = ⬜` trong lúc chờ user confirm text
7. Nếu feature/event có GUI hoặc flow cố định cần client tracking → dùng `/dev-tracking` để confirm group/feature/action map rồi implement tracking
8. Nếu `dev-status.md` có `Localization Keys` còn `Excel = ⬜` → report danh sách đang chờ; chỉ dùng `/dev-languagetool` phase `excel-commit` sau khi user đã xác nhận text qua test và đồng ý cập nhật Excel. Không tự commit Excel như side effect của B-QA chung.
9. `/changelog` — sau merge

---

## Quick Reference: Skills theo Phase

| Bước | Skill | Khi nào |
|------|-------|---------|
| A1 | `/grill-me` | Requirements còn mơ hồ |
| A1 | `/quick-design` | Design doc nhanh |
| A1 | `/ux-design` | Thiết kế UI chi tiết |
| A2 | `/architecture-decision` | Quyết định kỹ thuật → ghi ADR |
| A4 | `/scope-check` | Đánh giá trước ước lượng |
| B1–B7 | `/zoom-out` | Cần hiểu module/file lạ trước khi code |
| B1–B7 | `/diagnose` | Bug không rõ nguyên nhân |
| B1–B7 | `/dev-languagetool` (`status-draft`) | Tự tracking localization key/text phát sinh, thay đổi hoặc reuse vào `dev-status.md`, không đụng Excel |
| B-QA | `/smoke-check` | Verify happy path acceptance criteria |
| B-QA | `/qa-plan` | Sinh test cases edge cases |
| B-QA | `/code-review` | Review trước merge |
| B-QA | `/perf-profile` | Animation nặng hoặc nhiều node |
| Done | `/dev-tracking` | Thêm client tracking cho GUI/flow cố định nếu feature/event cần log |
| Done | `/dev-languagetool` (`excel-commit`) | Sau khi user confirm text, thêm/update các key `Excel = ⬜` vào Excel |
| Done | `/changelog` | Ghi lại sau merge |

