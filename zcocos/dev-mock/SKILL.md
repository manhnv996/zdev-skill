---
name: dev-mock
description: Use when creating or updating BidaMobile dev-only fake data, mock test cases, mock flows, Cheat.js triggers, or QA flows for Cocos2d-x JS features/events without packing mock code into project.json, CDN, or APK.
argument-hint: "[tên feature | docs/modules/{feature} | src feature folder]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
model: sonnet
---

# dev-mock - BidaMobile Mock Test Flow

Tạo mock test dev-only cho feature/event để user test UI/flow bằng phím cheat, không đưa fake data vào package production.

## 3 mục đích của mock test

Mọi quyết định thiết kế phải quy về 3 mục đích này. Nhầm mục đích là ra mock không dùng được.

| # | Mục đích | Nghĩa |
|---|---|---|
| 1 | **Giả lập gói tin server về** | Bấm phím → dựng gói tin giả → gọi **đúng handler thật** trong Module. Xem client xử lý ra sao khi gói đó về |
| 2 | **Giả lập data** | Chuẩn bị sẵn các **bộ data** cho từng kịch bản, tester chỉ đổi tên bộ là xem được data đó hiển thị ra sao trong GUI |
| 3 | **Giả lập flow** | Flow cần action của user + nhận gói tin, vd màn kết quả yêu cầu bấm "Nhận" mà bấm thật thì gửi packet lên server. Ít dùng hơn 2 cái trên |

Mục 1 là **bắt buộc và đầy đủ**: feature có bao nhiêu `cmdReceive*` trong Module thì có bấy nhiêu flow giả lập gói tin, không thiếu cái nào.

## Core Contract

- Runtime mock nằm trong `docs/modules/{feature}/mock/runtime/`, không nằm trong `src/game/...`.
- Không thêm mock runtime/config vào `project.json`.
- `Cheat.js` chỉ giữ loader/trigger mỏng; không chứa scenario data dài.
- `mock-current.json` là file tester sửa hằng ngày. Bấm phím cheat sẽ đọc lại config mới nhất.
- Mock JS chỉ load khi object mock chưa tồn tại; muốn reload JS trong app đang chạy thì thêm `"reloadScript": true` vào config tạm thời.
- **Mock không chép lại các bước của handler.** Dựng gói tin giả rồi gọi thẳng `Module.cmdReceiveXxx()`. Chép là mỗi lần handler đổi thì mock lệch, và thứ đang test không còn là code thật.
- **Mốc thời gian trong mock cũng theo server.** "Bây giờ" lấy từ `PoolFunction.SERVER_TIME` — chưa có thì log rồi bỏ qua, **không** fallback `Date.now()`. Mốc theo ngày (0h, cuối ngày) tính theo giờ server UTC+7, không dùng `new Date().setHours()`. Code thật đọc giờ server; mock dựng theo giờ máy sẽ tự tạo ra data lệch với chính code đang test.

## When to Use

Dùng khi user muốn tạo/thêm/cập nhật fake data test case, mock flow, mock server data/load-info/action, tách mock khỏi `Cheat.js`, tạo scenario matrix, hoặc test UI flow bằng cheat key mà không đưa mock vào CDN/APK.

Không dùng cho unit test tự động hoặc server integration test thật.

## Baseline Failures to Prevent

| Failure | Correct shape |
|---------|---------------|
| Fake data đặt thẳng trong `Cheat.js` | Data nằm trong `{Feature}Mock.js` dưới `docs/.../mock/runtime/` |
| Mock file đặt trong `src/` và thêm vào `project.json` | Runtime mock không đăng ký `project.json` |
| Đổi case phải restart app | Sửa `mock-current.json`, save, bấm phím cheat |
| Thiếu flow cho một số gói tin | Mỗi `cmdReceive*` trong Module phải có đúng 1 flow |
| Nhóm data chỉ chứa cờ trạng thái, số liệu để chung một bộ | Nhóm data phải là **bộ data hoàn chỉnh**, đổi tên nhóm là thấy đổi |
| Object `data` luôn thắng nhóm data | Phải có cờ `dataOverride`, mặc định `false` |
| Flow tự ép data ngầm bên trong hàm | Khai báo tường minh trong `FLOW_FORCE` và log ra khi ép |
| `data` liệt kê mọi field làm tester rối | Chỉ giữ field có **giá trị liên tục cần quét ngưỡng** |
| Mock chép lại các bước của handler | Gọi thẳng `Module.cmdReceiveXxx()` với gói tin giả |
| Mock dựng mốc thời gian bằng `Date.now()` / `new Date().setHours()` | `SERVER_TIME` + tính mốc ngày theo UTC+7, ví dụ 0h kế tiếp: `(Math.floor((t + 7h) / DAY) + 1) * DAY - 7h` |

## File Layout

```
docs/modules/{feature}/mock/
├── {feature}-mock.md              ← doc cho tester
└── runtime/
    ├── {Feature}Mock.js           ← logic, KHÔNG vào project.json
    └── mock-current.json          ← tester sửa hằng ngày
```

`{feature}` là docs id, ví dụ `battlepass`. `{Feature}Mock` là object runtime, ví dụ `BattlePassCustomMock`.

## 4 tầng ưu tiên của data

Trên thắng dưới. Đây là phần dễ làm sai nhất.

```
FLOW_FORCE[flowId]   ← bản chất flow quy định, KHÔNG ghi đè được
data                 ← chỉ khi dataOverride: true
DATA_GROUPS[dataId]  ← bộ data đang chọn
DEFAULTS             ← nền chung
```

**Vì sao cần `dataOverride`:** object `data` trong JSON vừa là nơi ghi đè, vừa là danh sách tham khảo các field sửa được. Nếu nó luôn thắng thì các bộ `DATA_GROUPS` không bao giờ có tác dụng — đổi `dataId` cũng không thấy gì đổi. Mặc định `false`.

**Vì sao cần `FLOW_FORCE`:** một số flow có data nằm trong chính định nghĩa của nó. Ví dụ `cmdReceiveBuyShield` nghĩa là "server báo mua **thành công**", nên số khiên phải ≥ 1; để `data` set về 0 thì gói tin tự mâu thuẫn với chính nó. Phải khai báo tường minh **và log ra khi ép**, nếu không tester sửa `data` mà không ăn sẽ không hiểu vì sao.

Chỉ đặt **giá trị cố định** vào `FLOW_FORCE`. Điều chỉnh có điều kiện (vd "nâng streak lên tối thiểu N nếu đang thấp hơn") giữ trong hàm của flow đó, vì nhét vào bảng sẽ đè luôn giá trị hợp lệ của tester.

## Quy ước `flowId`

Một biến `flowId`, phân loại bằng tiền tố:

| Nhóm | Tiền tố | Số lượng | Ghi chú |
|---|---|---|---|
| 1. Giả lập gói tin | `cmdReceive*` | = số `cmdReceive*` trong Module | **Đặt đúng tên handler** — đọc `flowId` là biết chạy vào hàm nào |
| 2. Chỉ set data | `data` | 1 | Không gửi gói tin, không mở GUI. Dùng khi GUI đã mở sẵn hoặc đang trong bàn chơi |
| 3. Flow cần action user | `flow_*` | tuỳ feature | Mở GUI hoặc dựng cả bối cảnh nhiều bước |

Nhóm 1 và nhóm 3 có thể cùng đụng tới một màn hình nhưng khác nhau rõ: `cmdReceiveXxxSettle` chỉ bắn đúng gói tin; `flow_resultWin` dựng **cả bối cảnh** (mở GUI ở phase chờ, delay, rồi mới trả response).

## Chọn field cho `data`

| Loại field | Đặt ở đâu |
|---|---|
| Giá trị liên tục, cần quét ngưỡng (điểm, thời gian, số lượng) | `data` |
| 2–3 trạng thái rời rạc (bật/tắt, enum, hạng mục) | Thành một `dataId` riêng |
| Hai field là hai mặt của cùng một dữ liệu | Chỉ để **một** cái sửa được, cái kia suy ra — tránh cheat ra data mâu thuẫn |
| Field đổi đi đổi lại liên tục trong một phiên test | `data`, kể cả khi chỉ có 2 trạng thái |

Bỏ field khỏi `data` **không** mất khả năng ghi đè — `DEFAULTS` vẫn giữ đủ, ai cần thì thêm tay vào `data` rồi bật `dataOverride`. Ghi rõ điều này trong note.

## Workflow

1. Resolve scope: docs path, runtime source folder, mock object name, entry key trong `DevMockLoader._entries`.
2. Đọc code thật:
   - **Liệt kê đủ `cmdReceive*` trong Module** → đây là danh sách flow nhóm 1, không được thiếu.
   - Tìm `Util.reset`, `Model.reset`, state cần set.
   - Tìm `PoolFunction.*SHOW*`, flow popup/gui/action cần test.
   - Tìm flow nào có tiền đề cố định → vào `FLOW_FORCE`.
3. Đề xuất scenario matrix trước khi code: `dataId`, `flowId`, expected UI, user verify. Hỏi confirm nếu chưa rõ.
4. **Đọc [references/file-templates.md](references/file-templates.md)**, rồi tạo `{feature}-mock.md`, `{Feature}Mock.js`, `mock-current.json` theo đúng khuôn đó.
5. Wire `Cheat.js`: thêm entry `{feature}: { path, configPath, exportName }`, key dev gọi `DevMockLoader.runFromConfig("{feature}")`.
6. Khi thêm `dataId`/`flowId` vào mock đã có, **cập nhật đủ 3 nơi trong cùng lượt**: `{Feature}Mock.js`, `mock-current.json` (`_validDataIds`/`_validFlowIds` + note), `{feature}-mock.md` (bảng flow + scenario matrix).

## Template 2 file runtime

Trước khi tạo hoặc sửa `mock-current.json` / `{Feature}Mock.js`, **bắt buộc đọc toàn bộ**
[references/file-templates.md](references/file-templates.md). Đó là source chuẩn cho cấu trúc
2 file đó.

Các guard không được bỏ qua dù đã đọc reference:

- `run(caseId, flowId, options)` không đổi chữ ký; đọc `dataId` từ `options` để khỏi phải sửa
  `Cheat.js` — file dùng chung với mock của feature khác.
- `_pick()` đủ 4 tầng theo đúng thứ tự, dùng `!= null` chứ không phải truthy.
- Mỗi `cmdReceive*` trong Module có đúng 1 case trong `runFlow`, đặt đúng tên handler.
- `mock-current.json` giữ dòng trống phân nhóm param; không generate bằng `json.dumps`.

## Hai quy tắc nạp lại — phải ghi trong doc

Thiếu hai dòng này là tester sửa xong không thấy gì đổi và tưởng mock hỏng.

| Sửa gì | Cần làm gì |
|---|---|
| `mock-current.json` | Không cần gì — bấm phím cheat là đọc lại |
| `{Feature}Mock.js` | Thêm tạm `"reloadScript": true`. Loader cache object mock trong bộ nhớ |
| File trong `src/` | **Khởi động lại app** — nằm trong `project.json`, nạp lúc boot |

Ngoài ra nếu mock gọi `Util.reset()` mỗi lần chạy, kiểm tra xem `reset()` có xoá state nào mà mock cần giữ không (tham chiếu node đang hiển thị, trạng thái tích luỹ...). Giữ lại quanh `reset()` giống cách giữ các giá trị tích luỹ khác.

## Verify

- `node --check src/gamemgr/Cheat.js`
- `node --check docs/modules/{feature}/mock/runtime/{Feature}Mock.js`
- Parse `mock-current.json` bằng `JSON.parse`.
- `rg "{Feature}Mock|mock-current|docs/modules/{feature}/mock" project.json` phải không có match.
- **Mỗi `cmdReceive*` trong Module có đúng 1 case trong `runFlow`** — quét bằng regex, không đếm tay.
- Mọi `dataId` trong `DATA_GROUPS` có mặt trong `_validDataIds` và trong doc.
- Mọi `flowId` trong `_validFlowIds` có case thật trong `runFlow` và có trong doc.
- Mọi key trong `data` tồn tại trong `DEFAULTS`; `data` và `_dataNotes` khớp 1-1.
- Mọi flow trong `FLOW_FORCE` có case thật trong `runFlow`.
- Bấm phím cheat local dev: đổi `dataId`, save, bấm lại → thấy đổi mà không cần restart.

## Common Mistakes

- Dùng comment `//` trong JSON làm `JSON.parse` lỗi. Dùng key `_help`, `_validDataIds`.
- Generate `mock-current.json` bằng `json.dumps` → mất hết dòng trống phân nhóm. Viết tay hoặc chỉ sửa đúng chuỗi cần đổi.
- Thêm `dataId`/`flowId` mà quên cập nhật `_validDataIds`/`_validFlowIds` hoặc doc.
- Để note trên đầu JSON làm tester khó thấy field cần sửa. Field điều khiển phải ở trên cùng, note `_*` ở dưới.
- Reload/eval mock JS mỗi lần bấm phím khi chỉ cần đổi data. Mặc định chỉ đọc lại JSON.
- Sửa feature production chỉ để mock test. Nếu thiếu hook, ưu tiên fake trong mock runtime hoặc hỏi user trước.
- Bắt tester đánh một ván thật / chờ điều kiện runtime để kiểm một thứ mà giả lập gói tin là xong. Chỉ chấp nhận khi hook thật sự không gọi được từ ngoài.
