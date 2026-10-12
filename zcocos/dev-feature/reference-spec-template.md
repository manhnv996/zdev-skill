# Reference — Spec Template

Template dùng trong Step A2 của `dev-feature`.

Main `SKILL.md` giữ flow hỏi user, confirm file list, protocol, methods và checkpoint. File này chỉ chứa template technical spec dài.

---

## Technical Specification Template

Dùng sau khi user đã confirm danh sách file, network protocol và methods ở Step A2.

**Tạo file:** `docs/modules/{featureName}/spec/{featureName}-spec.md`

> **Cách dùng template:** Template dưới đây là khung có điều kiện. Khi điền spec, thay toàn bộ row ví dụ bằng dữ liệu thật đã derive từ design và/hoặc confirm ở A2; không giữ nguyên placeholder/ví dụ file/action/dependency nếu feature không dùng. Với event feature, các state/cmd phổ biến như `isEndEvent`, `startTime/endTime`, `SEND_LOAD_INFO`, `LobbyIcon` thường hợp lý; với feature thường thì derive theo flow thật thay vì copy mặc định.

~~~~markdown
---
status: draft | approved
date: YYYY-MM-DD
design-ref: docs/modules/{featureName}/design/{featureName}-design.md
---

# {FeatureName} — Technical Specification

## Folder Structure

```
{srcPath}/
├── {FeatureName}Module.js
├── cmd/
│   ├── {FeatureName}SendPacket.js
│   └── {FeatureName}ReceivePacket.js
├── logic/
│   ├── {FeatureName}Util.js
│   └── ...
└── ui/
    ├── {FeatureName}MainGui.js
    ├── {FeatureName}LobbyIcon.js
    └── ...
```

> Điền đúng các file đã confirm vào `...`. Không thêm file chưa confirm, không để lại comment hay marker.

---

## Naming Conventions

| Loại | Pattern | extends | .json? | Folder |
|------|---------|---------|--------|--------|
| Module | `{Prefix}Module` | `BaseModule` | Không | root |
| Util | `{Prefix}Util` — `= {}` | *(plain object)* | Không | `logic/` |
| Model | `{Prefix}{Name}Model` | `cc.Class` | Không | `logic/` |
| JSONConfig | `{Prefix}JSONConfig.js` (file); class: `{Prefix}JSONConfig` hoặc `{Prefix}{Purpose}JSONConfig` | `BaseJSONConfig` | Không | `logic/` |
| Animate | `{Prefix}Animate` — `= {}` | *(plain object)* | Không | `logic/` |
| Tutorial | `{Prefix}Tutorial` — `= {}` | *(plain object)* | Không | `logic/` |
| SendPacket | `CmdSend{Prefix}{Action}` | `fr.OutPacket` | Không | `cmd/` |
| ReceivePacket | `CmdReceive{Prefix}{Action}` | `fr.InPacket` | Không | `cmd/` |
| GUI / Slot | `{Prefix}MainGui`, `{Prefix}[x]Slot`... | `BaseScreen` | **Có** (`syncAllChild`) | `ui/` |
| Table Row | `TableRow{Prefix}[x]Slot` | `TableRowSlot` | Không | `ui/` |
| Table Node | `Table{Prefix}[x]` / `{Prefix}[x]Table` | `ccui.Layout` | Không | `ui/` |

---

## {FeatureName}Module.js

`extends BaseModule` — Điều phối toàn bộ feature: giữ GUI refs, đăng ký PoolFunction, xử lý gói tin server.

### GUI Properties
| Property | Class | Mô tả |
|----------|-------|-------|
| `_{prefix}MainGui` | `{FeatureName}MainGui` | Màn hình chính |
| `_{prefix}LobbyIcon` | `{FeatureName}LobbyIcon` | Icon lobby |
| `_{prefix}PopupGui` | `{FeatureName}PopupGui` | Popup |

### PoolFunction Registrations (init)
| PoolFunction | Gọi method | Mô tả |
|-------------|-----------|-------|
| `{FEATURE}_SHOW_MAIN_GUI` | `show{Prefix}MainGui()` | |
| `{FEATURE}_HIDE_MAIN_GUI` | `hide{Prefix}MainGui()` | |
| `{FEATURE}_SHOW_LOBBY_ICON` | `show{Prefix}LobbyIcon()` | |
| `{FEATURE}_HIDE_LOBBY_ICON` | `hide{Prefix}LobbyIcon()` | |
| `{FEATURE}_SEND_LOAD_INFO` | `send{Prefix}LoadInfo()` | |
| `{FEATURE}_SEND_{ACTION}` | `send{Prefix}{Action}(params)` | |

### onGameMessage — CMD Handlers

Mỗi `case` trong switch theo đúng pattern 3 bước:

```js
case EXCHANGE.CMD.{FEATURE}_{ACTION}:
    cmd = new CmdReceive{Prefix}{Action}(packet);
    cmd.readData();
    Logger.trace("EXCHANGE.{FEATURE}_{ACTION}", JSON.stringify(cmd));
    this.cmdReceive{Prefix}{Action}(cmd);
    break;
```

| EXCHANGE.CMD | ReceivePacket class | Handler method |
|-------------|---------------------|----------------|
| `{FEATURE}_LOAD_INFO` | `CmdReceive{Prefix}LoadInfo` | `cmdReceive{Prefix}LoadInfo(cmd)` |
| `{FEATURE}_{ACTION}` | `CmdReceive{Prefix}{Action}` | `cmdReceive{Prefix}{Action}(cmd)` |

### Handler Methods — Error Handling

Mỗi handler là `switch (cmd.getError())`. **Thêm 1 section `####` cho mỗi CMD handler trong feature** (không chỉ 2 ví dụ dưới đây):

#### cmdReceive{Prefix}LoadInfo
| ErrorDefine | Xử lý |
|-------------|-------|
| `SUCCESS` | Update Util state (isEndEvent, startTime, endTime, ...); nếu !isEndEvent → showLobbyIcon, push popup vào queue; nếu isEndEvent → hideLobbyIcon, hidePopup |
| `default` | *(bỏ qua)* |

#### cmdReceive{Prefix}{Action} *(action có DISABLE_SCREEN)*
> Gọi `PoolFunction.doFunc(PoolFunction.HIDE_DISABLE_SCREEN)` ngay đầu hàm, trước switch.

| ErrorDefine | Xử lý |
|-------------|-------|
| `SUCCESS` | Update Util/Map data; gọi GUI update method nếu GUI đang hiển thị |
| `EXPIRE_TIME` | `SHOW_MESSAGE_BOX "globale_event_end_text"`, callback → hideLobbyIcon + hideMainGui |
| `NOT_ENOUGH_ITEM` | `SHOW_MESSAGE_BOX [message text]` |
| `default` | `SHOW_MESSAGE_BOX "club_notify_err_normal" + "(" + cmd.getError() + ")"` |

---

## cmd/

### {FeatureName}SendPacket.js

Mỗi lệnh gửi lên server là 1 class `extends fr.OutPacket`.

| Class | EXCHANGE.CMD | Params (fields) | Gửi khi |
|-------|-------------|----------------|---------|
| `CmdSend{Prefix}LoadInfo` | `{FEATURE}_LOAD_INFO` | *(không có)* | Module.send{Prefix}LoadInfo() |
| `CmdSend{Prefix}{Action}` | `{FEATURE}_{ACTION}` | `x: Number, y: Number` | Module.send{Prefix}{Action}() |

### {FeatureName}ReceivePacket.js

Mỗi response từ server là 1 class `extends fr.InPacket`.

| Class | EXCHANGE.CMD | Fields (tên: kiểu) | Xử lý tại |
|-------|-------------|-------------------|-----------|
| `CmdReceive{Prefix}LoadInfo` | `{FEATURE}_LOAD_INFO` | `isEndEvent: Boolean, startTime: String, [...]` | `Module.cmdReceive{Prefix}LoadInfo()` |
| `CmdReceive{Prefix}{Action}` | `{FEATURE}_{ACTION}` | `giftList: Array, [...]` | `Module.cmdReceive{Prefix}{Action}()` |

**Error codes cần xử lý:**

| ErrorDefine | Xử lý |
|-------------|-------|
| `SUCCESS` | [logic chính] |
| `EXPIRE_TIME` | Show message hết event, hide GUI + icon |
| `NOT_ENOUGH_ITEM` | Show message thiếu item |
| `[other]` | [xử lý] |

---

## logic/

> **Comment regions — áp dụng cho mọi file JS:** Mọi file JS có từ 2-3 nhóm logic rõ ràng đều phải dùng `// #region <Tên>` / `// #endregion`: Module, Util, Model, JSONConfig, Animate, Tutorial, GUI, Layer, Slot, Table. Tên region nên mirror section trong spec hoặc mục đích code thật (`Init / Reset`, `Show / Hide GUI`, `Send`, `onGameMessage`, `CMD Handlers`, `Localize`, `Touch`, ...).

### {FeatureName}Util.js

Plain JS object (`= {}`). Nguồn sự thật duy nhất về state của feature trong runtime.

> **Comment regions:** Nhóm các hàm/biến theo mục đích bằng `// #region <Tên>` / `// #endregion`. Tên region = tên section trong spec (Constants, State Variables, Reset/Setup, Event Time, Popup...). Spec liệt kê các section — code mirror y chang bằng region tương ứng.

#### State Variables
| Tên | Kiểu | Default | Nguồn | Mô tả |
|-----|------|---------|-------|-------|
| `isEndEvent` | Boolean | `true` | Server LOAD_INFO | Feature đang active hay đã kết thúc |
| `startTime` | String | `""` | Server | Thời điểm bắt đầu |
| `endTime` | String | `""` | Server | Thời điểm kết thúc |
| `[stateVar]` | [type] | [default] | [Server/Config] | [mô tả] |

#### Constants
| Tên | Giá trị | Dùng để |
|-----|---------|---------|
| `EVENT_NAME` | `"{feature_name}"` | Identify feature với OfferSystem |
| `[CONST_NAME]` | `[value]` | [mô tả] |

> **Gom nhóm hằng (soft rule):** từ 2–3 hằng cùng chủ đề trở lên thì ghi luôn dạng `GROUP.KEY`
> (`JAR.MAX_DELTA`, `SHIELD.ICON_TAG`) thay vì phẳng với prefix lặp (`JAR_MAX_DELTA`); scalar đứng một mình
> giữ phẳng. Identifier tiếng Anh toàn phần — tên riêng tiếng Việt của design chỉ nằm ở cột `Dùng để`
> và localization key. Chốt dạng đã gom ngay trong spec để code không phải đổi tên sau.

#### Functions
| Hàm | Params | Return | Làm gì |
|-----|--------|--------|--------|
| `reset()` | — | — | Reset tất cả state về default, gọi trong Module.reset() |
| `[helperFn]` | [params] | [type] | [mô tả] |

### {FeatureName}Model.js

Mỗi class `extends cc.Class`. Thêm section này cho từng Model class.

#### {FeatureName}{Name}Model
Dùng để: [parse response field X / lưu data Y để UI đọc]

| Field | Kiểu | Default | Mô tả |
|-------|------|---------|-------|
| `id` | Number | `-1` | |
| `[field]` | [type] | [default] | [mô tả] |

### {FeatureName}JSONConfig.js *(nếu có)*

`extends BaseJSONConfig` | Implement bởi `/dev-config` ở Phase B

Spec cần xác định những gì feature sẽ đọc từ config — không cần file JSON thật:

| Field (sau parse) | Kiểu | Nguồn JSON key | Dùng ở đâu |
|-------------------|------|----------------|-----------|
| `[field]` | [type] | `dataConfig["key"]` | [Util / Module] |

| Getter | Return | Dùng ở đâu |
|--------|--------|-----------|
| `get[Name]()` | [type] | [caller] |
| `get[Name]By[Key]([key])` | [type] | [caller] |

### {FeatureName}Animate.js *(nếu có)*

Plain JS object (`= {}`)

| Hàm | Params | Làm gì |
|-----|--------|--------|
| `doPlay(cmd, mainGui, ...)` | ... | Chạy animation sequence |
| `[fn]` | [params] | [mô tả] |

### {FeatureName}Tutorial.js *(nếu có)*

Plain JS object (`= {}`)

| Field / Hàm | Kiểu | Mô tả |
|-------------|------|-------|
| `_isHasTutorial` | Boolean | Server flag: có tutorial không |
| `_isRunning` | Boolean | Tutorial đang chạy |
| `reset()` | — | Reset tất cả state |
| `[checkFn]` | — | Trigger / close tutorial theo điều kiện |

---

## ui/

> **Quy tắc chung:** File UI có `.json` (tạo bằng Cocos Studio) → `extends BaseScreen`, gọi `syncAllChild("{resPath}{FileName}.json")` trong `ctor`, theo sau là `this.retain()`. `retain()` bắt buộc cho **toàn bộ** class `extends BaseScreen` (GUI, Popup, LobbyIcon, Layer, Slot, ...) — thiếu sẽ crash khi node bị remove rồi re-add (show lại GUI, scroll TableView, ...). File chỉ là container/layout không có `.json` → `extends ccui.Layout`.
>
> **`_enableKeyboardListener = false`:** Thêm vào ctor của tất cả UI **không phải GUI/Popup chính** (LobbyIcon, Layer, Slot, Node...) để chặn back button chạy vào logic không cần thiết. GUI/Popup chính tự xử lý back button qua keyboard listener nên không cần set false.
>
> **`Utility.scaleBgrToFitScreen(this.{mainBgNode})`:** Thêm vào ctor của **GUI/Popup chính** (sau `retain()`), để scale down container chính khi màn hình nhỏ. Argument là node container chính của GUI — **không phải luôn luôn là `imageBg`**: đọc file `.json` của GUI đó để xác định node nào là root layout/background chứa toàn bộ nội dung (thường là node con trực tiếp của `imageFullBg` hoặc root panel).
> **Khai báo node names:** Khai báo **toàn bộ** node name từ file `.json` theo đúng thứ tự cây node (cha trước, con sau). `syncAllChild` chỉ bind được node nếu property đã khai báo; node cha phải khai báo trước mới truy cập được node con. Tên property = tên node bỏ dấu `_` (vd `image_BgList` → `imageBgList`). Đọc file `.json` để lấy danh sách node trước khi viết code.
>
> **Code patterns (đọc khi code Phase B):** Pattern chi tiết cho UI nằm ở file reference riêng — [reference-ui-patterns.md](reference-ui-patterns.md):
> - showGui / hideGui — pattern chuẩn cho GUI/Popup
> - Countdown — dùng GameLoop thay schedule
> - Button Listener — anti-pattern (không dùng addClickEventListener)
> - Localization — pattern cho static text labels
> - Purchase Price — setInfoPrice + doBuy cho GUI mua item/pass
> - Utility — các hàm hay dùng (format số/thời gian, texture, parse date)
> - Gửi gói tin — pattern chuẩn trong Module

---

### {FeatureName}MainGui.js

`extends BaseScreen` | Resource: `{resPath}{FeatureName}MainGui.json`

Màn hình UI chính. Đọc data từ `{FeatureName}Util`, không giữ state riêng.

| Method | Params | Mô tả |
|--------|--------|-------|
| `showGui()` | — | Hiển thị màn hình, gọi setInfo() |
| `hideGui()` | — | Ẩn màn hình |
| `setInfo()` | — | Bind toàn bộ data từ Util lên UI |
| `update{X}()` | — | Cập nhật phần X khi có thay đổi nhỏ |
| `[otherMethod]` | [params] | [mô tả] |

### {FeatureName}LobbyIcon.js

`extends BaseScreen` | Resource: `{resPath}{FeatureName}LobbyIcon.json`

| Method | Params | Mô tả |
|--------|--------|-------|
| `showGui()` | — | Hiển thị icon |
| `hideGui()` | — | Ẩn icon |
| `checkShowNotifyIcon(b)` | Boolean | Bật/tắt notification badge |

### {FeatureName}[Tên]Gui.js *(thêm section tương tự cho mỗi GUI khác)*

`extends BaseScreen` | Resource: `{resPath}{FeatureName}[Tên]Gui.json`

---

### TableView Patterns *(nếu feature có UI dạng danh sách/bảng)*

> **Pattern chi tiết (đọc khi code Phase B):** [reference-tableview-patterns.md](reference-tableview-patterns.md):
> - **Pattern A** — 1 item/hàng (`cc.TableView` trực tiếp): Slot + Table class, đầy đủ delegate methods, quy tắc `slotSize`/`contentSize`/`slot.setPosition`
> - **Pattern B** — N items/hàng (`TableRowSlot`): Slot + TableRow + Table class
> - **Button trong slot trên TableView** — chống nhầm scroll vs click (`setSwallowTouches`, `isTouchMoved()`)

---

## Constants Cần Thêm

### PoolFunction
| Constant | Dùng để |
|----------|---------|
| `{FEATURE}_SHOW_MAIN_GUI` | |
| `{FEATURE}_HIDE_MAIN_GUI` | |
| `{FEATURE}_SHOW_LOBBY_ICON` | |
| `{FEATURE}_HIDE_LOBBY_ICON` | |
| `{FEATURE}_SEND_LOAD_INFO` | |
| `{FEATURE}_SEND_{ACTION}` | |

### EXCHANGE.CMD
| Constant | CMD ID | Ghi chú |
|----------|--------|---------|
| `{FEATURE}_LOAD_INFO` | [hỏi server] | |
| `{FEATURE}_{ACTION}` | [hỏi server] | |

---

## Wiring — Files Ngoài Feature Folder

| Việc cần làm | File cần sửa | Thay đổi |
|-------------|-------------|---------|
| Đăng ký JS files | `project.json` | Search trước trong `jsList`; chỉ thêm path còn thiếu, không thêm trùng. Thêm vào cuối `jsList`: cách 1 dòng trống so với entry cuối, thứ tự `cmd/` → `logic/` → `ui/` → `{Prefix}Module.js` |
| Đăng ký module | `src/gamemgr/ModuleMgr.js` | Thêm `var {prefix}Module = new {FeatureName}Module()` và gọi `.init()` trong `init`, `.reset()` trong **cả 2 hàm** `reset` và `resetReloadConfig` |
| PoolFunction constants | [file chứa PoolFunction defs] | Thêm constants section trên |
| EXCHANGE.CMD constants | [file chứa CMD defs] | Thêm constants section trên |
| [việc khác] | [file] | [thay đổi] |

**Dependencies — Feature này dùng data từ:**

| Module / Util | Cần gì | Khi nào dùng |
|---------------|--------|-------------|
| `UserInfo` | `gold` | Validate trước action |
| `OfferSystem` | `checkCanShowOffer(EVENT_NAME)` | Sau LOAD_INFO |
| [module khác] | [field/method] | [khi nào] |
~~~~
