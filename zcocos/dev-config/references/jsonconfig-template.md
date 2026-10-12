# Reference — JSONConfig Template

Reference bắt buộc cho `dev-config`. Đọc toàn bộ file này trước khi tạo hoặc sửa
`{Prefix}JSONConfig.js`.

Đây là khuôn để copy. Các rule quyết định (chọn Flow A/B, phân tích JSON, đăng ký ConfigMgr,
project.json, verify) nằm trong `SKILL.md`.

Các điểm không được bỏ dù đã đọc reference:

- Gọi từ file khác **luôn** qua `getInstance()`. Gọi thẳng trên class không báo lỗi nhưng không
  ra kết quả — lỗi hỏng ngầm.
- Mỗi class wrap trong `// #region {ClassName}` / `// #endregion`, kể cả khi file có nhiều class.
- Trong `readConfig()` reset array/object về `[]` / `{}` **trước** vòng lặp.
- Class B gọi `ClassA.getInstance()` trong `readConfig` thì A phải `preInit` trước B.

---

## Template class

Tham khảo thêm nếu còn: `RelicHuntJSONConfig.js`, `BattlePassCustomJSONConfig.js`.

```js
// #region {Prefix}{Name}JSONConfig
var {Prefix}{Name}JSONConfig = BaseJSONConfig.extend({

    dataConfig: null,

    // typed fields — khởi tạo với default value
    {field1}: {default1},
    {field2}: {default2},

    init: function (data) {
        if (data == null) return;
        this.dataConfig = data;
        this.readConfig();
    },

    readConfig: function () {
        // reset arrays/objects trước khi parse
        // đọc this.dataConfig["key"] → gán vào typed fields
        // ví dụ simple key:   this.costPlay = this.dataConfig["costPlay"];
        // ví dụ object iter:  for (var s in this.dataConfig["items"]) { ... }
        // ví dụ nested:       this.dataConfig["digType"]["1"]
    },

    // getter methods
    get{Name}: function () {
        return this.{field};
    },

    get{Name}By{Key}: function ({key}) {
        var list = this.{listField};
        for (var i = 0; i < list.length; i++) {
            if (list[i].{key} == {key}) return list[i];
        }
        return null;
    },
});
// #endregion
```

Mỗi class trong file JS phải có `// #region {ClassName}` / `// #endregion`. Nếu file có nhiều class, wrap từng class riêng để khớp convention project.

**Lưu ý khi viết `readConfig()`:**
- Luôn reset array/object về `[]` / `{}` trước vòng lặp
- `for (var s in obj)` để iterate object keys
- Cast kiểu rõ ràng nếu cần: `parseInt(s)`, `parseFloat(v)`

> **Cách gọi từ file khác** — LUÔN dùng `getInstance()`:
> ```js
> // ✅ Đúng
> var list = {Prefix}{Name}JSONConfig.getInstance().getRewardList();
> // ❌ Sai — gọi trực tiếp trên class sẽ không ra kết quả
> var list = {Prefix}{Name}JSONConfig.getRewardList();
> ```
> `getInstance(true)` chỉ dùng trong ConfigMgr khi khởi tạo (`preInit`). Mọi chỗ khác dùng `getInstance()` không có argument.

---

## Format output

### Flow B — diff trình bày cho user (Bước U1)

```
Class: {Prefix}{Name}JSONConfig

Thêm mới:
  + field "newKey" → gợi ý: this.newField = this.dataConfig["newKey"]

Thay đổi:
  ~ "oldKey" đổi thành "newKey" → cần sửa readConfig()

Bị xóa:
  - "removedKey" → giữ field với default hay xóa hẳn?
```

### Flow B — tổng kết (Bước U4)

```
## dev-config update hoàn tất

**Class**: {Prefix}{Name}JSONConfig
**Thêm**: {field1}, {field2}
**Sửa**: {field3}
**Xóa**: {field4}
**Getter mới**: {getter1()}
```

### Flow A — tổng kết (Bước 5)

```
## dev-config hoàn tất

**Feature**: {featureName}
**File JS**: {jsPath}/{Prefix}JSONConfig.js
**Classes**: {N} class

**{Prefix}{Name}JSONConfig** — `{FileName}.json`
- `getter1()`
- `getter2()`

**{Prefix}{Name2}JSONConfig** — `{FileName2}.json`
- `getter1()`
- ...

**Wiring**: ConfigMgr.js ✅ | project.json ✅
```
