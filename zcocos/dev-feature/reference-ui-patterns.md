# Reference — UI Patterns (BidaMobile Cocos 2dx JS)

Các pattern code chuẩn cho file UI (`extends BaseScreen` / `ccui.Layout`). Dùng ở **Phase B** khi code các file trong `ui/` và `Module`.

---

## showGui / hideGui — Pattern chuẩn cho GUI/Popup

Mọi file GUI/Popup `extends BaseScreen` có `showGui`/`hideGui` đều dùng pattern sau:

```js
showGui: function () {
    this.showDisable();

    if (this.parent != null) this.parent.removeChild(this);
    var _parent = ScreenMgr.getCurrScreen();
    _parent.addChild(this, _parent.getChildren().length);

    ActionGame.doZoomIn(this._rootNode, 0);
    this._super();

    // ---- custom code dưới đây (setInfo, scrollToPage, ...) ----
},

hideGui: function () {
    this.hideDisable();
    if (this.parent == null) return;
    this.parent.removeChild(this);
    this._super();
},
```

> **Không** dùng pattern cũ: `this._super()` trước, rồi mới addChild/removeChild.
> **LobbyIcon** là ngoại lệ: `showGui` add vào màn hình lobby cụ thể (`ScreenMgr.getScreen(gc.SCREEN_ID.LOBBY)`), không phải `getCurrScreen()`.

---

## Countdown — Dùng GameLoop thay schedule

**Không dùng** `this.schedule` / `this.unschedule` cho countdown. Dùng `GameLoop` để tránh vấn đề lifecycle với node bị retain/remove.

```js
// ✅ ĐÚNG — dùng GameLoop
_startCountdown: function () {
    GameLoop.removeFunction("feature_countdown_key");
    this._countdownAccum = 0;
    this._updateCountdown(0);
    GameLoop.addFunction("feature_countdown_key", this._updateCountdown, this);
},

_stopCountdown: function () {
    GameLoop.removeFunction("feature_countdown_key");
    this._countdownAccum = 0;
},

_updateCountdown: function (dt) {
    this._countdownAccum = (this._countdownAccum || 0) + dt;
    if (this._countdownAccum < 1 && dt > 0) return; // chỉ update mỗi giây
    this._countdownAccum = 0;
    // ... update text countdown
},
```

- **Key phải unique** toàn cục — dùng `"featureName_purpose"` (vd `"mg_main_gui_countdown"`). Với slot trong TableView: thêm id/index vào key (vd `"mg_task_slot_" + eventName`).
- **Gọi `_stopCountdown()` trong `hideGui()`** — KHÔNG dùng `onExit` của slot vì `cc.TableView` recycle cell không đảm bảo trigger `onExit`.
- Với slot trong TableView: thêm method `cleanupSlots()` vào Table class (iterate `cellAtIndex` → `_stopCountdown()`), gọi từ MainGui's `hideGui()` trước `removeChild`.

---

## Button Listener — Anti-pattern cần tránh

`BaseScreen` tự động đăng ký tất cả button nodes làm touch target và route qua `onTouchEndEvent` / `onTouchBeganEvent` / `onTouchCancelledEvent` / `onTouchMovedEvent`. **Không bao giờ** dùng `addClickEventListener` hoặc `addTouchEventListener` trong `ctor`, `setInfo`, hay bất kỳ method nào khác.

```js
// ❌ SAI — không cần và gây duplicate listener
ctor: function () {
    this._super();
    this.syncAllChild("...");
    this.btnClose.addClickEventListener(this._onBtnCloseTap.bind(this)); // XÓA
},

// ✅ ĐÚNG — BaseScreen đã lo, chỉ cần handle ở đây
onTouchEndEvent: function (sender) {
    this._super(sender);
    switch (sender) {
        case this.btnClose:
            PoolFunction.doFunc(PoolFunction.{FEATURE}_HIDE_MAIN_GUI);
            break;
    }
},
```

Tương tự cho `onTouchBeganEvent` (show tooltip) và `onTouchCancelledEvent` (hide tooltip) — dùng switch(sender), không dùng `addTouchEventListener`.

---

## Màu chữ trong button — `Utility.setTextBtn*`

Text nằm trong `btn_*` phải được set màu chữ + outline theo **màu của nút**, nếu không chữ sẽ trắng trơn không viền và chìm vào nền nút.

Gọi **một lần trong `ctor`**, ngay sau `syncAllChild(...)`:

```js
ctor: function () {
    this._super();
    this.syncAllChild("content/{feature}/{Prefix}Gui.json");
    this.retain();
    //Mau chu + vien theo mau nut. Nut khong doi texture luc runtime nen set 1 lan la du.
    Utility.setTextBtnGreen(this.labelBtnBuy);      //btn_Buy  dung common_btn_popup
    Utility.setTextBtnDisable(this.labelBtnSkip);   //btn_Skip dung common_btn_popup_dis
},
```

Chỉ phải gọi lại khi code **đổi texture của nút** lúc runtime (vd `loadTextures` để chuyển enable ↔ disable). `setVisible` / `setTouchEnabled` / `setString` **không** làm mất outline → không cần set lại.

### Chỉ áp dụng khi thỏa CẢ HAI điều kiện

1. **Nút dùng texture `content/common/textures/common_btn_*`.** Nút có texture riêng của feature thì art thường đã canh sẵn màu chữ theo bộ màu nút đó.
2. **Node text chưa được set màu/viền trong `.json`.** Đã có `OutlineEnabled: true`, `ShadowEnabled: true`, hoặc `CColor` khác `(255,255,255)` → đó là **chủ ý của designer**, giữ nguyên, không ghi đè bằng code.

Điều kiện 2 kiểm được bằng máy nên **rà `.json`**, đừng đoán từ tên node:

| Node `TextObjectData` trong `btn_*` | Kết luận |
|---|---|
| `CColor` = `(255,255,255)`, không `OutlineEnabled`/`ShadowEnabled` | chưa set → **cần** `setTextBtn*` |
| Có `OutlineEnabled: true` hoặc `CColor` khác trắng | art đã set → **bỏ qua** |

Hai điều kiện thường trùng nhau; nếu lệch nhau thì dừng lại hỏi user thay vì tự chọn.

### Bảng tra hàm theo màu nút

| Texture nút | Màu | Hàm |
|---|---|---|
| `common_btn_popup.png` | xanh lá | `Utility.setTextBtnGreen(label)` |
| `common_btn_popup_dis.png` | xám | `Utility.setTextBtnDisable(label)` |
| — | xanh dương | `Utility.setTextBtnBlue(label)` |
| — | đỏ | `Utility.setTextBtnRed(label)` |
| — | vàng | `Utility.setTextBtnYellow(label)` |
| — | tím | `Utility.setTextBtnPurple(label)` |

Không chắc màu thì **mở file PNG ra xem** (tool Read hiển thị được ảnh), đừng suy từ tên file.

**Hai cái bẫy:**

- `setTextBtnGreen` / `Blue` / `Red` / `Yellow` gọi `label.setTextColor()` **trước** khi null-check → label null sẽ crash ngay trong `ctor`. (`setTextBtnDisable` / `setTextBtnPurple` có guard.) Chỉ gọi trên node chắc chắn tồn tại trong `.json`.
- `Utility.setOutline` bỏ qua `ccui.TextBMFont` và `ccui.RichText` — hai loại này không nhận outline, gọi vào là no-op.

**Không thuộc phạm vi:** node text nằm trong `btn_*` nhưng không phải nhãn của nút (vd `label_Time` trên dải countdown của icon lobby).

> Code block ở trên là nguồn chuẩn, đủ để implement. Các file dưới đây chỉ là ví dụ thật để xem thêm **nếu còn tồn tại** — grep thấy mất thì bỏ qua, đừng đi tìm file thay thế và đừng coi là thiếu dữ kiện.
>
> - `RelicHuntPopupGui.ctor()` — ví dụ gọi 1 lần trong ctor

---

## Localization — Pattern chuẩn cho static text labels

Static text (title, button label, tab text...) **không** set trong `ctor` hay `setInfo`. Luôn override `localize()` để framework tự trigger khi ngôn ngữ thay đổi.

> **Chọn guard theo lifecycle:** Chỉ dùng `_isShowing` khi chính class có `showGui()` / `hideGui()`. Node không có hai method này (Layer, Slot, Table hoặc Node do parent quản lý) **không được dùng `_isShowing`** và mặc định không cần lifecycle guard; gọi `localize()` khi bind/reload data.

**Node có `showGui()` (GUI/Popup/Icon)** — dùng `_isShowing`:
```js
localize: function () {
    this._super();
    if (!this._isShowing) {
        this._changeLocalize = true;
        return;
    }
    this._changeLocalize = false;
    if (this.labelTitle != null) this.labelTitle.setString(fr.Localization.text("key_title"));
},
```

**Node không có `showGui()` (Layer, Slot, Table)** — không guard lifecycle, **gọi `this.localize()` ở đầu `setInfo()` / `reloadDataTable()`**:
```js
localize: function () {
    this._super();
    if (this.labelName != null) this.labelName.setString(fr.Localization.text("key_name"));
},

setInfo: function (data) {
    this.localize();  // ← bắt buộc gọi ở đây
    // ... rest of setInfo
},
```

---

## Purchase Price Pattern

Cho GUI hiển thị & xử lý mua item/pass (dialog buy).

### Cấu trúc

**Field lưu trữ:**
```js
_infoCost: 0,
_infoCurrency: "",
```

**2 methods:**

1. **`setInfoPrice()` — tính toán giá**
   - Xác định `paymentType` từ `gc.PAYMENT_TYPE`
   - Fallback IAP nếu `price <= 0`
   - Lấy `cost` + `currency` từ JSONConfig
   - **Lưu vào** `this._infoCost` + `this._infoCurrency`
   - Hiển thị text, xử lý IAP display (store price, ...)

2. **`doBuy()` — gọi mua** (define **trước** `onTouchEndEvent`)
   - Lấy `packName`, `packId` từ Util
   - Gọi **duy nhất 1 lần**: `PaymentUtil.doShowOptionToPurchase(packName, packId, this._infoCost, this._infoCurrency, -1, false, -1)`
   - **KHÔNG switch-case** payment type — đã resolve ở `setInfoPrice()` rồi

### Pattern Đầy Đủ

```js
var BuyPassGui = BaseScreen.extend({
    labelPrice: null,
    btnBuy: null,
    _infoCost: 0,
    _infoCurrency: "",

    setInfo: function () {
        this.localize();
        this.setInfoPrice();  // ← tách riêng
    },

    setInfoPrice: function () {
        var rarity = Model.rarity;
        var paymentType = gc.PAYMENT_TYPE;

        var price = JSONConfig.getInstance().getPrice(rarity, paymentType);
        if (price <= 0 && paymentType != PMSeaDefine.TYPE.IAP) {
            paymentType = PMSeaDefine.TYPE.IAP;
            price = JSONConfig.getInstance().getPrice(rarity, paymentType);
        }
        var currency = PMSeaDefine.getCurrency(paymentType);

        this._infoCost = price;
        this._infoCurrency = currency;

        if (price > 0) {
            this.labelPrice.setString(Utility.numberToStr(price) + " " + currency);
            if (paymentType == PMSeaDefine.TYPE.IAP) {
                var priceList = gc.IAP.getListPrice();
                var config = IAPJSONConfig.getInstance().getPackByPrice(price);
                if (priceList && config) {
                    var storePrice = priceList[config];
                    if (storePrice) this.labelPrice.setString(storePrice);
                }
            }
        } else {
            this.labelPrice.setString("");
        }
    },

    doBuy: function () {
        var packName = Util.getPurchasePackName(Model.rarity);
        var packId = Util.getPurchasePackId(Model.rarity);

        PaymentUtil.doShowOptionToPurchase(
            packName, packId,
            this._infoCost, this._infoCurrency,
            -1, false, -1
        );
    },

    onTouchEndEvent: function (sender) {
        this._super(sender);
        switch (sender) {
            case this.btnBuy:
                this.doBuy();
                break;
        }
    },

    localize: function () {
        this._super();
        // ... static text
    },
});
```

### Lợi ích

- ✅ Tính toán giá 1 lần ở `setInfoPrice()`, dùng lại ở `doBuy()` → không tính 2 lần
- ✅ Xử lý payment type fallback tập trung ở 1 chỗ → dễ bảo trì
- ✅ `doBuy()` đơn giản, không switch-case → rõ ràng, dễ test
- ✅ IAP logic (store price) ở `setInfoPrice()` → không cần xử lý đặc biệt ở `doBuy()`

### Ví dụ thật — tuỳ chọn

> Code block ở trên là nguồn chuẩn, đủ để implement. Các file dưới đây chỉ là ví dụ thật để xem thêm **nếu còn tồn tại** — grep thấy mất thì bỏ qua, đừng đi tìm file thay thế và đừng coi là thiếu dữ kiện.
>
> - `GuiSportBetBuyPremium.doBuyPremium()` — pattern gốc
> - `BPCustomBuyPassGui.doBuy()` — ví dụ BattlePass

---

## Utility — Các hàm hay dùng trong UI

> Luôn dùng đúng tên hàm — **KHÔNG tự đặt tên rồi đoán** (vd `formatBigNumber`, `secondsToHms` không tồn tại).

**Format số:**

| Hàm | Dùng khi |
|-----|---------|
| `Utility.numberToStr(n)` | Hiển thị số với dấu phân cách nghìn (gold, điểm, đếm...) — dùng cho hầu hết trường hợp |
| `Utility.toMoneyString(n)` | Rút gọn số rất lớn → `1.5M`, `2.3B` (top leaderboard, tích lũy lớn) |

**Format thời gian (countdown):**

| Hàm | Output ví dụ | Dùng khi |
|-----|-------------|---------|
| `Utility.milToRemainTimeFormatTwoUnits2s(sec)` | `"2 ngày 3 giờ"` / `"45 phút 12 giây"` | Countdown event — tự chọn 2 đơn vị lớn nhất |
| `Utility.milToRemainTimeFormat(sec)` | `"HH:MM:SS"` | Countdown ngắn dạng đồng hồ |

**Texture:**

| Hàm | Ghi chú |
|-----|--------|
| `Utility.reloadImageTexture(node, resName, texType)` | `texType` thường là `ccui.Widget.PLIST_TEXTURE` (atlas) hoặc `ccui.Widget.LOCAL_TEXTURE` (file riêng). Nếu `resName` rỗng/null thì KHÔNG gọi — check trước. |
| `Utility.scaleBgrToFitScreen(node)` | Scale down node để vừa màn hình nhỏ — dùng cho background chính của GUI/Popup |

**Parse thời gian từ server:**

| Hàm | Ghi chú |
|-----|--------|
| `Utility.convertStringToDateTime(str, isEndOfDay)` | Parse string `"YYYYMMDD"` → Unix ms. `isEndOfDay=true` → cuối ngày 23:59:59 |

**Hiện ngày/giờ từ timestamp, lấy "bây giờ":** xem section **Thời gian — luôn theo SERVER** bên dưới.

---

## Thời gian — luôn theo SERVER, không theo máy

Mọi thời gian **hiển thị cho user** và mọi phép **so với "bây giờ"** phải theo giờ server. User (và QC)
có thể đổi giờ / múi giờ thiết bị bất cứ lúc nào; code đọc giờ máy sẽ hiện sai ngày, countdown sai, hoặc
mở/khoá tính năng sai lúc. Có **2 cách** vô tình dùng giờ máy — phải chặn cả hai:

| | ❌ Phụ thuộc máy | ✅ Theo server |
|---|---|---|
| **1. Lấy "bây giờ"** | `Date.now()`, `new Date()` không tham số | `PoolFunction.doFunc(PoolFunction.SERVER_TIME)` (ms) |
| **2. Đổi timestamp ra ngày/giờ** | `new Date(ms).getDate()` / `getHours()` / `getMonth()` / `setHours()` — đọc theo **múi giờ máy** | Helper Utility bên dưới — quy về giờ server UTC+7 |

Loại 2 khó thấy hơn: timestamp **đã lấy từ server** vẫn hiện sai, vì bước đổi ra ngày dùng múi giờ máy.
Cùng một mốc `00:05 03/10` giờ VN, máy đặt giờ Los Angeles đọc `new Date(t).getDate()` ra `2`.

**Helper có sẵn — dùng, không tự viết hàm format ngày:**

| Hàm | Output (mốc `00:05:09` ngày `03/10/2026` giờ VN) | Ghi chú |
|-----|-----|-----|
| `Utility.millisToDateTime(ms)` | `"3/10/2026"` | Ngày — **không** đệm số 0, **có** năm |
| `Utility.millToDate(ms)` | `"00:05:09"` | ⚠️ Tên ghi *Date* nhưng trả **giờ** `HH:MM:SS` |
| `Utility.millToDateHourMinute(ms)` | `"00:05"` | `HH:MM` |
| `Utility.getTimeInVN(dateObj)` | `Date` | Chỉ khi cần format riêng không có helper: đọc `getDate()`/`getHours()` **trên object trả về** |

Đã verify 3 helper đầu ra cùng kết quả khi máy đặt múi giờ VN và Los Angeles.

```js
// ✅ "bây giờ" + đếm ngược
const serverTime = PoolFunction.doFunc(PoolFunction.SERVER_TIME);
if (serverTime <= 0) return;                 //chưa login xong / chưa sync — KHÔNG fallback Date.now()
const remainSec = (XUtil._endTimeUnix - serverTime) / 1000;

// ✅ hiện ngày từ timestamp server
label.setString(Utility.millisToDateTime(XUtil._startTimeUnix));

// ❌ cả hai dòng dưới đều đọc giờ máy
const now = Date.now();
const day = new Date(XUtil._startTimeUnix).getDate();
```

**Mốc kết thúc là mốc ĐÓNG (exclusive).** Server trả `0h 06/10` nghĩa là chạy hết ngày `05/10`. Khi
hiện *ngày cuối* thì lùi 1ms trước khi format: `Utility.millisToDateTime(endTimeUnix - 1)`. Countdown thì
vẫn dùng mốc thật, không lùi.

> Không áp dụng cho đo **khoảng thời gian trôi qua** trong 1 phiên (delta giữa 2 lần đọc cùng một đồng
> hồ, vd `gc.TIME.getTime()` cho animation/countdown nội bộ GUI) — đổi giờ máy không làm sai delta đó.

---

## Gửi gói tin — Pattern chuẩn trong Module

Không phải mọi `send*()` đều show disable screen. Quyết định theo UX intent, không chỉ theo tên CMD:
- Auto load / background sync / server polling: **không** gọi `SHOW_DISABLE_SCREEN` dù CMD có thể tên `LOAD_INFO`
- User-triggered blocking flow cần chờ response để tiếp tục: gọi `SHOW_DISABLE_SCREEN` trước khi gửi packet, kể cả CMD được đặt tên `LOAD_INFO`
- Handler của flow có disable phải gọi `HIDE_DISABLE_SCREEN` ngay đầu hàm, trước `switch(cmd.getError())`

**Load info / background sync:**
```js
send{Prefix}LoadInfo: function () {
    var cmd = new CmdSend{Prefix}LoadInfo();
    // LOAD_INFO thường không có params; nếu protocol có param thì set field theo spec ở đây.
    // cmd.someField = params.someField;
    var con = EXCHANGE.connector;
    if (con) con.sendPacket(cmd);
},
```

**User action có disable screen:**
```js
send{Prefix}{Action}: function (params) {
    PoolFunction.doFunc(PoolFunction.SHOW_DISABLE_SCREEN);

    var cmd = new CmdSend{Prefix}{Action}();
    cmd.someField = params;
    var con = EXCHANGE.connector;
    if (con) con.sendPacket(cmd);
},

cmdReceive{Prefix}{Action}: function (cmd) {
    PoolFunction.doFunc(PoolFunction.HIDE_DISABLE_SCREEN);

    switch (cmd.getError()) {
        case ErrorDefine.SUCCESS:
            // update data/UI
            break;
        default:
            PoolFunction.doFunc(PoolFunction.SHOW_MESSAGE_BOX, fr.Localization.text("club_notify_err_normal") + "(" + cmd.getError() + ")");
            break;
    }
},
```
