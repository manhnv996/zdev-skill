---
name: dev-config
description: "Tạo mới hoặc cập nhật JSONConfig cho BidaMobile (Cocos 2dx JS): đọc file JSON, tạo/sync class kế thừa BaseJSONConfig, đăng ký vào ConfigMgr.js và project.json. Dùng khi tạo config mới hoặc khi designer thay đổi format JSON."
argument-hint: "[tên-feature | đường dẫn .json | đường dẫn .json + đường dẫn .js (cho update)]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit
model: sonnet
---

# dev-config — BidaMobile (Cocos 2dx JS)

Tạo hoặc cập nhật `{Prefix}JSONConfig.js`. **Xác định flow trước:**

1. Nếu argument có cả đường dẫn `.json` lẫn `.js` → **Flow B**
2. Nếu chỉ có tên feature hoặc `.json`, sau khi xác định được `jsPath` ở Bước 0 → glob/check file tồn tại:
   - File JS **chưa có** → **Flow A: Tạo mới** (Bước 0 → 5)
   - File JS **đã có** → **Flow B: Cập nhật** (Bước U)

---

## Flow B: Cập nhật JSONConfig khi JSON thay đổi

> Dùng khi designer/server cập nhật file `.json` (thêm field, đổi format, ...). Không cần đụng ConfigMgr hay project.json.

### Bước U0: Xác định 2 file cần so sánh

- **File JSON mới**: từ argument hoặc hỏi user đường dẫn
- **File JS hiện tại**: từ argument hoặc hỏi user — nếu không có, gợi ý tìm theo pattern `{Prefix}JSONConfig.js` gần folder JSON

Nếu thiếu một trong hai → hỏi trước khi tiếp tục.

Nếu file JS có nhiều class, phải xác định class nào map với file JSON trước khi diff:
- Ưu tiên đọc spec doc nếu user đính kèm hoặc gọi từ `dev-feature`
- Nếu không có spec, grep trong `src/gamemgr/ConfigMgr.js` để tìm dòng `ClassName.getInstance(true).preInit(..., this._listJSONNew{N}[index])` và đối chiếu index với path JSON trong `_listJSONNew{N}`
- Nếu vẫn không xác định được class target → hỏi user, không tự sửa đại trà tất cả class trong file

### Bước U1: So sánh JSON mới với class hiện tại

1. Đọc file `.json` mới
2. Đọc file `{Prefix}JSONConfig.js` hiện tại
3. Với class target đã xác định, so sánh:
   - **Field mới trong JSON** chưa có trong `readConfig()` → cần thêm
   - **Field bị đổi key/format** → cần sửa cách đọc
   - **Field bị xóa** → cần xóa hoặc giữ với default (hỏi user)
4. Trình bày diff cho user theo format **Flow B — diff** trong [references/jsonconfig-template.md](references/jsonconfig-template.md).

### Bước U2: Đề xuất thay đổi getter

- Field mới → gợi ý getter mới nếu cần
- Field bị xóa → getter tương ứng có cần xóa không

Hỏi user: "Đây là các thay đổi tôi đề xuất. Bạn muốn điều chỉnh gì không?"

**Chờ user confirm trước khi sửa file.**

### Bước U3: Cập nhật file JS

Sửa đúng những gì đã confirm — không sửa phần không liên quan.

### Bước U4: Verify

- [ ] Đọc lại file JS — tất cả thay đổi đã đúng theo confirm
- [ ] Không có field cũ nào bị mất ngoài ý muốn
- [ ] Nếu có thể chạy local syntax check: `node --check {Prefix}JSONConfig.js`

In tổng kết theo format **Flow B — tổng kết** trong [references/jsonconfig-template.md](references/jsonconfig-template.md).

---

## Flow A: Tạo mới

---

## Bước 0: Thu thập thông tin

**Đọc argument:**
- Có đường dẫn `.json` → đọc file đó, dùng làm nguồn phân tích structure
- Có tên feature → dùng làm gợi ý, hỏi thêm
- Không có gì → hỏi

**Hỏi và gợi ý:**

1. **Tên feature / class prefix:** `PascalCase` (e.g. `RelicHunt`)

2. **Đường dẫn file JS output:** Nơi đặt `{Prefix}JSONConfig.js`
   - Gợi ý: cùng folder với Util/Module của feature (e.g. `src/game/event/{featureName}/logic/`)

3. **Đường dẫn file(s) JSON:**
   - Gợi ý: `res/config/json/event/{featureName}/` hoặc `res/config/json/{featureName}/`
   - Liệt kê tất cả file `.json` cần đọc (1 feature có thể có nhiều file → nhiều class)
   - Lưu lại relative path thật dưới `res/config/json/` để dùng trong `ConfigMgr` (vd `event/bpcustom/BP2026Info.json`, `newshop/BuyGoldConfig.json`, `club/ClubInfo.json`)

Số class = số file JSON đã liệt kê ở mục 3; tất cả nằm trong 1 file `{Prefix}JSONConfig.js`.

---

## Bước 1: Phân tích JSON

Với **mỗi file `.json`** đã xác định:

1. Đọc file JSON
2. Phân tích top-level keys và structure (object/array/primitive)
3. Xử lý getter list theo 2 trường hợp:

   **Trường hợp A — Có spec doc đã confirm** (dev-config được gọi từ dev-feature Phase B):
   - Đọc section `### {FeatureName}JSONConfig.js` trong spec để lấy Field table và Getter table đã confirm
   - Trình bày lại nhanh để user xác nhận: "Đây là getters đã confirm trong spec — tôi sẽ implement theo đúng danh sách này. Bạn có muốn điều chỉnh gì không?"
   - Nếu JSON thật có field mới chưa có trong spec → báo cho user biết và hỏi có cần thêm getter không; nếu có, cần cập nhật lại spec trước
   - **Không propose lại từ đầu** — spec là nguồn sự thật

   **Trường hợp B — Không có spec** (gọi trực tiếp, độc lập):
   - Trình bày đề xuất cho user:
     - **Typed fields**: tên field, kiểu, default value
     - **Getter methods** gợi ý dựa trên structure — list rõ từng method, vd:
       - `getCostPlayOnce()` — trả về cost dig 1 lần
       - `getNumGiftByChestId(chestId)` — lookup theo id
   - Hỏi user: "Đây là danh sách getters tôi đề xuất. Bạn muốn bỏ, sửa tên, hay thêm getter nào không?"

> Nếu file JSON **chưa có** (server/designer chưa cung cấp): hỏi user mô tả structure dự kiến — field nào, kiểu gì. Viết `readConfig()` với comment `// TODO: điều chỉnh khi có file JSON thật`.

**Chờ user confirm danh sách fields + getters trước khi code.**

---

## Bước 2: Tạo file JS

Trước khi viết, **bắt buộc đọc toàn bộ** [references/jsonconfig-template.md](references/jsonconfig-template.md) —
đó là khuôn chuẩn cho class `{Prefix}{Name}JSONConfig` và các format output.

Các guard không được bỏ qua dù đã đọc reference:

- Gọi từ file khác **luôn** qua `getInstance()`; `getInstance(true)` chỉ dùng trong ConfigMgr lúc `preInit`.
  Gọi thẳng trên class không báo lỗi nhưng không ra kết quả.
- Mỗi class wrap trong `// #region {ClassName}` / `// #endregion`, kể cả khi file có nhiều class.
- `readConfig()` reset array/object về `[]` / `{}` **trước** vòng lặp; cast kiểu rõ ràng (`parseInt`, `parseFloat`).

**Tạo file:** `{jsPath}/{Prefix}JSONConfig.js`

Nếu có nhiều class: tất cả trong 1 file, mặc định sắp xếp theo alphabetical order. Hỏi user: "Thứ tự các class trong file: [A, B, C...] — bạn có muốn đổi không?"

---

## Bước 3: Đăng ký vào ConfigMgr.js

`src/gamemgr/ConfigMgr.js` có 3 việc cần làm:

### 3a. Thêm path JSON vào list

Đọc phần khai báo các `_listJSONNew*`. Trước tiên search toàn bộ `_listJSONNew*` để xem relative path JSON đã tồn tại chưa.

- Nếu path đã tồn tại → không thêm trùng; ghi lại `list name` + `index` hiện có để dùng ở bước 3c
- Nếu path chưa tồn tại → tìm list cuối cùng và index cuối cùng của nó rồi mới thêm

**Rule tạo list mới:** Nếu list hiện tại đã có ≥ 80 entries → tạo `_listJSONNewN+1: [...]` mới, bắt đầu index từ 0.

Thêm mỗi file JSON vào **cuối** list hiện tại, dùng relative path thật dưới `res/config/json/`:
```js
"{relative/path/FileName}.json", //{index}
```
> Nhóm các file của cùng 1 feature lại, cách 1 dòng trống so với nhóm trước.

Ghi lại: `list name` + `index` của từng file (cần dùng ở bước 3c).

### 3b. Thêm vào `registerExtendWithBaseJSONConfig`

Trong hàm `registerExtendWithBaseJSONConfig()`, thêm 1 dòng cho mỗi class:
```js
Utility.extendWithStaticMethods({Prefix}{Name}JSONConfig, BaseJSONConfig);
```
Trước khi thêm phải grep class name trong hàm này. Nếu đã có dòng tương ứng → không thêm trùng. Nếu thiếu → thêm cạnh nhau, nhóm với các class cùng feature nếu đã có.

### 3c. Thêm vào `registerPreInitConfigNew{N}`

Mỗi `_listJSONNew{N}` có hàm tương ứng `registerPreInitConfigNew{N}()` (vd `_listJSONNew2` → `registerPreInitConfigNew2()`). Thêm 1 dòng cho mỗi class vào đúng hàm tương ứng với list đã chọn ở bước 3a:
```js
{Prefix}{Name}JSONConfig.getInstance(true).preInit(this._urlJSON, this._listJSONNew{N}[{index}]);
```
Trước khi thêm phải grep class name trong toàn bộ `registerPreInitConfigNew*`. Nếu đã có dòng preInit cho class đó → kiểm tra đúng list/index theo path JSON; nếu đúng thì giữ nguyên, nếu sai thì báo user trước khi sửa.

Thứ tự: nếu có class phụ thuộc nhau (class B gọi `ClassA.getInstance()` trong `readConfig`), class A phải được `preInit` **trước** class B.

> **Nếu vừa tạo list + hàm mới** (vd `_listJSONNew4` + `registerPreInitConfigNew4()`): kiểm tra `registerPreInitWithFile()` — nếu chưa có `this.registerPreInitConfigNew4()` thì thêm vào cuối danh sách các lời gọi trong hàm đó.

---

## Bước 4: Thêm vào project.json

Mở `project.json`, search path JS output trước:
- Nếu path đã có trong `jsList` (thường xảy ra khi chạy sau `dev-feature` Task 1) → không thêm trùng
- Nếu chưa có → thêm path file JS mới vào cuối `jsList`
- Cách 1 dòng trống so với entry cuối
- Format: dùng path thật của file JS output, ví dụ `"src/game/event/{featureName}/logic/{Prefix}JSONConfig.js"` hoặc path khác nếu feature không nằm trong `event/`

---

## Bước 5: Verify & Summary

**Agent tự check:**
- [ ] File JS tồn tại, có đủ số class đã thống nhất
- [ ] Mỗi class được wrap bằng `// #region {ClassName}` / `// #endregion`
- [ ] Mỗi class có `init()`, `readConfig()`, đủ getter methods đã thống nhất
- [ ] Nếu có thể chạy local syntax check: `node --check {Prefix}JSONConfig.js`
- [ ] `ConfigMgr.js` — mỗi relative path JSON xuất hiện đúng 1 lần trong `_listJSONNew*`
- [ ] `ConfigMgr.js` — `registerExtendWithBaseJSONConfig`: có đủ dòng cho mỗi class
- [ ] `ConfigMgr.js` — `registerPreInitConfigNew{N}`: có đủ dòng, đúng list + index, thứ tự phụ thuộc đúng
- [ ] `ConfigMgr.js` — không có duplicate `Utility.extendWithStaticMethods` hoặc duplicate `preInit` cho cùng class
- [ ] `project.json` — file JS có trong `jsList` đúng 1 lần

**In tổng kết** theo format **Flow A — tổng kết** trong [references/jsonconfig-template.md](references/jsonconfig-template.md).

**User phải test:**
- Load game → không crash, config được load
- Gọi `{Prefix}{Name}JSONConfig.getInstance().{getter}()` → trả về đúng giá trị từ JSON
