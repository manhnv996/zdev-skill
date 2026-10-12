# Reference — TableView Patterns (BidaMobile Cocos 2dx JS)

Dùng khi feature có UI dạng danh sách/bảng (`cc.TableView`). Áp dụng ở **Phase B** khi code các file Slot + Table trong `ui/`.

---

## Pattern A — 1 item/hàng

(`cc.TableView` trực tiếp, vd `RelicHuntMapRewardNode`)

2 class trong cùng 1 file:

| Class | extends | Resource |
|-------|---------|---------|
| `{Prefix}[Tên]Slot` | `BaseScreen` | `{resPath}{Prefix}[Tên]Slot.json` |
| `{Prefix}[Tên]Table` | `ccui.Layout` | *(không có)* |

`{Prefix}[Tên]Table` — pattern chuẩn (tham khảo `RelicHuntMapRewardNodeTable`):

```js
var {Prefix}[Tên]Table = ccui.Layout.extend({

    contentSize: cc.size(0, 0),   // override trong ctor từ parent
    slotSize: cc.size(W, H),      // kích thước 1 cell — dùng cho cả size lẫn slot position
    listInfo: [],

    ctor: function (contentSize) {
        this._super();
        this.contentSize = contentSize;
        this.setContentSize(this.contentSize);
        this.createTableView();
    },

    createTableView: function () {
        if (this._tableView != null) return;
        this._tableView = new cc.TableView(this, this.contentSize);
        this._tableView.setDirection(cc.SCROLLVIEW_DIRECTION_HORIZONTAL); // hoặc VERTICAL
        this._tableView.setDelegate(this);
        this.addChild(this._tableView);
        this._tableView.reloadData();
    },

    reloadData: function () {
        if (this._tableView != null) this._tableView.reloadData();
    },

    // Dùng khi muốn reload data nhưng giữ nguyên vị trí scroll hiện tại
    // Horizontal scroll: lưu/khôi phục container.x → offset cc.p(x, 0)
    // Vertical scroll:   lưu/khôi phục container.y → offset cc.p(0, y)
    reloadDataAndKeepPos: function () {
        if (this._tableView == null) return;
        var _x = this._tableView.getContainer().x; // thay bằng .y nếu scroll dọc
        this._tableView.reloadData();
        this._tableView.setContentOffset(cc.p(_x, 0)); // cc.p(0, _y) nếu scroll dọc
    },

    tableCellAtIndex: function (table, idx) {
        var cell = table.dequeueCell();
        var slot;
        if (!cell) {
            cell = new cc.TableViewCell();
            slot = new {Prefix}[Tên]Slot();
            slot.setTag(0);
            cell.addChild(slot);
            slot.setPosition(cc.p(this.slotSize.width / 2, this.slotSize.height / 2));
        } else {
            slot = cell.getChildByTag(0);
        }
        slot.setInfo(this.listInfo[idx]);
        return cell;
    },

    tableCellSizeForIndex: function (table, idx) {
        return cc.size(this.slotSize.width, this.slotSize.height);
    },

    tableCellTouched: function (table, cell) { },

    numberOfCellsInTableView: function () {
        return this.listInfo.length;
    },
});
```

> **Quy tắc:** `slotSize` khai báo là class property — dùng cho cả `tableCellSizeForIndex` lẫn `slot.setPosition`. KHÔNG hardcode size inline. TableView tạo trong `createTableView()` riêng, KHÔNG inline trong `ctor`.
>
> **`slotSize` phải ĐO từ file `.json`, không được đoán.** Đây là lỗi hay gặp nhất và biểu hiện là "content trong TableView không ở đúng giữa". Trước khi khai báo, đọc `.json` lấy:
> - `Size` của node container trong Layer (vd `image_BgStreakList`) → chính là `contentSize` truyền vào Table
> - `Size` của node nền lớn nhất trong Slot (vd `image_Bg2` / `image_Bg2s`) → chiều cao/rộng thật của 1 cell
>
> Nếu slot có `Size = 0x0` ở root, đó là bình thường: `syncAllChild` dựng node rỗng và visual nằm ở node con. Kiểm tra `image_Bg` có `pos=(0,0) anchor=(0.5,0.5)` — khi đó **tâm visual trùng gốc slot**, nên `slot.setPosition(cc.p(slotSize.width / 2, slotSize.height / 2))` mới căn giữa đúng. Sai `slotSize` thì dòng này căn giữa vào một ô sai kích thước → lệch.
>
> **Danh sách N phần tử cố định lấp kín container** (vd thang 9 bậc): tính `slotSize` trong `createTableView()` theo `contentSize`, đừng hardcode:
> ```js
> createTableView: function () {
>     if (this._tableView != null) return;
>     //N o co dinh phai lap kin chieu ngang -> chia deu theo contentSize that
>     this.slotSize = cc.size(this.contentSize.width / N, this.contentSize.height);
>     ...
> }
> ```
> Danh sách scroll được thì `slotSize.width` lấy theo `contentSize.width`, chỉ `height` là design value cố định.
>
> **`slot.setPosition` bắt buộc:** Slot node có `contentSize = (0, 0)` nên sau `cell.addChild(slot)` phải gọi `slot.setPosition(cc.p(this.slotSize.width / 2, this.slotSize.height / 2))` để đặt vào trung tâm cell. Thiếu dòng này slot sẽ nằm ở góc (0, 0) của cell thay vì giữa.
>
> **Table `contentSize` phải lấy từ parent:** Trong Layer's `createTable()`, luôn dùng `parent.getContentSize()` để lấy size rồi truyền vào constructor của Table — KHÔNG dùng giá trị hardcode. Khi `table.contentSize == parent.contentSize`, add bằng `parent.addChild(table)` là đủ, **KHÔNG cần gọi `table.setPosition`**. Class property `contentSize` trong Table class chỉ là fallback khi parent null — vẫn nên khai báo giá trị ước tính có nghĩa (không để 0, 0) để dễ nhận biết khi đọc code.
> `slotSize` **không truyền qua constructor** — chỉ có thể lấy được `contentSize` từ parent, còn `slotSize` là design decision nên khai báo thẳng trong Table class property. Constructor Table chỉ nhận `contentSize`.

---

## Pattern B — N items/hàng

(`TableRowSlot`, vd `StorageGemSlot` với 3 items/hàng)

3 class trong cùng 1 file:

| Class | extends | Resource |
|-------|---------|---------|
| `{Prefix}[Tên]Slot` | `BaseScreen` | `{resPath}{Prefix}[Tên]Slot.json` |
| `TableRow{Prefix}[Tên]Slot` | `TableRowSlot` | *(không có)* |
| `Table{Prefix}[Tên]` | `ccui.Layout` | *(không có)* |

`TableRow{Prefix}[Tên]Slot` set `MAX_CELL = N`, implements:
- `_doInitCellSlot(idx)` — tạo mới slot, addChild, setInfo
- `_doUpdateCellSlot(idx)` — gọi setInfo trên cell đã có

`Table{Prefix}[Tên]` tạo `cc.TableView`, implements delegate như Pattern A. Thêm `updateRowList(list)` để chunk list thành mảng N-item rồi mới `reloadData`.

---

## Button trong slot nằm trên TableView — chống nhầm scroll vs click

Khi slot có button phủ gần hết diện tích (người dùng vuốt qua slot dễ bị hiểu là click), cần 3 việc:

*Trong Slot class:*
```js
_parentTableView: null,

setParentTableView: function (parentTableView) {
    this._parentTableView = parentTableView;
},

ctor: function () {
    // ...
    if (this.btnA) this.btnA.setSwallowTouches(false);  // mỗi btn phủ lớn
    if (this.btnB) this.btnB.setSwallowTouches(false);
},

onTouchEndEvent: function (sender) {
    this._super(sender);
    switch (sender) {
        case this.btnA:
            if (this._parentTableView != null && this._parentTableView.isTouchMoved()) return;
            // action...
            break;
        case this.btnB:
            if (this._parentTableView != null && this._parentTableView.isTouchMoved()) return;
            // action...
            break;
        // logic chung sau switch (vd hide tooltip) sẽ không bị block
    }
},
```

> Check `isTouchMoved()` phải nằm **trong từng case**, không đặt trước switch — để tránh block logic chung sau switch (vd `HIDE_TOOL_TIP`).

*Trong Table class — `tableCellAtIndex`:*
```js
if (!cell) {
    cell = new cc.TableViewCell();
    slot = new {Prefix}[Tên]Slot();
    slot.setTag(0);
    slot.setParentTableView(this._tableView);   // ← truyền ref tableView
    cell.addChild(slot);
    slot.setPosition(...);
}
```

> Code block ở trên là nguồn chuẩn, đủ để implement. Các file dưới đây chỉ là ví dụ thật để xem thêm **nếu còn tồn tại** — grep thấy mất thì bỏ qua, đừng đi tìm file thay thế và đừng coi là thiếu dữ kiện.
>
> - `StorageGemSlot` — Pattern B
> - `ShopGemSmallSlot` — Pattern A
